from flask import Flask, render_template, session, redirect, url_for, flash, request, jsonify
from dotenv import load_dotenv
from modules.auth import auth_bp
from modules.crops import crops_bp
from modules.api import api_bp
from modules.gemini_ai import gemini_bp
import os
import sys
import re
# Load environment variables from .env (Supabase, Gemini, etc.)
load_dotenv()

# Ensure project root is on sys.path so advisory_generator can be imported
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Advisory generator (server-side) imported from project root
try:
    from advisory_generator import AgriculturalAdvisoryGenerator
except ModuleNotFoundError:
    # Fallback: load module directly from file path
    import importlib.util
    spec_path = os.path.join(ROOT, 'advisory_generator.py')
    if os.path.exists(spec_path):
        spec = importlib.util.spec_from_file_location('advisory_generator', spec_path)
        advisory_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(advisory_mod)
        AgriculturalAdvisoryGenerator = advisory_mod.AgriculturalAdvisoryGenerator
    else:
        raise

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages and sessions

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(crops_bp)
app.register_blueprint(api_bp)
app.register_blueprint(gemini_bp)

@app.route('/')
def home():
    # If user is logged in, send them to dashboard instead of frontpage
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('frontpage.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash("Please login first", 'warning')
        return redirect(url_for('auth.login'))

    user_data = {
        'name': session.get('user_name', 'User'),
        'email': session.get('user_email'),
        'language': session.get('language', 'bn')
    }

    advisory = None
    sms = None

    if request.method == 'POST':
        # Get form inputs from dashboard advisory form
        crop = request.form.get('crop', 'টমেটো')
        weather = request.form.get('weather', 'হালকা মেঘ')
        risk = request.form.get('risk', 'Low')

        gen = AgriculturalAdvisoryGenerator()
        advisory = gen.generate_advisory(crop, weather, risk)

        # extract console.log message if present
        m = re.search(r'console\.log\((?:"|\')(.*?)(?:"|\')\)', advisory, re.S)
        if m:
            sms = m.group(1)
            # remove console.log line from displayed advisory
            advisory = re.sub(r'\n*\s*console\.log\((?:"|\').*?(?:"|\')\)\s*', '', advisory, flags=re.S)

    return render_template('dashboard.html', user=user_data, advisory=advisory, sms=sms)



@app.route('/advisory/generate', methods=['POST'])
def advisory_generate():
    """API endpoint: generate advisories for given crops and weather.

    Expected JSON: { crops: ['আলু','টমেটো'], weather: { temperature, humidity, rain_chance, condition }, season: 'kharif' }
    """
    if not request.is_json:
        return jsonify({'error': 'JSON body required'}), 400
    data = request.get_json()
    crops = data.get('crops') or []
    weather = data.get('weather') or {}
    season = data.get('season')

    gen = AgriculturalAdvisoryGenerator()
    advisories = gen.generate_crops_advisory(crops, weather, season)
    return jsonify({'advisories': advisories})

@app.route('/risk-map')
def risk_map():
    if 'user_id' not in session:
        flash("Please login first", 'warning')
        return redirect(url_for('auth.login'))
    return render_template('risk_map.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/debug-db')
def debug_db():
    from modules.database import get_supabase
    supabase = get_supabase()
    
    if supabase:
        # Test connection
        try:
            result = supabase.table('farmers').select('*').limit(1).execute()
            return f"Supabase connected! Found {len(result.data)} farmers"
        except Exception as e:
            return f"Supabase error: {e}"
    else:
        return "Supabase not connected"

@app.route('/debug-all-crops')
def debug_all_crops():
    from modules.database import get_supabase
    supabase = get_supabase()
    
    try:
        # Get ALL crops from the database (not filtered by user)
        result = supabase.table('crop_batches').select('*').execute()
        return f"""
        <h1>All Crops in Database</h1>
        <p>Total crops: {len(result.data) if result.data else 0}</p>
        <pre>{result.data if result.data else 'No crops found'}</pre>
        """
    except Exception as e:
        return f"Error: {e}"

@app.route('/debug-session')
def debug_session():
    return f"""
    <h1>Session Debug</h1>
    <p>User ID: {session.get('user_id')}</p>
    <p>User Name: {session.get('user_name')}</p>
    <p>Session: {dict(session)}</p>
    """

if __name__ == "__main__":
    app.run(debug=True)