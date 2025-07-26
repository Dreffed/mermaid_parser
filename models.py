# ===== models.py =====
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PlatformConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False, unique=True)
    client_id = db.Column(db.String(200))
    client_secret = db.Column(db.String(200))
    redirect_url = db.Column(db.String(200))
    additional_config = db.Column(db.Text, default='{}')  # JSON string
    is_active = db.Column(db.Boolean, default=True)
    last_tested = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_config(self):
        """Return configuration as dictionary"""
        base_config = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_url': self.redirect_url
        }

        try:
            additional = json.loads(self.additional_config or '{}')
            base_config.update(additional)
        except json.JSONDecodeError:
            pass

        return base_config

class ConversionHistory(db.Model):
    id = db.Column(db.String(36), primary_key=True)  # UUID
    source_code = db.Column(db.Text, nullable=False)
    target_platform = db.Column(db.String(50), nullable=False)
    result_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')  # pending, success, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'source_code': self.source_code,
            'target_platform': self.target_platform,
            'result_url': self.result_url,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat()
        }

