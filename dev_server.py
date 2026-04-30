#!/usr/bin/env python3
"""Lightweight dev server for UI preview - no heavy dependencies"""
from flask import Flask, render_template, Blueprint
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'dev-secret-key'

# Create blueprints to match real app structure
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Mock user object for templates
class MockUser:
    is_authenticated = False
    full_name = "Demo User"

@app.context_processor
def inject_user():
    return dict(current_user=MockUser())

# Auth routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    return "Logged out"

# Dashboard routes
@dashboard_bp.route('/')
def index():
    return render_template('dashboard/index.html', user=MockUser())

@dashboard_bp.route('/metering')
def metering():
    return render_template('dashboard/metering.html')

@dashboard_bp.route('/analytics')
def analytics():
    return render_template('dashboard/analytics.html')

# API routes (mock)
@api_bp.route('/forecast/solar')
def forecast():
    return {'success': True, 'data': []}

# Main routes
@app.route('/')
def landing():
    return render_template('landing.html')

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(api_bp)

@app.errorhandler(404)
def not_found(e):
    return f"404 Not Found: {e}", 404

@app.errorhandler(500)
def server_error(e):
    return f"500 Server Error: {e}", 500

if __name__ == '__main__':
    print("🚀 Starting dev server at http://localhost:5000")
    print("   Landing: http://localhost:5000/")
    print("   Login: http://localhost:5000/auth/login")
    print("   Register: http://localhost:5000/auth/register")
    print("   Dashboard: http://localhost:5000/dashboard/")
    print("   Metering: http://localhost:5000/dashboard/metering")
    print("   Analytics: http://localhost:5000/dashboard/analytics")
    app.run(debug=True, host='localhost', port=5000, use_reloader=False)
