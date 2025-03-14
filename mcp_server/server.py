from quart import Quart, request, jsonify
from dotenv import load_dotenv
import jwt
import uuid
import datetime
import os
from functools import wraps
from mcp_server.data_sources import DataAggregator
from mcp_server.dashboard_factory import DashboardFactory, process_dashboard_data
from mcp_server.user_management import UserManager
import logging
import plotly.graph_objects as go
from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio
import numpy as np
import pandas as pd

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
    """Decorator to require API key authentication"""
    @wraps(f)
    async def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        
        api_key = auth_header.split(' ')[1]
        if api_key not in api_keys:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Update last used timestamp
        api_keys[api_key]['last_used'] = datetime.datetime.utcnow()
        return await f(*args, **kwargs)
    return decorated

def generate_mock_data(start_date, end_date):
    """Generate mock data when external APIs are unavailable"""
    try:
        # Convert dates to datetime objects
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Generate date range
        dates = pd.date_range(start=start, end=end, freq='H')
        
        # Generate mock data
        mock_data = {
            'eia': {
                'data': [
                    {
                        'timestamp': d.isoformat(),
                        'value': np.random.normal(1000, 100)  # Mock generation in MWh
                    } for d in dates
                ]
            },
            'solargis': {
                'current_generation': np.random.normal(800, 50),
                'capacity': 1000,
                'data': [
                    {
                        'timestamp': d.isoformat(),
                        'ghi': np.random.normal(500, 50),
                        'dni': np.random.normal(700, 70),
                        'temp': np.random.normal(25, 5)
                    } for d in dates
                ]
            },
            'analysis': {
                'generation_forecast': [
                    {
                        'timestamp': d.isoformat(),
                        'value': np.random.normal(900, 100)
                    } for d in dates
                ],
                'consumption_forecast': [
                    {
                        'timestamp': d.isoformat(),
                        'value': np.random.normal(800, 150)
                    } for d in dates
                ]
            }
        }
        
        return mock_data
    except Exception as e:
        logging.error(f"Error generating mock data: {str(e)}")
        return None

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

@app.route('/api/data/fetch', methods=['POST'])
@require_auth
async def fetch_data():
    """Fetch data based on query parameters"""
    try:
        # Get query parameters from request
        data = await request.get_json()
        query = data.get('query')
        data_sources = data.get('data_sources', ['renewable_energy_db', 'web_scraping', 'external_apis'])
        
        if not query:
            return jsonify({'error': 'Query parameter is required'}), 400
        
        # Extract date range from query if present
        # Default to last 30 days if not specified
        now = datetime.datetime.utcnow()
        default_start = (now - datetime.timedelta(days=30)).isoformat()
        default_end = now.isoformat()
        
        # Parse query for parameters
        query_params = {
            'start_date': default_start,
            'end_date': default_end,
            'data_types': [],
            'location': None
        }
        
        try:
            # Try to fetch real data first
            result = await data_aggregator.fetch_comprehensive_data({
                'query': query,
                'start_date': query_params['start_date'],
                'end_date': query_params['end_date'],
                'data_sources': data_sources
            })
        except Exception as e:
            logging.warning(f"Failed to fetch real data: {str(e)}. Falling back to mock data.")
            result = None
        
        # If real data fetch failed, use mock data
        if result is None:
            logging.info("Generating mock data for demonstration")
            result = generate_mock_data(
                query_params['start_date'],
                query_params['end_date']
            )
            
            if result is None:
                return jsonify({'error': 'Failed to generate data'}), 500
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error in data fetch endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/dashboards/create', methods=['POST'])
@require_auth
async def create_dashboard():
    """Create a new dashboard"""
    try:
        data = await request.get_json()
        required_fields = ['title', 'description', 'data']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get dashboard type from layout
        dashboard_type = data.get('layout', {}).get('type', 'default')
        
        # Process data for dashboard
        processed_data = process_dashboard_data(data['data'], dashboard_type)
        if not processed_data:
            return jsonify({'error': 'Failed to process dashboard data'}), 500
        
        # Create dashboard layout
        layout = DashboardFactory.create_dashboard(dashboard_type, processed_data)
        
        # Generate dashboard ID
        dashboard_id = str(uuid.uuid4())
        
        # Store dashboard
        dashboards[dashboard_id] = {
            'title': data['title'],
            'description': data['description'],
            'data': processed_data,
            'layout': layout,
            'settings': data.get('settings', {}),
            'created_at': datetime.datetime.utcnow().isoformat()
        }
        
        # Generate dashboard URL
        dashboard_url = f"/dashboards/{dashboard_id}"
        
        return jsonify({
            'dashboard_id': dashboard_id,
            'dashboard_url': dashboard_url,
            'embed_code': f'<iframe src="{dashboard_url}" width="100%" height="600px" frameborder="0"></iframe>'
        })
        
    except Exception as e:
        logging.error(f"Error creating dashboard: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

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
    config.bind = ["0.0.0.0:5002"]
    asyncio.run(serve(app, config)) 