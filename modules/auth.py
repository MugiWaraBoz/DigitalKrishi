# modules/auth.py
from werkzeug.security import generate_password_hash, check_password_hash

# Simulated "database" for demo purposes
users_db = []

def register_user(name, email, password, phone, language):
    # Check if email already exists
    if any(u['email'] == email for u in users_db):
        return False, "Email already registered"
    
    hashed_password = generate_password_hash(password)
    user = {
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
