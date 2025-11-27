from flask import Flask, render_template, session, redirect, url_for, flash
from modules.auth import auth_bp

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages and sessions

# Register Blueprint
app.register_blueprint(auth_bp)

@app.route('/')
def home():
    return render_template('index.html')

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

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == "__main__":
    app.run(debug=True)