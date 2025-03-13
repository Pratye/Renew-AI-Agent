from flask import Flask, request, jsonify
import jwt
import uuid
import datetime
import os
from functools import wraps
from data_sources import DataAggregator
from dashboard_templates import DashboardFactory, process_dashboard_data
from user_management import UserManager
import asyncio
import logging
from aioflask import Flask
import re
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

app = Flask(__name__)
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
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No authentication token provided'}), 401
        
        token = auth_header.split(' ')[1]
        try:
            user = user_manager.verify_token(token)
            if not user:
                return jsonify({'error': 'Invalid token'}), 401
            return f(user, *args, **kwargs)
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
    return decorated

def extract_dashboard_type(query):
    """Extract dashboard type from query string"""
    dashboard_types = {
        'cbg': ['cbg', 'community based generation', 'community generation'],
        'solar_farm': ['solar farm', 'solar plant', 'pv farm'],
        'wind_farm': ['wind farm', 'wind plant', 'wind generation'],
        'hybrid_plant': ['hybrid plant', 'hybrid generation', 'mixed generation']
    }
    
    query_lower = query.lower()
    for dashboard_type, keywords in dashboard_types.items():
        if any(keyword in query_lower for keyword in keywords):
            return dashboard_type
    
    return None

@app.route('/api/key/generate', methods=['POST'])
def create_api_key():
    """Generate a new API key"""
    api_key = generate_api_key()
    return jsonify({
        'api_key': api_key,
        'created_at': datetime.datetime.now().isoformat()
    })

