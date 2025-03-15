import hashlib
import jwt
import datetime
import os
from typing import Dict, Any, Optional, List
import logging
import uuid

def simple_hash(password: str) -> str:
    """Simple password hashing using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(hashed_password: str, password: str) -> bool:
    """Check if password matches the hash"""
    return hashed_password == simple_hash(password)

class UserManager:
    def __init__(self):
        """Initialize UserManager with in-memory storage"""
        # In-memory storage
        self.users = {}
        self.chat_history = {}
        self.dashboards = {}
        
        # Create a default admin user
        default_user_id = str(uuid.uuid4())
        self.users[default_user_id] = {
            '_id': default_user_id,
            'username': 'admin',
            'email': 'admin@example.com',
            'password': simple_hash('admin'),
            'created_at': datetime.datetime.now(),
            'last_login': None,
            'preferences': {
                'default_dashboard_type': 'cbg',
                'auto_refresh': True,
                'refresh_interval': 300
            }
        }
        
        logging.info("UserManager initialized with in-memory storage")
    
    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        try:
            # Check if user already exists
            for user in self.users.values():
                if user['email'] == email or user['username'] == username:
                    raise ValueError('Username or email already exists')
            
            # Create user document
            user_id = str(uuid.uuid4())
            user = {
                '_id': user_id,
                'username': username,
                'email': email,
                'password': simple_hash(password),
                'created_at': datetime.datetime.now(),
                'last_login': None,
                'preferences': {
                    'default_dashboard_type': 'cbg',
                    'auto_refresh': True,
                    'refresh_interval': 300
                }
            }
            
            self.users[user_id] = user
            
            return self.generate_auth_token(user)
            
        except Exception as e:
            logging.error(f"Error registering user: {str(e)}")
            raise
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login a user"""
        try:
            user = None
            for u in self.users.values():
                if u['email'] == email:
                    user = u
                    break
                    
            if not user or not check_password(user['password'], password):
                raise ValueError('Invalid email or password')
            
            # Update last login
            user['last_login'] = datetime.datetime.now()
            
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
            
            user_id = payload['user_id']
            return self.users.get(user_id)
            
        except jwt.ExpiredSignatureError:
            raise ValueError('Token has expired')
        except jwt.InvalidTokenError:
            raise ValueError('Invalid token')
    
    def save_chat_history(self, user_id: str, messages: List[Dict[str, Any]]) -> str:
        """Save chat history for a user"""
        try:
            chat_id = str(uuid.uuid4())
            
            if user_id not in self.chat_history:
                self.chat_history[user_id] = []
                
            chat_session = {
                '_id': chat_id,
                'user_id': user_id,
                'messages': messages,
                'timestamp': datetime.datetime.now()
            }
            
            self.chat_history[user_id].append(chat_session)
            return chat_id
            
        except Exception as e:
            logging.error(f"Error saving chat history: {str(e)}")
            raise
    
    def get_chat_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a user"""
        try:
            if user_id not in self.chat_history:
                return []
                
            # Sort by timestamp and limit
            history = sorted(
                self.chat_history[user_id],
                key=lambda x: x['timestamp'],
                reverse=True
            )
            
            return history[:limit]
            
        except Exception as e:
            logging.error(f"Error getting chat history: {str(e)}")
            raise
    
    def save_dashboard(self, user_id: str, dashboard: Dict[str, Any]) -> str:
        """Save dashboard for a user"""
        try:
            dashboard_id = str(uuid.uuid4())
            
            if user_id not in self.dashboards:
                self.dashboards[user_id] = {}
                
            dashboard['_id'] = dashboard_id
            dashboard['user_id'] = user_id
            dashboard['is_public'] = dashboard.get('is_public', False)
            dashboard['public_url'] = None
            dashboard['created_at'] = datetime.datetime.now()
            
            if dashboard['is_public']:
                # Generate a public URL token
                public_token = str(uuid.uuid4())
                dashboard['public_url'] = f"/public/dashboards/{public_token}"
            
            self.dashboards[user_id][dashboard_id] = dashboard
            return dashboard_id
            
        except Exception as e:
            logging.error(f"Error saving dashboard: {str(e)}")
            raise
    
    def get_user_dashboards(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all dashboards for a user"""
        try:
            if user_id not in self.dashboards:
                return []
                
            # Sort by created_at
            dashboards = list(self.dashboards[user_id].values())
            return sorted(
                dashboards,
                key=lambda x: x['created_at'],
                reverse=True
            )
            
        except Exception as e:
            logging.error(f"Error getting user dashboards: {str(e)}")
            raise
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific dashboard"""
        try:
            for user_dashboards in self.dashboards.values():
                if dashboard_id in user_dashboards:
                    return user_dashboards[dashboard_id]
            return None
            
        except Exception as e:
            logging.error(f"Error getting dashboard: {str(e)}")
            raise
    
    def delete_dashboard(self, user_id: str, dashboard_id: str) -> bool:
        """Delete a dashboard"""
        try:
            if user_id not in self.dashboards or dashboard_id not in self.dashboards[user_id]:
                return False
                
            del self.dashboards[user_id][dashboard_id]
            return True
            
        except Exception as e:
            logging.error(f"Error deleting dashboard: {str(e)}")
            raise
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        try:
            if user_id not in self.users:
                return False
                
            self.users[user_id]['preferences'] = preferences
            return True
            
        except Exception as e:
            logging.error(f"Error updating user preferences: {str(e)}")
            raise
    
    def get_public_dashboard(self, public_token: str) -> Optional[Dict[str, Any]]:
        """Get a public dashboard by its token"""
        try:
            public_url = f"/public/dashboards/{public_token}"
            
            for user_dashboards in self.dashboards.values():
                for dashboard in user_dashboards.values():
                    if dashboard.get('public_url') == public_url and dashboard.get('is_public'):
                        return dashboard
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting public dashboard: {str(e)}")
            raise
    
    def set_dashboard_visibility(self, user_id: str, dashboard_id: str, is_public: bool) -> Dict[str, Any]:
        """Set dashboard visibility (public/private)"""
        try:
            if user_id not in self.dashboards or dashboard_id not in self.dashboards[user_id]:
                raise ValueError('Dashboard not found')
                
            dashboard = self.dashboards[user_id][dashboard_id]
            dashboard['is_public'] = is_public
            
            if is_public and not dashboard.get('public_url'):
                # Generate public URL if making public
                public_token = str(uuid.uuid4())
                dashboard['public_url'] = f"/public/dashboards/{public_token}"
            elif not is_public:
                # Remove public URL if making private
                dashboard['public_url'] = None
            
            return dashboard
            
        except Exception as e:
            logging.error(f"Error setting dashboard visibility: {str(e)}")
            raise
    
    def get_public_dashboards(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all public dashboards"""
        try:
            public_dashboards = []
            
            for user_dashboards in self.dashboards.values():
                for dashboard in user_dashboards.values():
                    if dashboard.get('is_public'):
                        public_dashboards.append(dashboard)
            
            # Sort by created_at
            public_dashboards = sorted(
                public_dashboards,
                key=lambda x: x['created_at'],
                reverse=True
            )
            
            return public_dashboards[:limit]
            
        except Exception as e:
            logging.error(f"Error getting public dashboards: {str(e)}")
            raise 