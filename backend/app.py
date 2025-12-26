# app.py
from flask import Flask, jsonify, request, render_template, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from flask_cors import CORS
import os
from dotenv import load_dotenv
import importlib
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def get_database_uri():
    """Get database URI with Railway/PostgreSQL support"""
    db_url = os.environ.get("DATABASE_URL")
    
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        print("[DB] Using PostgreSQL (Railway)")
        return db_url
    
    print("[DB] Using SQLite (local development)")
    return "sqlite:///echo_platform.db"

def register_blueprints(app):
    """Register all blueprints with proper error handling"""
    print("\n" + "="*60)
    print("[INIT] REGISTERING BLUEPRINTS")
    print("="*60)
    
    # List of all blueprints to register (in order of importance)
    blueprints_to_register = [
        ('auth', 'auth_bp'),
        ('schools', 'schools_bp'),
        ('teachers', 'teachers_bp'),
        ('students', 'students_bp'),
        ('classes', 'classes_bp'),
        ('subjects', 'subjects_bp'),
        ('users', 'users_bp'),
        ('dashboard', 'dashboard_bp'),
        ('utils', 'utils_bp')
    ]
    
    registered_count = 0
    
    for module_name, bp_name in blueprints_to_register:
        try:
            print(f"\n[PKG] Attempting: routes.{module_name}...")
            
            # Import the module
            module = importlib.import_module(f'routes.{module_name}')
            
            # Get the blueprint
            blueprint = getattr(module, bp_name)
            
            # Verify it's a Blueprint
            if isinstance(blueprint, Blueprint):
                # Register the blueprint
                app.register_blueprint(blueprint)
                registered_count += 1
                print(f"   [OK] SUCCESS: Registered '{blueprint.name}'")
                
                # Show what routes it provides
                if hasattr(blueprint, 'deferred_functions'):
                    print(f"   [*] Provides {len(blueprint.deferred_functions)} endpoint(s)")
            else:
                print(f"   [ERR] FAILED: {bp_name} is not a Blueprint object")
                
        except ImportError as e:
            print(f"   [ERR] FAILED: Cannot import routes.{module_name}")
            print(f"      Error: {e}")
        except AttributeError:
            print(f"   [ERR] FAILED: No '{bp_name}' found in routes.{module_name}")
        except Exception as e:
            print(f"   [ERR] FAILED: Error with routes.{module_name}")
            print(f"      Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"[SUMMARY] REGISTRATION SUMMARY")
    print("="*60)
    print(f"[OK] Successfully registered: {registered_count}/{len(blueprints_to_register)} blueprints")
    
    if registered_count == 0:
        print("[WARN] WARNING: No blueprints registered! Check your routes/ directory.")
    elif registered_count < len(blueprints_to_register):
        print("[WARN] WARNING: Some blueprints failed to register.")
    else:
        print("[OK] SUCCESS: All blueprints registered successfully!")
    
    # List all registered blueprints
    print("\n[LIST] Registered Blueprints:")
    for name, blueprint in app.blueprints.items():
        print(f"   - {name}: {blueprint}")
    
    print("="*60 + "\n")

def setup_database(app):
    """Setup database tables and handle migrations"""
    with app.app_context():
        try:
            print("[INIT] Setting up database...")
            
            # Import all models to ensure they're registered
            print("[IMPORT] Importing models...")
            from models.school import School
            from models.user import User
            from models.teacher import Teacher
            from models.student import Student
            from models.class_model import Class
            from models.subject import Subject
            print("[OK] All models imported")
            
            # Check if we're using PostgreSQL
            is_postgres = 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']
            
            if is_postgres:
                # For PostgreSQL, we should use migrations
                try:
                    print("[MIGRATE] Running migrations for PostgreSQL...")
                    upgrade()
                    print("[OK] Migrations applied successfully")
                except Exception as e:
                    print(f"[WARN] Migration error, falling back to create_all: {e}")
                    db.create_all()
                    print("[OK] Tables created directly")
            else:
                # For SQLite, create tables directly
                db.create_all()
                print("[OK] SQLite tables created")
            
            print("[OK] Database setup complete")
            
        except Exception as e:
            print(f"[ERR] Database setup error: {e}")
            import traceback
            traceback.print_exc()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # ============ CONFIGURATION ============
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'echo-platform-dev-key-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    
    # Debug mode based on environment
    app.config['DEBUG'] = os.environ.get('FLASK_ENV') == 'development'
    
    # ============ INITIALIZE EXTENSIONS ============
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # ============ SETUP DATABASE ============
    setup_database(app)
    
    # ============ REGISTER BLUEPRINTS ============
    register_blueprints(app)
    
    # ============ BASIC ROUTES ============
    @app.route('/')
    def home():
        """API home page"""
        return jsonify({
            'service': 'Echo School Platform API',
            'version': '1.0.0',
            'status': 'active',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite',
            'endpoints': {
                'health': '/health',
                'docs': '/docs',
                'debug': '/debug/routes',
                'auth': '/auth/*',
                'schools': '/schools/*',
                'teachers': '/teachers/*',
                'students': '/students/*',
                'classes': '/classes/*',
                'subjects': '/subjects/*',
                'users': '/users/*',
                'dashboard': '/dashboard/*',
                'utils': '/utils/*'
            }
        })
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db_status,
            'service': 'Echo Platform API',
            'registered_blueprints': list(app.blueprints.keys())
        })
    
    @app.route('/docs')
    @app.route('/api-docs')
    def api_documentation():
        """Serve API documentation HTML page"""
        try:
            return render_template('api_docs.html')
        except Exception as e:
            return jsonify({
                'message': 'API Documentation',
                'error': 'HTML template not found',
                'available_endpoints': list(app.blueprints.keys())
            })
    
    @app.route('/api')
    def api_overview():
        """JSON API overview"""
        return jsonify({
            'api': 'Echo Platform API',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'base_url': request.host_url.rstrip('/'),
            'blueprints': list(app.blueprints.keys()),
            'endpoints': {
                'auth': '/auth/*',
                'schools': '/schools/*',
                'teachers': '/teachers/*',
                'students': '/students/*',
                'classes': '/classes/*',
                'subjects': '/subjects/*',
                'users': '/users/*',
                'dashboard': '/dashboard/*',
                'utils': '/utils/*'
            }
        })
    
    @app.route('/debug/routes')
    def list_routes():
        """Debug endpoint to list all registered routes"""
        routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':  # Skip static files
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'path': str(rule)
                })
        
        # Group by blueprint
        grouped_routes = {}
        for route in routes:
            # Extract blueprint name from endpoint (format: blueprint.endpoint_name)
            if '.' in route['endpoint']:
                blueprint_name = route['endpoint'].split('.')[0]
                if blueprint_name not in grouped_routes:
                    grouped_routes[blueprint_name] = []
                grouped_routes[blueprint_name].append(route)
            else:
                # Main app routes (not from blueprints)
                if 'main' not in grouped_routes:
                    grouped_routes['main'] = []
                grouped_routes['main'].append(route)
        
        return jsonify({
            'total_routes': len(routes),
            'blueprints': list(app.blueprints.keys()),
            'grouped_routes': grouped_routes,
            'all_routes': routes
        })
    
    @app.route('/debug/blueprints')
    def debug_blueprints():
        """Debug endpoint to show registered blueprints"""
        blueprints_info = []
        for name, blueprint in app.blueprints.items():
            blueprints_info.append({
                'name': name,
                'url_prefix': blueprint.url_prefix,
                'import_name': blueprint.import_name,
                'has_routes': len(blueprint.deferred_functions) if hasattr(blueprint, 'deferred_functions') else 0
            })
        
        return jsonify({
            'count': len(blueprints_info),
            'blueprints': blueprints_info,
            'app_blueprints': list(app.blueprints.keys())
        })
    
    @app.route('/test-auth')
    def test_auth():
        """Quick test for auth routes"""
        return jsonify({
            'message': 'If you can see this, auth routes are not working',
            'expected_auth_routes': [
                '/auth/register/school-owner (POST)',
                '/auth/register/teacher (POST)',
                '/auth/register/student (POST)',
                '/auth/login (POST)'
            ]
        })
    
    # ============ ERROR HANDLERS ============
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': f'The requested endpoint {request.path} does not exist.',
            'timestamp': datetime.utcnow().isoformat(),
            'available_blueprints': list(app.blueprints.keys()),
            'suggestions': [
                '/health',
                '/docs',
                '/api',
                '/debug/routes',
                '/debug/blueprints'
            ]
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal Server Error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred on the server.',
            'timestamp': datetime.utcnow().isoformat(),
            'request_path': request.path
        }), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': str(error),
            'timestamp': datetime.utcnow().isoformat()
        }), 400
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'error': 'Method Not Allowed',
            'message': f'The method {request.method} is not allowed for this endpoint.',
            'timestamp': datetime.utcnow().isoformat(),
            'path': request.path
        }), 405
    
    # ============ FAVICON HANDLER ============
    @app.route('/favicon.ico')
    def favicon():
        return '', 204
    
    return app

# ============ CREATE APP INSTANCE ============
app = create_app()

# ============ MAIN ENTRY POINT ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("\n" + "="*60)
    print("[START] ECHO SCHOOL PLATFORM API")
    print("="*60)
    print(f"[ENV] Environment: {'Development' if debug else 'Production'}")
    print(f"[PORT] Port: {port}")
    print(f"[DB] Database: {app.config['SQLALCHEMY_DATABASE_URI'].split('://')[0]}")
    print(f"[DEBUG] Debug Mode: {debug}")
    print("="*60)
    print(f"[URL] URL: http://localhost:{port}")
    print(f"[HEALTH] Health: http://localhost:{port}/health")
    print(f"[DOCS] Docs: http://localhost:{port}/docs")
    print(f"[DEBUG] Debug Routes: http://localhost:{port}/debug/routes")
    print(f"[DEBUG] Debug Blueprints: http://localhost:{port}/debug/blueprints")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)