@app.route('/api/data/fetch', methods=['POST'])
@require_auth
async def fetch_data(user):
    """Fetch data based on query"""
    try:
        data = request.json
        query = data.get('query', '')
        
        # Extract location information from the query using NLP
        location = {
            "country": None,
            "latitude": None,
            "longitude": None
        }
        
        if "in" in query.lower():
            country = query.lower().split("in")[1].strip().split()[0]
            location["country"] = country
        
        # Get date range from query or use default (last 30 days)
        start_date = data.get('start_date', (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat())
        end_date = data.get('end_date', datetime.datetime.now().isoformat())
        
        # Prepare query for data aggregator
        query_params = {
            "start_date": start_date,
            "end_date": end_date,
            **location
        }
        
        # Fetch comprehensive data from all sources
        response_data = await data_aggregator.fetch_comprehensive_data(query_params)
        
        if response_data:
            return jsonify(response_data)
        else:
            return jsonify({
                'error': 'No data available for the specified query',
                'query': query,
                'parameters': query_params
            }), 404
            
    except Exception as e:
        logging.error(f"Error in fetch_data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/register', methods=['POST'])
async def register():
    """Register a new user"""
    try:
        data = request.json
        result = user_manager.register_user(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error in registration: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
async def login():
    """Login a user"""
    try:
        data = request.json
        result = user_manager.login_user(
            email=data['email'],
            password=data['password']
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        logging.error(f"Error in login: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/chat/history', methods=['GET'])
@require_auth
async def get_chat_history(user):
    """Get chat history for the authenticated user"""
    try:
        limit = int(request.args.get('limit', 50))
        history = user_manager.get_chat_history(str(user['_id']), limit)
        return jsonify(history)
    except Exception as e:
        logging.error(f"Error getting chat history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/save', methods=['POST'])
@require_auth
async def save_chat_history(user):
    """Save chat history for the authenticated user"""
    try:
        data = request.json
        chat_id = user_manager.save_chat_history(str(user['_id']), data['messages'])
        return jsonify({'chat_id': chat_id})
    except Exception as e:
        logging.error(f"Error saving chat history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboards', methods=['GET'])
@require_auth
async def get_user_dashboards(user):
    """Get all dashboards for the authenticated user"""
    try:
        dashboards = user_manager.get_user_dashboards(str(user['_id']))
        return jsonify(dashboards)
    except Exception as e:
        logging.error(f"Error getting user dashboards: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboards/create', methods=['POST'])
@require_auth
async def create_dashboard(user):
    """Create a new dashboard for the authenticated user"""
    try:
        data = request.json
        dashboard_id = str(uuid.uuid4())
        
        # Extract dashboard type from query if present
        dashboard_type = None
        if 'query' in data:
            dashboard_type = extract_dashboard_type(data['query'])
        elif 'type' in data:
            dashboard_type = data['type']
        
        if not dashboard_type:
            return jsonify({'error': 'Dashboard type not specified or could not be determined from query'}), 400
        
        # Check if the dashboard should be public
        is_public = False
        if 'query' in data:
            query_lower = data['query'].lower()
            if any(keyword in query_lower for keyword in ['public', 'publicly', 'share', 'shared']):
                is_public = True
        
        # Fetch data if query provided
        if 'query' in data:
            query_params = {
                'query': data['query'],
                'start_date': data.get('start_date'),
                'end_date': data.get('end_date')
            }
            raw_data = await data_aggregator.fetch_comprehensive_data(query_params)
        else:
            raw_data = data.get('data', {})
        
        # Process data for the specific dashboard type
        processed_data = process_dashboard_data(raw_data, dashboard_type)
        
        if not processed_data:
            return jsonify({'error': 'Failed to process data for dashboard'}), 500
        
        # Generate dashboard layout using the factory
        try:
            layout = DashboardFactory.create_dashboard(dashboard_type, processed_data)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Create dashboard with processed data and layout
        dashboard = {
            'id': dashboard_id,
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat(),
            'title': data.get('title', f'{dashboard_type.upper()} Dashboard'),
            'description': data.get('description', ''),
            'type': dashboard_type,
            'data': processed_data,
            'layout': layout,
            'is_public': is_public,
            'settings': {
                'auto_refresh': data.get('auto_refresh', user['preferences'].get('auto_refresh', True)),
                'refresh_interval': data.get('refresh_interval', user['preferences'].get('refresh_interval', 300))
            }
        }
        
        # Save dashboard to database
        dashboard_id = user_manager.save_dashboard(str(user['_id']), dashboard)
        
        # Generate dashboard URLs
        dashboard_url = f'/dashboards/{dashboard_id}'
        public_url = dashboard.get('public_url') if is_public else None
        
        # Generate embed code
        embed_code = f'''
        <iframe 
            src="{public_url if is_public else dashboard_url}" 
            width="100%" 
            height="800" 
            frameborder="0" 
            style="border: 1px solid #ccc; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
        ></iframe>
        '''
        
        response = {
            'dashboard_id': dashboard_id,
            'dashboard_url': dashboard_url,
            'type': dashboard_type,
            'auto_refresh': dashboard['settings']['auto_refresh'],
            'refresh_interval': dashboard['settings']['refresh_interval'],
            'embed_code': embed_code
        }
        
        if is_public:
            response.update({
                'is_public': True,
                'public_url': public_url,
                'message': 'Dashboard created and made public successfully'
            })
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error creating dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboards/<dashboard_id>', methods=['DELETE'])
@require_auth
async def delete_dashboard(user, dashboard_id):
    """Delete a dashboard"""
    try:
        success = user_manager.delete_dashboard(str(user['_id']), dashboard_id)
        if success:
            return jsonify({'message': 'Dashboard deleted successfully'})
        return jsonify({'error': 'Dashboard not found'}), 404
    except Exception as e:
        logging.error(f"Error deleting dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboards/<dashboard_id>', methods=['PUT'])
@require_auth
async def update_dashboard(user, dashboard_id):
    """Update an existing dashboard"""
    try:
        data = request.json
        dashboard = user_manager.get_dashboard(dashboard_id)
        
        if not dashboard or dashboard['user_id'] != str(user['_id']):
            return jsonify({'error': 'Dashboard not found'}), 404
        
        # If new data needs to be fetched
        if 'query' in data:
            query_params = {
                'query': data['query'],
                'start_date': data.get('start_date'),
                'end_date': data.get('end_date')
            }
            raw_data = await data_aggregator.fetch_comprehensive_data(query_params)
            if raw_data:
                processed_data = process_dashboard_data(raw_data, dashboard['type'])
                if processed_data:
                    dashboard['data'] = processed_data
                    dashboard['layout'] = DashboardFactory.create_dashboard(dashboard['type'], processed_data)
        
        # Update other dashboard properties
        if 'layout' in data:
            dashboard['layout'] = data['layout']
        if 'settings' in data:
            dashboard['settings'].update(data['settings'])
        if 'title' in data:
            dashboard['title'] = data['title']
        if 'description' in data:
            dashboard['description'] = data['description']
        
        dashboard['updated_at'] = datetime.datetime.now().isoformat()
        
        # Save updated dashboard
        user_manager.save_dashboard(str(user['_id']), dashboard)
        
        return jsonify(dashboard)
        
    except Exception as e:
        logging.error(f"Error updating dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preferences', methods=['PUT'])
@require_auth
async def update_preferences(user):
    """Update user preferences"""
    try:
        data = request.json
        success = user_manager.update_user_preferences(str(user['_id']), data)
        if success:
            return jsonify({'message': 'Preferences updated successfully'})
        return jsonify({'error': 'Failed to update preferences'}), 500
    except Exception as e:
        logging.error(f"Error updating preferences: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/dashboards/<dashboard_id>', methods=['GET'])
@require_auth
async def render_dashboard(user, dashboard_id):
    """Render a dashboard"""
    try:
        dashboard = user_manager.get_dashboard(dashboard_id)
        if not dashboard:
            return jsonify({'error': 'Dashboard not found'}), 404
        
        # Check if user has access to this dashboard
        if dashboard['user_id'] != str(user['_id']):
            return jsonify({'error': 'Access denied'}), 403
        
        # Update data if auto-refresh is enabled
        if dashboard['settings']['auto_refresh']:
            try:
                # Fetch fresh data
                raw_data = await data_aggregator.fetch_comprehensive_data({
                    'query': f"Update data for {dashboard['type']} dashboard",
                    'start_date': (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat(),
                    'end_date': datetime.datetime.now().isoformat()
                })
                
                if raw_data:
                    # Process new data
                    processed_data = process_dashboard_data(raw_data, dashboard['type'])
                    if processed_data:
                        dashboard['data'] = processed_data
                        dashboard['layout'] = DashboardFactory.create_dashboard(dashboard['type'], processed_data)
                        dashboard['updated_at'] = datetime.datetime.now().isoformat()
                        
                        # Save updated dashboard
                        user_manager.save_dashboard(str(user['_id']), dashboard)
            except Exception as e:
                logging.warning(f"Failed to refresh dashboard data: {str(e)}")
        
        # Create Dash app for this dashboard
        dash_app = Dash(
            f"dashboard_{dashboard_id}",
            server=app,
            url_base_pathname=f"/dashboards/{dashboard_id}/",
            external_stylesheets=[dbc.themes.BOOTSTRAP]
        )
        
        # Generate Dash layout based on dashboard widgets
        dash_app.layout = html.Div([
            # Header
            html.H1(dashboard['title'], className='mb-4'),
            html.P(dashboard['description'], className='mb-4'),
            
            # Grid layout
            html.Div([
                dbc.Row([
                    dbc.Col([
                        render_widget(widget, dashboard['data'])
                        for widget in dashboard['layout']['grid']['widgets']
                        if widget['position']['row'] == row
                    ], width=12)
                    for row in range(dashboard['layout']['grid']['rows'])
                ], className='g-4')
            ]),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=dashboard['settings']['refresh_interval'] * 1000,  # Convert to milliseconds
                n_intervals=0
            ) if dashboard['settings']['auto_refresh'] else None
        ])
        
        return dash_app.index()
        
    except Exception as e:
        logging.error(f"Error rendering dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

def render_widget(widget, data):
    """Render a dashboard widget"""
    try:
        if widget['type'] == 'summary_stats':
            return dbc.Card([
                dbc.CardHeader(widget['title']),
                dbc.CardBody([
                    html.Div([
                        html.H4(metric['name']),
                        html.H2(data[metric['field']])
                    ]) for metric in widget['data']['metrics']
                ])
            ])
            
        elif widget['type'] == 'gauge_chart':
            return dbc.Card([
                dbc.CardHeader(widget['title']),
                dbc.CardBody([
                    dcc.Graph(
                        figure=go.Figure(
                            go.Indicator(
                                mode="gauge+number",
                                value=widget['data']['value'],
                                gauge={'axis': {'range': [0, widget['data']['max']]}},
                                title={'text': widget['title']}
                            )
                        )
                    )
                ])
            ])
            
        elif widget['type'] == 'line_chart':
            return dbc.Card([
                dbc.CardHeader(widget['title']),
                dbc.CardBody([
                    dcc.Graph(
                        figure=go.Figure([
                            go.Scatter(
                                x=series['x'],
                                y=series['y'],
                                name=series['name']
                            ) for series in widget['data']['series']
                        ])
                    )
                ])
            ])
            
        elif widget['type'] == 'map':
            return dbc.Card([
                dbc.CardHeader(widget['title']),
                dbc.CardBody([
                    dcc.Graph(
                        figure=go.Figure(
                            go.Scattermapbox(
                                lat=[loc['latitude'] for loc in widget['data']['locations']],
                                lon=[loc['longitude'] for loc in widget['data']['locations']],
                                mode='markers',
                                marker=go.scattermapbox.Marker(
                                    size=14,
                                    color=widget['data']['values']
                                )
                            )
                        ).update_layout(
                            mapbox_style="carto-positron",
                            mapbox=dict(
                                zoom=widget['data']['parameters']['zoom_level']
                            )
                        )
                    )
                ])
            ])
            
        elif widget['type'] == 'bar_chart':
            return dbc.Card([
                dbc.CardHeader(widget['title']),
                dbc.CardBody([
                    dcc.Graph(
                        figure=go.Figure([
                            go.Bar(
                                x=widget['data']['categories'],
                                y=widget['data']['values']
                            )
                        ])
                    )
                ])
            ])
            
        elif widget['type'] == 'donut_chart':
            return dbc.Card([
                dbc.CardHeader(widget['title']),
                dbc.CardBody([
                    dcc.Graph(
                        figure=go.Figure([
                            go.Pie(
                                labels=widget['data']['labels'],
                                values=widget['data']['values'],
                                hole=0.4
                            )
                        ])
                    )
                ])
            ])
            
        elif widget['type'] == 'forecast':
            return dbc.Card([
                dbc.CardHeader(widget['title']),
                dbc.CardBody([
                    dcc.Graph(
                        figure=go.Figure([
                            go.Scatter(
                                x=widget['data']['timestamps'],
                                y=widget['data']['values'],
                                name='Forecast'
                            ),
                            go.Scatter(
                                x=widget['data']['timestamps'],
                                y=widget['data']['confidence_intervals'],
                                fill='tonexty',
                                name='Confidence'
                            )
                        ])
                    ),
                    html.Div([
                        html.H5("Recommendations"),
                        html.Ul([
                            html.Li(rec) for rec in widget['data']['recommendations']
                        ])
                    ])
                ])
            ])
            
    except Exception as e:
        logging.error(f"Error rendering widget: {str(e)}")
        return html.Div(f"Error rendering widget: {str(e)}")

@app.route('/api/dashboards/<dashboard_id>/visibility', methods=['PUT'])
@require_auth
async def set_dashboard_visibility(user, dashboard_id):
    """Set dashboard visibility (public/private)"""
    try:
        data = request.json
        is_public = data.get('is_public', False)
        
        dashboard = user_manager.set_dashboard_visibility(
            str(user['_id']),
            dashboard_id,
            is_public
        )
        
        return jsonify({
            'message': f"Dashboard is now {'public' if is_public else 'private'}",
            'dashboard': dashboard
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logging.error(f"Error setting dashboard visibility: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboards/public', methods=['GET'])
async def get_public_dashboards():
    """Get list of public dashboards"""
    try:
        limit = int(request.args.get('limit', 50))
        dashboards = user_manager.get_public_dashboards(limit)
        return jsonify(dashboards)
    except Exception as e:
        logging.error(f"Error getting public dashboards: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/public/dashboards/<public_token>', methods=['GET'])
async def view_public_dashboard(public_token):
    """View a public dashboard"""
    try:
        dashboard = user_manager.get_public_dashboard(public_token)
        if not dashboard:
            return jsonify({'error': 'Dashboard not found'}), 404
        
        # Update data if auto-refresh is enabled
        if dashboard['settings']['auto_refresh']:
            try:
                # Fetch fresh data
                raw_data = await data_aggregator.fetch_comprehensive_data({
                    'query': f"Update data for {dashboard['type']} dashboard",
                    'start_date': (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat(),
                    'end_date': datetime.datetime.now().isoformat()
                })
                
                if raw_data:
                    # Process new data
                    processed_data = process_dashboard_data(raw_data, dashboard['type'])
                    if processed_data:
                        dashboard['data'] = processed_data
                        dashboard['layout'] = DashboardFactory.create_dashboard(dashboard['type'], processed_data)
                        dashboard['updated_at'] = datetime.datetime.now().isoformat()
                        
                        # Save updated dashboard
                        user_manager.save_dashboard(dashboard['user_id'], dashboard)
            except Exception as e:
                logging.warning(f"Failed to refresh dashboard data: {str(e)}")
        
        # Create Dash app for this dashboard
        dash_app = Dash(
            f"public_dashboard_{public_token}",
            server=app,
            url_base_pathname=f"/public/dashboards/{public_token}/",
            external_stylesheets=[dbc.themes.BOOTSTRAP]
        )
        
        # Generate Dash layout based on dashboard widgets
        dash_app.layout = html.Div([
            # Header
            html.H1(dashboard['title'], className='mb-4'),
            html.P(dashboard['description'], className='mb-4'),
            
            # Public badge
            dbc.Badge("Public Dashboard", color="success", className="mb-4"),
            
            # Grid layout
            html.Div([
                dbc.Row([
                    dbc.Col([
                        render_widget(widget, dashboard['data'])
                        for widget in dashboard['layout']['grid']['widgets']
                        if widget['position']['row'] == row
                    ], width=12)
                    for row in range(dashboard['layout']['grid']['rows'])
                ], className='g-4')
            ]),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=dashboard['settings']['refresh_interval'] * 1000,  # Convert to milliseconds
                n_intervals=0
            ) if dashboard['settings']['auto_refresh'] else None
        ])
        
        return dash_app.index()
        
    except Exception as e:
        logging.error(f"Error rendering public dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001) 