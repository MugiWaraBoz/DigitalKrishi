from flask import Flask, render_template, request, redirect, url_for, flash, session
from modules.auth import register_user, login_user

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages and sessions

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        language = request.form['language']

        success, message = register_user(name, email, password, phone, language)
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        success, user = login_user(email, password)
        if success:
            session['user'] = user['email']
            flash(f"Welcome {user['name']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please login first", 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html', user_email=session['user'])

if __name__ == "__main__":
    app.run(debug=True)
