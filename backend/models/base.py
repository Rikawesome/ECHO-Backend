"""
Base model with common fields for all models.
This will be inherited by all other models.
"""
from datetime import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy

# We'll get db from app.py later
db = SQLAlchemy()

def generate_uuid():
    """Generate a UUID string for primary keys"""
    return str(uuid.uuid4())

class BaseModel(db.Model):
    """
    Abstract base model that all other models will inherit from.
    Contains common fields like id, created_at, updated_at.
    """
    __abstract__ = True  # This means SQLAlchemy won't create a table for this class
    
    # Primary key using UUID (better than auto-increment integers)
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    
    # Timestamps for tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """
        Convert model instance to dictionary.
        Useful for API responses.
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Handle datetime objects (convert to ISO format)
            if isinstance(value, datetime):
                value = value.isoformat()
            
            result[column.name] = value
        
        return result
    
    def update(self, **kwargs):
        """
        Update model fields from keyword arguments.
        Returns self for method chaining.
        
        Example: user.update(first_name='John', last_name='Doe')
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Always update the updated_at timestamp
        self.updated_at = datetime.utcnow()
        return self
    
    def __repr__(self):
        """String representation of the model"""
        return f'<{self.__class__.__name__} {self.id}>'