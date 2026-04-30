from flask import Flask
from flask_login import LoginManager
from config import Config
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.api import api_bp
from services.supabase_service import SupabaseService
from services.scheduler_service import SchedulerService
import os
import atexit

# Initialize scheduler
scheduler_service = SchedulerService()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this feature.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return SupabaseService.get_user_by_id(user_id)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    
    # Start background scheduler
    scheduler_service.start_jobs()
    
    # Ensure scheduler shuts down properly
    atexit.register(scheduler_service.stop_jobs)
    
    # Add route for landing page
    @app.route('/')
    def landing():
        from flask import render_template
        return render_template('landing.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return {'error': 'Page not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    return app

if __name__ == '__main__':
    application = create_app()
    application.run(debug=False, host='0.0.0.0', port=5000)