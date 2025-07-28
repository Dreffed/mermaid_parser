# ===== app.py =====
import os
import json
import uuid
import traceback

from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
# from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, logout_user, login_required, current_user, LoginManager, UserMixin
from dotenv import load_dotenv

# Import our custom modules
from models import db, User, PlatformConfig, ConversionHistory
from mermaid_parser  import MermaidParser, MermaidParseError
from converters.miro_converter import MiroConverter
from converters.base_converter import ConversionError

load_dotenv()

app = Flask(__name__)

# Database Configuration
database_url = os.environ.get('DATABASE_URL')

# Handle both old and new PostgreSQL URL formats
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'postgresql://localhost/mermaid_converter'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# PostgreSQL-specific optimizations
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,          # Verify connections before use
    'pool_recycle': 300,            # Recycle connections every 5 minutes
    'connect_args': {
        'connect_timeout': 10,      # Connection timeout
        'application_name': 'mermaid_converter'  # App identification in PostgreSQL logs
    }
}

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize parser
mermaid_parser = MermaidParser()

with app.app_context():
    db.create_all()
    # Create default admin user if none exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')  # Change this in production!
        db.session.add(admin)
        db.session.commit()
        print('Admin User added!')
    print('Database initialized successfully!')

# Add custom Jinja2 filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Convert JSON string to Python object"""
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}

@app.template_filter('to_json')
def to_json_filter(value):
    """Convert Python object to JSON string"""
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return '{}'

# Main Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parse', methods=['POST'])
def parse_mermaid():
    """Parse Mermaid diagram and return structure or errors"""
    try:
        data = request.get_json()
        mermaid_code = data.get('code', '')

        if not mermaid_code.strip():
            return jsonify({'error': 'No Mermaid code provided'}), 400

        # Parse the Mermaid code
        result = mermaid_parser.parse(mermaid_code)

        return jsonify({
            'success': True,
            'diagram_type': result['type'],
            'nodes': [node.__dict__ for node in result['nodes']],
            'edges': [edge.__dict__ for edge in result['edges']],
            'metadata': result.get('metadata', {})
        })

    except MermaidParseError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'line': getattr(e, 'line_number', None),
            'details': getattr(e, 'details', None)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/api/convert', methods=['POST'])
def convert_diagram():
    """Convert parsed Mermaid diagram to target platform"""
    try:
        data = request.get_json()
        mermaid_code = data.get('code', '')
        target_platform = data.get('platform', 'miro')
        options = data.get('options', {})

        if not mermaid_code.strip():
            return jsonify({'error': 'No Mermaid code provided'}), 400

        # Parse first
        parsed_result = mermaid_parser.parse(mermaid_code)

        # Get platform configuration
        platform_config = PlatformConfig.query.filter_by(
            platform=target_platform,
            is_active=True
        ).first()

        if not platform_config:
            return jsonify({
                'error': f'No active configuration found for {target_platform}. Please configure in admin panel.'
            }), 400

        # Initialize converter
        if target_platform == 'miro':
            converter = MiroConverter(platform_config.get_config())
        else:
            return jsonify({'error': f'Platform {target_platform} not yet supported'}), 400

        # Perform conversion
        conversion_result = converter.convert(parsed_result, options)

        # Save to history
        history = ConversionHistory(
            id=str(uuid.uuid4()),
            source_code=mermaid_code,
            target_platform=target_platform,
            result_url=conversion_result.get('url'),
            status='success',
            created_at=datetime.utcnow()
        )
        db.session.add(history)
        db.session.commit()

        return jsonify({
            'success': True,
            'conversion_id': history.id,
            'platform': target_platform,
            'url': conversion_result.get('url'),
            'board_id': conversion_result.get('board_id'),
            'message': f'Successfully converted to {target_platform}!'
        })

    except ConversionError as e:
        return jsonify({
            'success': False,
            'error': f'Conversion failed: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/api/platforms')
def get_platforms():
    """Get available platforms and their status"""
    platforms = PlatformConfig.query.filter_by(is_active=True).all()
    return jsonify({
        'platforms': [
            {
                'name': p.platform,
                'display_name': p.platform.title(),
                'configured': bool(p.client_id and p.client_secret),
                'last_tested': p.last_tested.isoformat() if p.last_tested else None
            }
            for p in platforms
        ]
    })

@app.route('/api/history')
def get_history():
    """Get conversion history"""
    history = ConversionHistory.query.order_by(ConversionHistory.created_at.desc()).limit(50).all()
    return jsonify({
        'history': [
            {
                'id': h.id,
                'platform': h.target_platform,
                'status': h.status,
                'url': h.result_url,
                'created_at': h.created_at.isoformat(),
                'preview': h.source_code[:100] + '...' if len(h.source_code) > 100 else h.source_code
            }
            for h in history
        ]
    })

# Admin Routes
@app.route('/admin')
def admin():
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials or not authorized')

    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('index'))

    platforms = PlatformConfig.query.all()
    recent_conversions = ConversionHistory.query.order_by(ConversionHistory.created_at.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                         platforms=platforms,
                         recent_conversions=recent_conversions)

