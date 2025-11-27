from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# Create Blueprint
auth_bp = Blueprint('auth', __name__)

# Simulated "database" for demo purposes
users_db = []

def register_user(name, email, password, phone, language):
    # Check if email already exists
    if any(u['email'] == email for u in users_db):
        return False, "Email already registered"
    
    hashed_password = generate_password_hash(password)
    user = {
        'id': len(users_db) + 1,
        'name': name,
        'email': email,
        'password': hashed_password,
        'phone': phone,
        'language': language
    }
    users_db.append(user)
    return True, "Registration successful"

def login_user(email, password):
    user = next((u for u in users_db if u['email'] == email), None)
    if user and check_password_hash(user['password'], password):
        return True, user
    return False, None

# Routes
@auth_bp.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        success, user = login_user(email, password)
        if success:
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            session['language'] = user['language']
            flash(f"Welcome {user['name']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out", 'info')
    return redirect(url_for('auth.login'))