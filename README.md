# Vastu AI — Household Prediction System v2.0

Full-stack Indian real estate price prediction app with AI chatbot.

---

## Project Structure

```
vastu-ai/
├── frontend/
│   └── index.html        ← Deploy as Static Site on Render
└── backend/
    ├── main.py           ← FastAPI backend (API key lives here)
    ├── requirements.txt
    └── Dockerfile
```

---

## Step 1 — Deploy Backend (stores your API key safely)

1. Create a new GitHub repo called `vastu-backend`
2. Upload `backend/` files to it
3. On Render → **New Web Service**
   - Language: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port 8000`
4. In Render → **Environment Variables** → Add:
   - Key: `ANTHROPIC_API_KEY`
   - Value: `sk-ant-your-key-here`
5. Deploy → note your URL e.g. `https://vastu-backend.onrender.com`

---

## Step 2 — Deploy Frontend

1. Create a new GitHub repo called `vastu-frontend`
2. Upload `frontend/index.html` renamed as `index.html`
3. On Render → **New Static Site**
   - Publish Directory: `.`
4. Deploy → get your frontend URL

---

## Step 3 — Connect Frontend to Backend

Open your live site → paste your backend URL in the config box at the top:
```
https://vastu-backend.onrender.com
```

The AI chatbot will now work fully! ✅

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/health` | Status + API key check |
| POST | `/predict` | House price prediction |
| POST | `/chat` | AI chatbot (proxies Anthropic) |
| GET | `/cities` | List of supported cities |
| GET | `/market/{city}` | Market data for a city |

---

## Features

- 🏠 Price prediction for 12 Indian cities
- 📊 Factor analysis (location, amenities, condition, etc.)
- ✅ Verdict: Good deal / Fair / Overpriced
- 💡 7 expert suggestions per prediction
- 🤖 AI chatbot powered by Claude (via secure backend)
- 📈 Live city price index
- 🔐 API key stored securely on backend (never exposed to browser)
