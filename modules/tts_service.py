from flask import Blueprint, request, send_file, jsonify, current_app
from io import BytesIO
import os
import re

tts_bp = Blueprint('tts', __name__)


@tts_bp.route('/api/tts', methods=['POST'])
def tts_endpoint():
    """Consolidated TTS endpoint.

    Tries Google Cloud Text-to-Speech when available (and when
    `GOOGLE_APPLICATION_CREDENTIALS` is set). Falls back to gTTS.

    Expects JSON: { "text": "...", "lang": "bn" (optional) }
    Returns: audio/mpeg (MP3)
    """
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    lang = (data.get('lang') or data.get('language') or '').strip()

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    # Auto-detect Bangla if present when no lang provided
    if not lang:
        lang = 'bn' if re.search(r'[\u0980-\u09FF]', text) else 'en'

    # Prefer Google Cloud TTS if client available and credentials set
    use_gcloud = False
    try:
        from google.cloud import texttospeech
        if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            use_gcloud = True
    except Exception:
        use_gcloud = False

    if use_gcloud:
        try:
            from google.cloud import texttospeech
            client = texttospeech.TextToSpeechClient()
            candidates = ['bn-IN', 'bn-BD', lang]
            audio_content = None
            for code in candidates:
                try:
                    synthesis_input = texttospeech.SynthesisInput(text=text)
                    voice = texttospeech.VoiceSelectionParams(
                        language_code=code,
                        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
                    )
                    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
                    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
                    audio_content = response.audio_content
                    if audio_content:
                        break
                except Exception:
                    audio_content = None
                    continue

            if not audio_content:
                raise RuntimeError('Google Cloud TTS returned no audio')

            buf = BytesIO(audio_content)
            buf.seek(0)
            return send_file(buf, mimetype='audio/mpeg', as_attachment=False, download_name='tts.mp3')
        except Exception as e:
            current_app.logger.exception('Google Cloud TTS failed, falling back to gTTS: %s', e)

    # gTTS fallback
    try:
        from gtts import gTTS
    except Exception as e:
        current_app.logger.exception('No TTS provider available: %s', e)
        return jsonify({'error': 'No TTS provider available', 'details': str(e)}), 500

    try:
        buf = BytesIO()
        tts = gTTS(text=text, lang=lang)
        tts.write_to_fp(buf)
        buf.seek(0)
        return send_file(buf, mimetype='audio/mpeg', as_attachment=False, download_name='tts.mp3')
    except Exception as e:
        current_app.logger.exception('gTTS fallback TTS error: %s', e)
        return jsonify({'error': 'TTS failed', 'details': str(e)}), 500
