from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
from modules.database import get_supabase
import re

auth_bp = Blueprint('auth', __name__)

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
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        # Validation
        if not all([email, password, name]):
            flash('Email, password, and name are required', 'error')
            return redirect(url_for('auth.register'))

        supabase = get_supabase()
        if not supabase:
            flash('Database connection error', 'error')
            return redirect(url_for('auth.register'))

        print(f"Attempting to register: {email}")  # Debug

        # Create auth user
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
        })

        print(f"Auth response: {auth_response}")  # Debug

        if auth_response.user:
            print(f"User created with ID: {auth_response.user.id}")  # Debug
            
            # Create farmer profile in farmers table
            farmer_data = {
                'id': auth_response.user.id,  # Use the same ID as auth user
                'email': email,
                'name': name,
                'phone': phone,
                'preferred_language': preferred_language
            }

            # Include optional coordinates if provided
            if latitude:
                try:
                    farmer_data['latitude'] = float(latitude)
                except Exception:
                    farmer_data['latitude'] = latitude
            if longitude:
                try:
                    farmer_data['longitude'] = float(longitude)
                except Exception:
                    farmer_data['longitude'] = longitude

            print(f"Creating farmer profile: {farmer_data}")  # Debug
            
            farmer_response = supabase.table('farmers').insert(farmer_data).execute()

            print(f"Farmer response: {farmer_response}")  # Debug

            if farmer_response.data:
                flash('Registration successful! You can now login.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Failed to create farmer profile', 'error')
                return redirect(url_for('auth.register'))

        else:
            error_msg = auth_response.get('message', 'Registration failed')
            flash(f'Registration failed: {error_msg}', 'error')
            return redirect(url_for('auth.register'))

    except Exception as e:
        print(f"Registration error: {str(e)}")  # Debug
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

        print(f"Login attempt: {email}")  # Debug

        # Authenticate user
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        print(f"Login auth response: {auth_response}")  # Debug

        if auth_response.user:
            # Get farmer profile
            farmer_response = supabase.table('farmers').select('*').eq('id', auth_response.user.id).execute()
            
            print(f"Farmer lookup: {farmer_response}")  # Debug

            if farmer_response.data:
                farmer = farmer_response.data[0]
                # Set session data
                session['user_id'] = auth_response.user.id
                session['user_email'] = farmer['email']
                session['user_name'] = farmer['name']
                session['language'] = farmer.get('preferred_language', 'en')
                # set optional coordinates in session for convenience
                session['latitude'] = farmer.get('latitude')
                session['longitude'] = farmer.get('longitude')
                session['access_token'] = auth_response.session.access_token
                
                flash(f'Welcome back, {farmer["name"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                # If farmer profile doesn't exist, create it
                farmer_data = {
                    'id': auth_response.user.id,
                    'email': email,
                    'name': auth_response.user.user_metadata.get('name', 'Farmer'),
                    'preferred_language': 'en'
                }
                
                create_response = supabase.table('farmers').insert(farmer_data).execute()
                if create_response.data:
                    session['user_id'] = auth_response.user.id
                    session['user_email'] = email
                    session['user_name'] = farmer_data['name']
                    session['language'] = 'en'
                    # set session coords if present
                    session['latitude'] = farmer_data.get('latitude')
                    session['longitude'] = farmer_data.get('longitude')
                    
                    flash(f'Welcome, {farmer_data["name"]}!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Profile created but login failed', 'error')
                    return redirect(url_for('auth.login'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))

    except Exception as e:
        print(f"Login error: {str(e)}")  # Debug
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

        # Accept latitude/longitude updates if provided
        lat = data.get('latitude')
        lng = data.get('longitude')
        if lat is not None and lat != '':
            try:
                update_data['latitude'] = float(lat)
            except Exception:
                update_data['latitude'] = lat
        if lng is not None and lng != '':
            try:
                update_data['longitude'] = float(lng)
            except Exception:
                update_data['longitude'] = lng

        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}

        supabase = get_supabase()
        response = supabase.table('farmers').update(update_data).eq('id', session['user_id']).execute()

        if response.data:
            # Update session
            session['user_name'] = update_data.get('name', session.get('user_name'))
            session['language'] = update_data.get('preferred_language', session.get('language', 'en'))
            # update session coordinates if changed
            if 'latitude' in update_data:
                session['latitude'] = update_data.get('latitude')
            if 'longitude' in update_data:
                session['longitude'] = update_data.get('longitude')
            
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