from flask import Flask, render_template, session, redirect, url_for, flash
from modules.auth import auth_bp
from modules.crops import crops_bp
from modules.api import api_bp

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages and sessions

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(crops_bp)
app.register_blueprint(api_bp)

@app.route('/')
def home():
    # If user is logged in, send them to dashboard instead of frontpage
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('frontpage.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please login first", 'warning')
        return redirect(url_for('auth.login'))
    
    user_data = {
        'name': session.get('user_name', 'User'),
        'email': session.get('user_email'),
        'language': session.get('language', 'bn')
    }
    
    return render_template('dashboard.html', user=user_data)

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