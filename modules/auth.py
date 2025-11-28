from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
from modules.database import get_supabase
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, ""

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    try:
        data = request.form
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        phone = data.get('phone')
        preferred_language = data.get('preferred_language', 'en')

        # Validation
        if not all([email, password, name]):
            flash('Email, password, and name are required', 'error')
            return redirect(url_for('auth.register'))

        if not validate_email(email):
            flash('Invalid email format', 'error')
            return redirect(url_for('auth.register'))

        is_valid_pwd, pwd_msg = validate_password(password)
        if not is_valid_pwd:
            flash(pwd_msg, 'error')
            return redirect(url_for('auth.register'))

        supabase = get_supabase()
        if not supabase:
            flash('Database connection error', 'error')
            return redirect(url_for('auth.register'))

        # Create auth user
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
        })

        if auth_response.user:
            # Create farmer profile
            farmer_data = {
                'id': auth_response.user.id,
                'email': email,
                'name': name,
                'phone': phone,
                'preferred_language': preferred_language,
                'password': password  # Storing hashed version from auth
            }

            farmer_response = supabase.table('farmers').insert(farmer_data).execute()

            if farmer_response.data:
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('auth.login'))
            else:
                # If farmer profile creation fails, delete the auth user
                supabase.auth.admin.delete_user(auth_response.user.id)
                flash('Failed to create farmer profile', 'error')
                return redirect(url_for('auth.register'))

        else:
            error_msg = auth_response.get('message', 'Registration failed')
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))

    except Exception as e:
        error_msg = str(e)
        if 'User already registered' in error_msg:
            flash('Email already registered', 'error')
        else:
            flash(f'Registration error: {error_msg}', 'error')
        return redirect(url_for('auth.register'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        data = request.form
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('auth.login'))

        supabase = get_supabase()
        if not supabase:
            flash('Database connection error', 'error')
            return redirect(url_for('auth.login'))

        # Authenticate user
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if auth_response.user:
            # Get farmer profile
            farmer_response = supabase.table('farmers').select('*').eq('id', auth_response.user.id).execute()
            
            if farmer_response.data:
                farmer = farmer_response.data[0]
                
                # Set session data
                session['user_id'] = auth_response.user.id
                session['user_email'] = farmer['email']
                session['user_name'] = farmer['name']
                session['language'] = farmer.get('preferred_language', 'en')
                session['access_token'] = auth_response.session.access_token
                
                flash(f'Welcome back, {farmer["name"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Farmer profile not found', 'error')
                return redirect(url_for('auth.login'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))

    except Exception as e:
        error_msg = str(e)
        if 'Invalid login credentials' in error_msg:
            flash('Invalid email or password', 'error')
        else:
            flash(f'Login error: {error_msg}', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    try:
        supabase = get_supabase()
        if supabase:
            supabase.auth.sign_out()
        
        # Clear session
        session.clear()
        flash('You have been logged out successfully', 'success')
        
    except Exception as e:
        flash('Logout completed', 'info')
    
    return redirect(url_for('home'))

@auth_bp.route('/profile', methods=['GET'])
def profile():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('auth.login'))
    
    try:
        supabase = get_supabase()
        farmer_response = supabase.table('farmers').select('*').eq('id', session['user_id']).execute()
        
        if farmer_response.data:
            farmer = farmer_response.data[0]
            return render_template('profile.html', farmer=farmer)
        else:
            flash('Profile not found', 'error')
            return redirect(url_for('dashboard'))
            
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@auth_bp.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.form
        update_data = {
            'name': data.get('name'),
            'phone': data.get('phone'),
            'preferred_language': data.get('preferred_language', 'en')
        }

        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        supabase = get_supabase()
        response = supabase.table('farmers').update(update_data).eq('id', session['user_id']).execute()

        if response.data:
            # Update session
            session['user_name'] = update_data.get('name', session.get('user_name'))
            session['language'] = update_data.get('preferred_language', session.get('language', 'en'))
            
            flash('Profile updated successfully', 'success')
        else:
            flash('Failed to update profile', 'error')
            
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'error')
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/check-auth')
def check_auth():
    """API endpoint to check authentication status"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'name': session.get('user_name'),
                'email': session.get('user_email')
            }
        })
    else:
        return jsonify({'authenticated': False})