@app.route('/admin/platforms/<platform>', methods=['GET', 'POST'])
@login_required
def admin_platform_config(platform):
    if not current_user.is_admin:
        return redirect(url_for('index'))

    config = PlatformConfig.query.filter_by(platform=platform).first()
    if not config:
        config = PlatformConfig(platform=platform)
        db.session.add(config)

    if request.method == 'POST':
        config.client_id = request.form.get('client_id')
        config.client_secret = request.form.get('client_secret')
        config.redirect_url = request.form.get('redirect_url')
        config.additional_config = request.form.get('additional_config', '{}')
        config.is_active = 'is_active' in request.form

        try:
            db.session.commit()
            flash(f'{platform.title()} configuration saved successfully!')
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving configuration: {str(e)}')

    # Parse additional_config for template
    additional_config = {}
    if config and config.additional_config:
        try:
            additional_config = json.loads(config.additional_config)
        except (json.JSONDecodeError, TypeError):
            additional_config = {}

    return render_template('admin/platform_config.html',
                         platform=platform,
                         config=config,
                         additional_config=additional_config)  # Pass parsed config

@app.route('/admin/test/<platform>')
@login_required
def test_platform(platform):
    """Test platform connection"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    config = PlatformConfig.query.filter_by(platform=platform).first()
    if not config:
        return jsonify({'error': 'Platform not configured'}), 400

    try:
        if platform == 'miro':
            converter = MiroConverter(config.get_config())
            result = converter.test_connection()
        else:
            return jsonify({'error': f'Testing not implemented for {platform}'}), 400

        config.last_tested = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/admin/miro/oauth/start')
@login_required
def miro_oauth_start():
    """Start Miro OAuth flow"""
    if not current_user.is_admin:
        return redirect(url_for('index'))

    config = PlatformConfig.query.filter_by(platform='miro').first()
    if not config or not config.client_id:
        flash('Miro OAuth not configured. Please add client_id and client_secret first.')
        return redirect(url_for('admin_platform_config', platform='miro'))

    try:
        converter = MiroConverter(config.get_config())
        auth_url = converter.get_auth_url(state='admin_oauth')
        return redirect(auth_url)
    except Exception as e:
        flash(f'Error starting OAuth flow: {str(e)}')
        return redirect(url_for('admin_platform_config', platform='miro'))

@app.route('/admin/miro/oauth/callback')
@login_required
def miro_oauth_callback():
    """Handle Miro OAuth callback"""
    if not current_user.is_admin:
        return redirect(url_for('index'))

    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        flash(f'OAuth error: {error}')
        return redirect(url_for('admin_platform_config', platform='miro'))

    if not code:
        flash('No authorization code received')
        return redirect(url_for('admin_platform_config', platform='miro'))

    config = PlatformConfig.query.filter_by(platform='miro').first()
    if not config:
        flash('Miro configuration not found')
        return redirect(url_for('admin_platform_config', platform='miro'))

    try:
        converter = MiroConverter(config.get_config())
        token_response = converter.exchange_code_for_token(code)

        # Update configuration with tokens
        additional_config = json.loads(config.additional_config or '{}')
        additional_config['access_token'] = token_response.get('access_token')
        additional_config['refresh_token'] = token_response.get('refresh_token')
        additional_config['token_type'] = token_response.get('token_type', 'Bearer')
        additional_config['expires_in'] = token_response.get('expires_in')

        config.additional_config = json.dumps(additional_config)
        db.session.commit()

        flash('✅ Miro OAuth completed successfully! Access token saved.')
        return redirect(url_for('admin_platform_config', platform='miro'))

    except Exception as e:
        flash(f'OAuth callback error: {str(e)}')
        return redirect(url_for('admin_platform_config', platform='miro'))

@app.route('/admin/miro/oauth/refresh')
@login_required
def miro_oauth_refresh():
    """Manually refresh Miro access token"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    config = PlatformConfig.query.filter_by(platform='miro').first()
    if not config:
        return jsonify({'error': 'Miro not configured'}), 400

    try:
        converter = MiroConverter(config.get_config())
        token_response = converter.refresh_access_token()

        # Update stored tokens
        additional_config = json.loads(config.additional_config or '{}')
        additional_config['access_token'] = token_response.get('access_token')
        if 'refresh_token' in token_response:
            additional_config['refresh_token'] = token_response.get('refresh_token')

        config.additional_config = json.dumps(additional_config)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Access token refreshed successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/debug/miro/endpoints')
@login_required
def debug_miro_endpoints():
    """Debug Miro OAuth endpoints"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'correct_endpoints': {
            'authorize_url': 'https://miro.com/oauth/authorize',
            'token_url': 'https://api.miro.com/v1/oauth/token',
            'api_base': 'https://api.miro.com/v2'
        },
        'incorrect_endpoints': {
            'wrong_token_url': 'https://miro.com/oauth/token/',  # This was causing 404
            'wrong_token_url2': 'https://miro.com/oauth/token'
        },
        'test_urls': {
            'auth_test': 'https://miro.com/oauth/authorize?response_type=code&client_id=test',
            'api_test': 'https://api.miro.com/v2/users/me'
        }
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
