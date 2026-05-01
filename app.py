from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_login import LoginManager
from config import Config
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.api import api_bp
from routes.admin import admin_bp
from services.supabase_service import SupabaseService
from services.scheduler_service import SchedulerService
from datetime import datetime
import os
import atexit
import logging
from logging.handlers import RotatingFileHandler

# Initialize scheduler
scheduler_service = SchedulerService()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Setup logging
    setup_logging(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this feature.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user from database for Flask-Login"""
        try:
            return SupabaseService.get_user_by_id(user_id)
        except Exception as e:
            app.logger.error(f"Failed to load user {user_id}: {str(e)}")
            return None
    
    @login_manager.unauthorized_handler
    def unauthorized():
        """Handle unauthorized access"""
        if request.is_json or request.blueprint == 'api':
            return jsonify({'error': 'Authentication required', 'code': 401}), 401
        return redirect(url_for('auth.login', next=request.url))
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    
    # Start background scheduler for AI tasks
    try:
        scheduler_service.start_jobs()
        atexit.register(scheduler_service.stop_jobs)
        app.logger.info("Background scheduler started successfully")
    except Exception as e:
        app.logger.warning(f"Scheduler failed to start (non-critical): {str(e)}")
    
    # Register context processors
    @app.context_processor
    def inject_globals():
        """Inject global variables into all templates"""
        return {
            'current_year': datetime.now().year,
            'app_name': 'Almuslim',
            'app_version': '1.0.0'
        }
    
    # Register template filters
    @app.template_filter('format_currency')
    def format_currency(value):
        """Format number as PKR currency"""
        try:
            return f"PKR {float(value):,.2f}"
        except (ValueError, TypeError):
            return "PKR 0.00"
    
    @app.template_filter('format_date')
    def format_date(value, format='%d %b %Y'):
        """Format date string"""
        try:
            if isinstance(value, str):
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return value.strftime(format)
        except:
            return value
    
    @app.template_filter('status_color')
    def status_color(status):
        """Return color class based on application status"""
        colors = {
            'draft': 'gray',
            'submitted': 'blue',
            'survey_scheduled': 'yellow',
            'demand_notice': 'orange',
            'inspection': 'purple',
            'approved': 'green',
            'rejected': 'red'
        }
        return colors.get(status, 'gray')
    
    # Landing page route
    @app.route('/')
    def landing():
        """Main landing page"""
        return render_template('landing.html')
    
    # Health check endpoint for monitoring
    @app.route('/health')
    def health_check():
        """Health check endpoint for Vercel/monitoring"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'services': {
                'database': check_database_connection(),
                'scheduler': scheduler_service.jobs_started if scheduler_service else False
            }
        }
        return jsonify(health_status)
    
    # Robots.txt to prevent indexing of admin panel
    @app.route('/robots.txt')
    def robots():
        return """User-agent: *
Disallow: /admin-portal-2024/
Disallow: /api/
Allow: /
Sitemap: /sitemap.xml""", 200, {'Content-Type': 'text/plain'}
    
    # Sitemap
    @app.route('/sitemap.xml')
    def sitemap():
        """Generate sitemap"""
        pages = [
            {'loc': '/', 'priority': '1.0'},
            {'loc': '/auth/login', 'priority': '0.8'},
            {'loc': '/auth/register', 'priority': '0.8'},
        ]
        
        sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for page in pages:
            sitemap_xml += f"""  <url>
    <loc>https://almuslim.vercel.app{page['loc']}</loc>
    <priority>{page['priority']}</priority>
  </url>\n"""
        
        sitemap_xml += '</urlset>'
        return sitemap_xml, 200, {'Content-Type': 'application/xml'}
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request"""
        if request.is_json or request.blueprint == 'api':
            return jsonify({
                'error': 'Bad request',
                'message': str(error),
                'code': 400
            }), 400
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden"""
        if request.is_json or request.blueprint == 'api':
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource',
                'code': 403
            }), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found"""
        if request.is_json or request.blueprint == 'api':
            return jsonify({
                'error': 'Not found',
                'message': 'The requested resource was not found',
                'code': 404
            }), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed"""
        if request.is_json or request.blueprint == 'api':
            return jsonify({
                'error': 'Method not allowed',
                'message': str(error),
                'code': 405
            }), 405
        return render_template('errors/405.html'), 405
    
    @app.errorhandler(429)
    def too_many_requests(error):
        """Handle 429 Too Many Requests"""
        return jsonify({
            'error': 'Too many requests',
            'message': 'Please try again later',
            'code': 429,
            'retry_after': 60
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        app.logger.error(f"Internal server error: {str(error)}")
        if request.is_json or request.blueprint == 'api':
            return jsonify({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred',
                'code': 500
            }), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle 503 Service Unavailable"""
        return jsonify({
            'error': 'Service unavailable',
            'message': 'The service is temporarily unavailable. Please try again later.',
            'code': 503
        }), 503
    
    # Handle OPTIONS requests for CORS
    @app.after_request
    def after_request(response):
        """Add security headers and handle CORS"""
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # CORS headers for API routes
        if request.blueprint == 'api' or request.path.startswith('/api/'):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        # Cache control for static files
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000'
        
        return response
    
    # Request logging middleware
    @app.before_request
    def before_request():
        """Log incoming requests"""
        # Skip logging for static files and health checks
        if not request.path.startswith('/static/') and request.path != '/health':
            app.logger.info(f"{request.method} {request.path} - {request.remote_addr}")
    
    return app


def setup_logging(app):
    """Setup application logging"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Set logging level based on environment
    log_level = logging.DEBUG if app.debug else logging.INFO
    
    # File handler for errors
    error_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    # File handler for all logs
    app_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    app_handler.setLevel(log_level)
    app_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    
    # Add handlers
    app.logger.addHandler(error_handler)
    app.logger.addHandler(app_handler)
    app.logger.setLevel(log_level)
    app.logger.info('Application startup')


def check_database_connection():
    """Check if database connection is working"""
    try:
        # Simple query to test connection
        result = SupabaseService.get_client().table('profiles').select('id', count='exact').limit(1).execute()
        return True if result else False
    except Exception:
        return False


# ============================================
# ERROR TEMPLATES (Embedded for simplicity)
# ============================================

def create_error_templates(app):
    """Create error templates if they don't exist"""
    error_templates = {
        'errors/400.html': '''
            {% extends "base.html" %}
            {% block title %}400 - Bad Request{% endblock %}
            {% block content %}
            <div class="min-h-[70vh] flex items-center justify-center">
                <div class="text-center">
                    <h1 class="text-6xl font-bold text-navy-900">400</h1>
                    <p class="text-xl text-gray-600 mt-4">Bad Request</p>
                    <a href="/" class="mt-6 inline-block px-6 py-3 bg-navy-900 text-white rounded-xl">Go Home</a>
                </div>
            </div>
            {% endblock %}
        ''',
        'errors/403.html': '''
            {% extends "base.html" %}
            {% block title %}403 - Forbidden{% endblock %}
            {% block content %}
            <div class="min-h-[70vh] flex items-center justify-center">
                <div class="text-center">
                    <h1 class="text-6xl font-bold text-navy-900">403</h1>
                    <p class="text-xl text-gray-600 mt-4">Access Denied</p>
                    <a href="/" class="mt-6 inline-block px-6 py-3 bg-navy-900 text-white rounded-xl">Go Home</a>
                </div>
            </div>
            {% endblock %}
        ''',
        'errors/404.html': '''
            {% extends "base.html" %}
            {% block title %}404 - Page Not Found{% endblock %}
            {% block content %}
            <div class="min-h-[70vh] flex items-center justify-center">
                <div class="text-center">
                    <h1 class="text-6xl font-bold text-navy-900">404</h1>
                    <p class="text-xl text-gray-600 mt-4">Page Not Found</p>
                    <a href="/" class="mt-6 inline-block px-6 py-3 bg-navy-900 text-white rounded-xl">Go Home</a>
                </div>
            </div>
            {% endblock %}
        ''',
        'errors/500.html': '''
            {% extends "base.html" %}
            {% block title %}500 - Server Error{% endblock %}
            {% block content %}
            <div class="min-h-[70vh] flex items-center justify-center">
                <div class="text-center">
                    <h1 class="text-6xl font-bold text-navy-900">500</h1>
                    <p class="text-xl text-gray-600 mt-4">Internal Server Error</p>
                    <a href="/" class="mt-6 inline-block px-6 py-3 bg-navy-900 text-white rounded-xl">Go Home</a>
                </div>
            </div>
            {% endblock %}
        '''
    }
    
    os.makedirs('templates/errors', exist_ok=True)
    for path, content in error_templates.items():
        full_path = os.path.join('templates', path)
        if not os.path.exists(full_path):
            with open(full_path, 'w') as f:
                f.write(content.strip())


# ============================================
# APPLICATION ENTRY POINT
# ============================================

# Create the application instance
application = create_app()

# Create error templates
with application.app_context():
    create_error_templates(application)

# Import here to avoid circular imports
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.api import api_bp
from routes.admin import admin_bp

if __name__ == '__main__':
    # Get port from environment variable (for Vercel/Railway)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    
    application.run(
        debug=debug,
        host='0.0.0.0',
        port=port,
        threaded=True
    )