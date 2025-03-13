from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os
from typing import Dict, Any, Optional, List
import logging
import uuid

class UserManager:
    def __init__(self):
        """Initialize UserManager with MongoDB connection"""
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.client = MongoClient(mongo_uri)
        self.db = self.client['renewable_energy_consultant']
        
        # Collections
        self.users = self.db['users']
        self.chat_history = self.db['chat_history']
        self.dashboards = self.db['dashboards']
        
        # Create indexes
        self.users.create_index('email', unique=True)
        self.users.create_index('username', unique=True)
        self.chat_history.create_index([('user_id', 1), ('timestamp', -1)])
        self.dashboards.create_index([('user_id', 1), ('created_at', -1)])
        self.dashboards.create_index('is_public')  # Add index for public dashboards
    
    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        try:
            # Check if user already exists
            if self.users.find_one({'$or': [{'email': email}, {'username': username}]}):
                raise ValueError('Username or email already exists')
            
            # Create user document
            user = {
                'username': username,
                'email': email,
                'password': generate_password_hash(password),
                'created_at': datetime.datetime.now(),
                'last_login': None,
                'preferences': {
                    'default_dashboard_type': 'cbg',
                    'auto_refresh': True,
                    'refresh_interval': 300
                }
            }
            
            result = self.users.insert_one(user)
            user['_id'] = result.inserted_id
            
            return self.generate_auth_token(user)
            
        except Exception as e:
            logging.error(f"Error registering user: {str(e)}")
            raise
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login a user"""
        try:
            user = self.users.find_one({'email': email})
            if not user or not check_password_hash(user['password'], password):
                raise ValueError('Invalid email or password')
            
            # Update last login
            self.users.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.datetime.now()}}
            )
            
            return self.generate_auth_token(user)
            
        except Exception as e:
            logging.error(f"Error logging in user: {str(e)}")
            raise
    
    def generate_auth_token(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JWT token for user"""
        token = jwt.encode(
            {
                'user_id': str(user['_id']),
                'username': user['username'],
                'exp': datetime.datetime.now() + datetime.timedelta(days=7)
            },
            os.getenv('JWT_SECRET_KEY', 'your-secret-key'),
            algorithm='HS256'
        )
        
        return {
            'token': token,
            'user': {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'preferences': user['preferences']
            }
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user info"""
        try:
            payload = jwt.decode(
                token,
                os.getenv('JWT_SECRET_KEY', 'your-secret-key'),
                algorithms=['HS256']
            )
            
            user = self.users.find_one({'_id': payload['user_id']})
            return user if user else None
            
        except jwt.ExpiredSignatureError:
            raise ValueError('Token has expired')
        except jwt.InvalidTokenError:
            raise ValueError('Invalid token')
    
    def save_chat_history(self, user_id: str, messages: List[Dict[str, Any]]) -> str:
        """Save chat history for a user"""
        try:
            chat_session = {
                'user_id': user_id,
                'messages': messages,
                'timestamp': datetime.datetime.now()
            }
            
            result = self.chat_history.insert_one(chat_session)
            return str(result.inserted_id)
            
        except Exception as e:
            logging.error(f"Error saving chat history: {str(e)}")
            raise
    
    def get_chat_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a user"""
        try:
            return list(
                self.chat_history.find(
                    {'user_id': user_id},
                    {'messages': 1, 'timestamp': 1}
                ).sort('timestamp', -1).limit(limit)
            )
        except Exception as e:
            logging.error(f"Error getting chat history: {str(e)}")
            raise
    
    def save_dashboard(self, user_id: str, dashboard: Dict[str, Any]) -> str:
        """Save dashboard for a user"""
        try:
            dashboard['user_id'] = user_id
            dashboard['is_public'] = dashboard.get('is_public', False)
            dashboard['public_url'] = None
            
            if dashboard['is_public']:
                # Generate a public URL token
                public_token = str(uuid.uuid4())
                dashboard['public_url'] = f"/public/dashboards/{public_token}"
            
            result = self.dashboards.insert_one(dashboard)
            return str(result.inserted_id)
            
        except Exception as e:
            logging.error(f"Error saving dashboard: {str(e)}")
            raise
    
    def get_user_dashboards(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all dashboards for a user"""
        try:
            return list(
                self.dashboards.find({'user_id': user_id})
                .sort('created_at', -1)
            )
        except Exception as e:
            logging.error(f"Error getting user dashboards: {str(e)}")
            raise
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific dashboard"""
        try:
            return self.dashboards.find_one({'_id': dashboard_id})
        except Exception as e:
            logging.error(f"Error getting dashboard: {str(e)}")
            raise
    
    def delete_dashboard(self, user_id: str, dashboard_id: str) -> bool:
        """Delete a dashboard"""
        try:
            result = self.dashboards.delete_one({
                '_id': dashboard_id,
                'user_id': user_id
            })
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Error deleting dashboard: {str(e)}")
            raise
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        try:
            result = self.users.update_one(
                {'_id': user_id},
                {'$set': {'preferences': preferences}}
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Error updating user preferences: {str(e)}")
            raise
    
    def get_public_dashboard(self, public_token: str) -> Optional[Dict[str, Any]]:
        """Get a public dashboard by its token"""
        try:
            return self.dashboards.find_one({
                'public_url': f"/public/dashboards/{public_token}",
                'is_public': True
            })
        except Exception as e:
            logging.error(f"Error getting public dashboard: {str(e)}")
            raise
    
    def set_dashboard_visibility(self, user_id: str, dashboard_id: str, is_public: bool) -> Dict[str, Any]:
        """Set dashboard visibility (public/private)"""
        try:
            dashboard = self.dashboards.find_one({
                '_id': dashboard_id,
                'user_id': user_id
            })
            
            if not dashboard:
                raise ValueError('Dashboard not found')
            
            update_data = {'is_public': is_public}
            
            if is_public and not dashboard.get('public_url'):
                # Generate public URL if making public
                public_token = str(uuid.uuid4())
                update_data['public_url'] = f"/public/dashboards/{public_token}"
            elif not is_public:
                # Remove public URL if making private
                update_data['public_url'] = None
            
            self.dashboards.update_one(
                {'_id': dashboard_id},
                {'$set': update_data}
            )
            
            # Return updated dashboard
            return self.dashboards.find_one({'_id': dashboard_id})
            
        except Exception as e:
            logging.error(f"Error setting dashboard visibility: {str(e)}")
            raise
    
    def get_public_dashboards(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of public dashboards"""
        try:
            return list(
                self.dashboards.find(
                    {'is_public': True},
                    {
                        'title': 1,
                        'description': 1,
                        'type': 1,
                        'public_url': 1,
                        'created_at': 1,
                        'updated_at': 1
                    }
                ).sort('created_at', -1).limit(limit)
            )
        except Exception as e:
            logging.error(f"Error getting public dashboards: {str(e)}")
            raise 