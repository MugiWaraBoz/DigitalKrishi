# DigitalKrishi

DigitalKrishi is a lightweight Flask-based web application designed to help smallholder farmers monitor crop batches, receive AI-powered crop advisories, and interact with a Bangla-capable voice assistant. The project integrates weather, risk mapping, Supabase as the backend DB, and text-to-speech functionality with server-side fallbacks.

**Repository structure (important files)**
- `app.py` — Flask app entrypoint and blueprint registration.
- `modules/` — backend modules (auth, crops, api, tts_service, gemini_ai, etc.).
- `templates/` — Jinja2 templates (dashboard, profile, risk_map, voice, etc.).
- `static/` — client assets and JS (including `static/js/voice.js`).
- `requirements.txt` — Python dependencies.
- `docs/README.md` — additional developer notes.

**Key features**
- User accounts and profile with farm coordinates (latitude/longitude).
- Crop batch management (add, complete, reactivate, delete).
- AI-powered crop advisory (server-generated, uses Gemini/OpenAI style model in config).
- Voice assistant page: listens, queries AI, and speaks responses (Bangla/English), with queue and fallback to server TTS.
- Risk Map: pin active batch, view neighbor mock data, mobile-friendly quick access.
- Server-side TTS: prefers Google Cloud Text-to-Speech, falls back to gTTS when not available.

Requirements
- Python 3.9+
- A Supabase project (PostgREST) for storing farmers, crops, and related data.
- Optional: Google Cloud credentials for high-quality TTS.

Environment variables
Do NOT commit secrets. Create a `.env` file (or set environment variables) with the following keys:

- `OPENWEATHER_API_KEY` — API key for weather (OpenWeather or your preferred provider).
- `SUPABASE_URL` — Supabase project URL (e.g. `https://xyz.supabase.co`).
- `SUPABASE_KEY` — Supabase anon/service role key.
- `GEMINI_API_KEY` — API key for Gemini/LLM model (or whichever model is configured).
- `GEMINI_MODEL` — model id (e.g. `gemini-2.0-flash`).
- `GOOGLE_APPLICATION_CREDENTIALS` — (optional) path to Google service account JSON for Google Cloud TTS.

Never paste live API keys into source or public repos. Use placeholders in `.env.example`.

Quick setup (development)

1. Clone the repo and create a virtual environment

PowerShell (Windows):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Create `.env` in project root and provide the values described above.
   
3. Run the app

```powershell
# from project root (virtualenv activated)
python app.py
# or if you use flask directly
# set FLASK_APP=app.py
# flask run
```

Open `http://127.0.0.1:5000` in your browser.
