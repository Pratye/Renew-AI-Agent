import os
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO
from dotenv import load_dotenv
import json
import uuid
from datetime import datetime
import logging

# Import custom modules
from api.claude_api import ClaudeAPI
from api.openai_api import OpenAIAPI
from api.mcp_server import MCPServer
from utils.data_processor import DataProcessor
from utils.report_generator import ReportGenerator

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize API clients
try:
    claude_api = ClaudeAPI(api_key=os.getenv("ANTHROPIC_API_KEY"))
    logging.info("Claude API initialized successfully")
except Exception as e:
    logging.warning(f"Failed to initialize Claude API: {str(e)}. Continuing without Claude.")
    claude_api = None

# Initialize OpenAI/GroQ API
openai_api = OpenAIAPI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    model=os.getenv("OPENAI_MODEL")
)

# Initialize MCP server if credentials are available
mcp_server = None
if os.getenv("MCP_SERVER_URL") and os.getenv("MCP_API_KEY"):
    try:
        mcp_server = MCPServer(
            server_url=os.getenv("MCP_SERVER_URL"),
            api_key=os.getenv("MCP_API_KEY")
        )
        logging.info("MCP server initialized successfully")
    except Exception as e:
        logging.warning(f"Failed to initialize MCP server: {str(e)}. Some features may be limited.")

# Initialize utility classes
data_processor = DataProcessor()
report_generator = ReportGenerator()

# System prompt for the renewable energy consultant persona
SYSTEM_PROMPT = """
You are a Renewable Energy Consultant chatbot. Your expertise includes solar, wind, hydro, 
geothermal, and other renewable energy sources. You can provide information on:

- Renewable energy technologies and their applications
- Cost analysis and ROI calculations for renewable energy projects
- Environmental impact assessments
- Policy and regulatory frameworks
- Market trends and forecasts
- Best practices for implementation

You can generate reports and dashboards based on data analysis. You have access to various 
data sources and can perform web searches for the latest information.

Always be helpful, informative, and focused on providing accurate information about renewable energy.
"""

@app.route('/')
def index():
    # Generate a unique session ID if not already present
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session['conversation_history'] = []
    
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        context = data.get('context', 'chat')
        
        # Get conversation history from session
        conversation_history = session.get('conversation_history', [])
        
        # Add user message to conversation history
        conversation_history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Generate AI response
        if context == 'info_panel':
            response = openai_api.generate_response(
                SYSTEM_PROMPT,
                conversation_history,
                max_tokens=500
            )
        else:
            response = claude_api.generate_response(
                SYSTEM_PROMPT,
                conversation_history
            ) if claude_api else openai_api.generate_response(
                SYSTEM_PROMPT,
                conversation_history
            )
        
        # Check if we need to fetch data from MCP server
        if mcp_server and any(keyword in user_message.lower() for keyword in ['data', 'statistics', 'numbers', 'report', 'dashboard']):
            try:
                # Fetch relevant data from MCP server
                mcp_data = mcp_server.fetch_data(user_message)
                
                # Process the data
                processed_data = data_processor.process(mcp_data)
                
                # Generate dashboard if requested
                if 'dashboard' in user_message.lower():
                    dashboard_info = mcp_server.create_dashboard(
                        title=f"Renewable Energy Dashboard - {datetime.now().strftime('%Y-%m-%d')}",
                        description=f"Dashboard generated based on query: {user_message}",
                        data=processed_data,
                        auto_refresh=True
                    )
                    response += f"\n\nI've created an interactive dashboard for you: {dashboard_info['url']}"
                    if dashboard_info.get('embed_code'):
                        response += f"\nYou can embed this dashboard using the provided code."
                
                # Generate visualization if specifically requested
                elif 'visualization' in user_message.lower():
                    visualization_url = data_processor.generate_visualization(processed_data)
                    response += f"\n\nI've created a visualization based on the data: {visualization_url}"
                
                # Generate report if requested
                if 'report' in user_message.lower():
                    report_url = report_generator.generate_report(processed_data, user_message)
                    response += f"\n\nI've generated a detailed report for you: {report_url}"
            
            except Exception as e:
                logging.error(f"Error processing MCP data: {str(e)}")
                response += "\n\nI apologize, but I encountered an error while trying to fetch additional data. I've provided the best response I can based on my knowledge."
        
        # Add AI response to conversation history
        conversation_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update session
        session['conversation_history'] = conversation_history
        
        return jsonify({
            'response': response,
            'session_id': session.get('session_id')
        })
    
    except Exception as e:
        logging.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_conversation():
    session['conversation_history'] = []
    return jsonify({'status': 'success', 'message': 'Conversation reset successfully'})

@app.route('/api/export', methods=['GET'])
def export_conversation():
    conversation_history = session.get('conversation_history', [])
    return jsonify({
        'conversation': conversation_history,
        'session_id': session.get('session_id'),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/dashboard/create', methods=['POST'])
def create_dashboard():
    """
    Create a new dashboard based on the provided data and configuration.
    """
    try:
        data = request.json
        required_fields = ['title', 'description', 'data']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Optional parameters
        layout = data.get('layout')
        auto_refresh = data.get('auto_refresh', False)
        refresh_interval = data.get('refresh_interval', 300)
        
        # Create dashboard using MCP server
        if mcp_server:
            dashboard_info = mcp_server.create_dashboard(
                title=data['title'],
                description=data['description'],
                data=data['data'],
                layout=layout,
                auto_refresh=auto_refresh,
                refresh_interval=refresh_interval
            )
            return jsonify(dashboard_info)
        else:
            # Fallback to local dashboard generation
            processed_data = data_processor.process(data['data'])
            visualization_url = data_processor.generate_visualization(processed_data)
            
            return jsonify({
                'dashboard_id': str(uuid.uuid4()),
                'url': visualization_url,
                'type': 'local'
            })
    
    except Exception as e:
        logging.error(f"Error creating dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/update/<dashboard_id>', methods=['PUT'])
def update_dashboard(dashboard_id):
    """
    Update an existing dashboard.
    """
    try:
        if not mcp_server:
            return jsonify({'error': 'MCP server not configured'}), 400
        
        data = request.json
        result = mcp_server.update_dashboard(
            dashboard_id=dashboard_id,
            data=data.get('data'),
            layout=data.get('layout'),
            settings=data.get('settings')
        )
        
        return jsonify(result)
    
    except Exception as e:
        logging.error(f"Error updating dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000) 