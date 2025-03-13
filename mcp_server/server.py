from quart import Quart, request, jsonify
from dotenv import load_dotenv
import jwt
import uuid
import datetime
import os
from functools import wraps
from mcp_server.data_sources import DataAggregator
from mcp_server.dashboard_factory import DashboardFactory
from mcp_server.user_management import UserManager
import logging
import plotly.graph_objects as go
from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio

app = Quart(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Initialize managers
data_aggregator = DataAggregator()
user_manager = UserManager()

# In-memory storage (replace with a database in production)
data_store = {}
dashboards = {}
visualizations = {}
api_keys = {}

def generate_api_key():
    """Generate a new API key"""
    return f"mcp_{uuid.uuid4().hex}"

def require_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No authentication token provided'}), 401
        
        token = auth_header.split(' ')[1]
        try:
            user = user_manager.verify_token(token)
            if not user:
                return jsonify({'error': 'Invalid token'}), 401
            return await f(user, *args, **kwargs)
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
    return decorated

@app.route('/api/generate_key', methods=['POST'])
async def generate_key():
    """Generate a new API key for the client application"""
    try:
        # Get client information from request
        data = await request.get_json()
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        # In production, validate client credentials against a database
        # For now, use environment variables
        if not client_id or not client_secret:
            return jsonify({'error': 'Client credentials required'}), 400
            
        if client_id != os.getenv('ALLOWED_CLIENT_ID') or client_secret != os.getenv('ALLOWED_CLIENT_SECRET'):
            return jsonify({'error': 'Invalid client credentials'}), 401
        
        # Generate new API key
        api_key = generate_api_key()
        
        # Store API key with client information
        api_keys[api_key] = {
            'client_id': client_id,
            'created_at': datetime.datetime.utcnow(),
            'last_used': datetime.datetime.utcnow()
        }
        
        return jsonify({
            'api_key': api_key,
            'expires_in': 86400  # 24 hours
        })
    except Exception as e:
        logging.error(f"Error generating API key: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ... [rest of your existing route handlers with async/await] ...

@app.before_serving
async def startup():
    """Initialize services before serving"""
    logging.info("Starting up services...")
    # Add any startup initialization here

@app.after_serving
async def shutdown():
    """Cleanup services after serving"""
    logging.info("Shutting down services...")
    # Add any cleanup code here

if __name__ == '__main__':
    config = Config()
    config.bind = ["0.0.0.0:5001"]
    asyncio.run(serve(app, config)) 