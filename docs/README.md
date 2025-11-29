DigitalKrishi — Project Documentation

Overview

DigitalKrishi is a Flask-based web application designed to help Bangladeshi farmers monitor crop batches, receive AI-driven agricultural advisories in Bangla, and visualize local spoilage risk via a community risk map. It includes voice assistant features (speech recognition + TTS), server-side AI calls (Gemini/Google generative AI), and multiple helper APIs.

Repository layout (important files)

- app.py — Flask application entrypoint and blueprint registration.
- advisory_generator.py — server-side advisory generator (imported dynamically).
- requirements.txt — Python dependencies. Optional packages: google-cloud-texttospeech for server TTS.

- modules/
  - api.py — Main API blueprint (AI endpoints, weather, crop endpoints, TTS fallback endpoint). The consolidated `/api/tts` endpoint prefers Google Cloud TTS when configured and falls back to gTTS.
  - auth.py — Authentication (register/login/logout), session handling.
  - crops.py — Routes for adding/viewing crop batches and related UI logic.
  - gemini_ai.py — Gemini AI helper blueprint, voice page route.
  - tts_service.py — Consolidated TTS blueprint used by the frontend when browsers lack Bangla voices.
  - database.py — Supabase integration helpers (DB access).

- templates/
  - base.html — Base layout (navigation, language loader, shared scripts/styles).
  - dashboard.html — Main farmer dashboard with quick actions, active batches, server advisory UI, and quick stats.
  - voice.html — Dedicated voice assistant page. Uses Web Speech API for recognition and speechSynthesis for browser TTS; falls back to `/api/tts` when necessary.
  - risk_map.html — Interactive Leaflet map showing farmer location, neighbor mock risks, and a selector to pin active crop batches.

- static/
  - js/voice.js — Client-side voice assistant logic: recognition, AI question submission, queuing of TTS replies, local history, stop/pause controls.

Key Features

1. Voice Assistant
- Uses Web Speech API (SpeechRecognition) to capture Bangla speech and a server endpoint `/api/ai/voice-question` to get answers (Gemini).
- Replies are shown as text and spoken. Preference order: browser native Bangla voice (if available) → server TTS (`/api/tts`).
- Replies are queued to avoid overlap and there's a Stop button to cancel immediate playback.
- Conversation history is saved in `localStorage` on the client.

2. Server TTS
- Endpoint: `POST /api/tts` with JSON { text, lang }.
- Implementation attempts Google Cloud Text-to-Speech when `GOOGLE_APPLICATION_CREDENTIALS` is set and the `google-cloud-texttospeech` package is installed, otherwise falls back to `gTTS`.

3. Risk Map
- `templates/risk_map.html` renders a Leaflet map with: farmer marker, neighbor mock-risk markers, clustering when available.
- New: a dropdown to select active crop batches and pin one on the map. If batch latitude/longitude are not present, the map picks a plausible location near the district center (mock behavior) and displays neighbor alerts around it.

4. Dashboard
- Quick Actions include Add Crop, Plant Disease Analyzer, Voice Assistant and (mobile-only) a Risk Map button to ensure access on phones.

How to run locally

1. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. (Optional) To enable Google Cloud TTS, set the environment variable to your service account JSON path:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\path\to\gcp-key.json'
```

3. Start the Flask app:

```powershell
python app.py
```

4. Visit `http://localhost:5000` and login.

Notes & Troubleshooting

- Native Bangla voices vary across operating systems and browsers. The app uses a server-side fallback to ensure Bangla audio is available.
- If you enable Google Cloud TTS but still get no audio, confirm the credentials path and network connectivity.
- The risk map uses mocked neighbor data for privacy; if you want real neighbor data, implement a server endpoint to return anonymized nearby events.

Development notes

- To change the TTS fallback order or add caching, edit `modules/tts_service.py`.
- Voice assistant logic is in `static/js/voice.js`. For improving latency, prewarm the TTS provider or add short SSML pauses.
- The dashboard regularly polls `/api/dashboard/stats` every 30s — adjust the interval near the bottom of `templates/dashboard.html`.

Where to look for further improvements

- Persist conversation history server-side (Supabase) for cross-device history.
- Replace `gTTS` fallback with Google Cloud TTS exclusively for more natural Bangla voices (requires provisioning).
- Add geocoding or allow farmers to set precise farm coordinates in their profile for accurate mapping.

Contact

If you want me to implement server-side history, add geocoding, or fully integrate Google Cloud TTS, tell me which feature to prioritize and I will implement it.
