from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from services.supabase_service import SupabaseService
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, ""

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Please provide both email and password.', 'danger')
            return render_template('auth/login.html')
        
        if not validate_email(email):
            flash('Please provide a valid email address.', 'danger')
            return render_template('auth/login.html')
        
        result = SupabaseService.login_user(email, password)
        
        if result['success']:
            user = result['user']
            login_user(user, remember=remember)
            session['access_token'] = result['access_token']
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash(result.get('error', 'Invalid email or password. Please try again.'), 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not full_name or len(full_name) < 2:
            errors.append('Full name is required and must be at least 2 characters.')
        
        if not email or not validate_email(email):
            errors.append('Please provide a valid email address.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        password_valid, password_message = validate_password(password)
        if not password_valid:
            errors.append(password_message)
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html')
        
        result = SupabaseService.register_user(email, password, full_name)
        
        if result['success']:
            flash('Registration successful! Please log in to continue.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(result.get('error', 'Registration failed. This email may already be registered.'), 'danger')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    access_token = session.get('access_token')
    if access_token:
        SupabaseService.logout_user(access_token)
    
    logout_user()
    session.clear()
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('landing'))