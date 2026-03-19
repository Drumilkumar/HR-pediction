from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os
import numpy as np

app = FastAPI(title="Vastu AI — House Prediction Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── SCHEMAS ──────────────────────────────────────────────────────────────────

class HouseInput(BaseModel):
    city: str
    bhk: int
    area_sqft: float
    floor: str
    age: str
    locality: str
    furnishing: str
    amenities: List[str]
    asking_price: Optional[float] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[str] = ""

# ── PREDICTION MODEL ──────────────────────────────────────────────────────────

BASE_PSF = {
    "mumbai": 22000, "delhi": 14000, "bangalore": 10500, "pune": 8200,
    "hyderabad": 7800, "chennai": 7500, "ahmedabad": 6200, "kolkata": 5800,
    "surat": 5200, "jaipur": 5500, "noida": 8000, "gurgaon": 12000,
}
BHK_M    = {1: 0.80, 2: 1.0, 3: 1.18, 4: 1.36, 5: 1.60}
FLOOR_M  = {"ground": 0.93, "low": 0.97, "mid": 1.0, "high": 1.06, "penthouse": 1.22}
AGE_M    = {"new": 1.18, "1-3": 1.08, "3-8": 1.0, "8-15": 0.88, "15+": 0.76}
LOC_M    = {"prime": 1.45, "suburban": 1.0, "peripheral": 0.77, "outskirts": 0.60}
FURNISH_A= {"unfurnished": 0, "semi": 280, "fully": 650, "premium": 1500}
AMEN_A   = {
    "lift":200,"parking":320,"gym":450,"pool":750,"security":260,
    "power":210,"garden":370,"clubhouse":480,"cctv":160,"intercom":110,
    "gated":370,"metro":650,"school":400,"hospital":350,"mall":300
}

def run_prediction(data: HouseInput):
    city   = data.city.lower().replace(" ", "")
    base   = BASE_PSF.get(city, 7000)
    base  *= BHK_M.get(data.bhk, 1.0)
    base  *= FLOOR_M.get(data.floor, 1.0)
    base  *= AGE_M.get(data.age, 1.0)
    base  *= LOC_M.get(data.locality, 1.0)
    base  += FURNISH_A.get(data.furnishing, 0)
    amen_bonus = sum(AMEN_A.get(a, 0) for a in data.amenities)
    base  += amen_bonus / max(data.area_sqft, 1) * 12

    price    = round(base * data.area_sqft)
    price_lo = round(price * 0.87)
    price_hi = round(price * 1.13)
    psf      = round(base)
    score    = min(100, 45 + len(data.amenities)*4 + int(LOC_M.get(data.locality,1)*12))

    verdict = "good"
    market_psf = BASE_PSF.get(city, 7000)
    if data.asking_price:
        asking_psf = data.asking_price / data.area_sqft
        if asking_psf < market_psf * 0.9:   verdict = "good"
        elif asking_psf < market_psf * 1.15: verdict = "fair"
        else:                                verdict = "high"

    factors = {
        "location":   round(LOC_M.get(data.locality, 1) * 68),
        "amenities":  min(100, len(data.amenities) * 7 + 5),
        "condition":  round(AGE_M.get(data.age, 1) * 82),
        "floor":      round(FLOOR_M.get(data.floor, 1) * 82),
        "furnishing": round((FURNISH_A.get(data.furnishing, 0) / 1500) * 100),
    }

    emi = round(price * 0.8 * 0.085 / 12 / (1 - (1 + 0.085/12)**(-240)))

    suggestions = [
        f"Budget ₹{round(price*0.1/100000, 1)}L for stamp duty & registration (~10%)",
        f"Estimated 20yr home loan EMI: ₹{emi:,}/month at 8.5%",
        "Negotiate 5–10% below asking price — always make a counter offer",
        f"{'High amenity count boosts resale by 15–20%' if len(data.amenities)>=6 else 'Add gated society & parking to improve resale value'}",
        f"{'Prime location: expect 8–12% annual appreciation' if data.locality=='prime' else 'Look near upcoming metro/infra for better ROI'}",
        "Get independent structural inspection before final payment",
        "Verify RERA registration of builder at rera.gov.in",
    ]

    return {
        "predicted_price": price,
        "price_low": price_lo,
        "price_high": price_hi,
        "price_per_sqft": psf,
        "value_score": score,
        "amenity_count": len(data.amenities),
        "verdict": verdict,
        "factors": factors,
        "emi_estimate": emi,
        "suggestions": suggestions,
    }

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "online", "service": "Vastu AI Backend v2.0"}

@app.get("/health")
def health():
    return {"status": "healthy", "ai_key_set": bool(ANTHROPIC_API_KEY)}

@app.post("/predict")
def predict(data: HouseInput):
    try:
        return run_prediction(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(req: ChatRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    system = f"""You are Vastu AI, an expert Indian real estate assistant embedded in a house price prediction app.
Help users with: property prices, BHK advice, home loans, EMI calculations, negotiation tips, RERA, stamp duty, localities, investment ROI.
Be concise (under 150 words), warm, and practical. Use ₹ for currency. Mention Indian cities naturally.
Occasionally use friendly Hindi: 'bilkul', 'bahut acha', 'sahi hai'.
{f"Current prediction context: {req.context}" if req.context else ""}"""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "system": system,
                "messages": [m.dict() for m in req.messages],
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    reply = data["content"][0]["text"]
    return {"reply": reply}

@app.get("/cities")
def cities():
    return {"cities": list(BASE_PSF.keys())}

@app.get("/market/{city}")
def market_data(city: str):
    c = city.lower()
    psf = BASE_PSF.get(c)
    if not psf:
        raise HTTPException(status_code=404, detail="City not found")
    return {
        "city": city,
        "avg_psf": psf,
        "avg_1bhk": round(psf * 500),
        "avg_2bhk": round(psf * 950),
        "avg_3bhk": round(psf * 1400),
        "trend": "rising" if psf > 8000 else "stable",
    }
