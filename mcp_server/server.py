from quart import Quart, request, jsonify
import jwt
import uuid
import datetime
import os
from functools import wraps
from data_sources import DataAggregator
from dashboard_templates import DashboardFactory, process_dashboard_data
from user_management import UserManager
import logging
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
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