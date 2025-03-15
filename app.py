import os
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_socketio import SocketIO
from dotenv import load_dotenv
import json
import uuid
from datetime import datetime
import logging

# Import custom modules
from api.mcp_client import SimpleMCPClient
from api.vector_store import VectorStore
from utils.data_processor import DataProcessor
from utils.report_generator import ReportGenerator

# Load environment variables
load_dotenv()

# Ensure static directories exist
os.makedirs(os.path.join(os.getcwd(), 'static'), exist_ok=True)
os.makedirs(os.path.join(os.getcwd(), 'static', 'dashboards'), exist_ok=True)
os.makedirs(os.path.join(os.getcwd(), 'data', 'vector_store'), exist_ok=True)

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize MCP client
mcp_client = None
try:
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:5002")
    server_script_path = os.getenv("MCP_SERVER_SCRIPT_PATH")
    
    if not server_script_path:
        logging.warning("MCP_SERVER_SCRIPT_PATH not set. Using default path.")
        # Try to find the server script in common locations
        possible_paths = [
            os.path.join(os.getcwd(), 'mcp_server', 'server.py'),
            os.path.join(os.getcwd(), 'server.py'),
            os.path.join(os.getcwd(), 'mcp', 'server.py')
        ]
        for path in possible_paths:
            if os.path.exists(path):
                server_script_path = path
                logging.info(f"Found MCP server script at: {path}")
                break
    
    logging.info(f"Initializing MCP client with server URL: {server_url}")
    mcp_client = SimpleMCPClient(server_url=server_url, server_script_path=server_script_path)
    if mcp_client.connect_to_server():
        logging.info("MCP client initialized and connected successfully")
    else:
        logging.error("Failed to connect to MCP server")
except Exception as e:
    logging.error(f"Failed to initialize MCP client: {str(e)}")

# Initialize utility classes
data_processor = DataProcessor()
report_generator = ReportGenerator()
vector_store = VectorStore()

# System prompt for the renewable energy consultant persona
SYSTEM_PROMPT = """
You are a Renewable Energy Consultant chatbot with autonomous dashboard creation capabilities. Your expertise includes solar, wind, hydro, 
geothermal, biogas, and other renewable energy sources. You can provide information on:

- Renewable energy technologies and their applications
- Cost analysis and ROI calculations for renewable energy projects
- Environmental impact assessments
- Policy and regulatory frameworks
- Market trends and forecasts
- Best practices for implementation

You proactively create interactive dashboards and visualizations based on user queries. When users ask about renewable energy data, 
performance metrics, or any analysis that would benefit from visualization, you automatically generate and host a relevant dashboard.

You can create different types of dashboards:
- Community Based Generation (CBG) / Compressed Bio Gas dashboards
- Solar Farm dashboards
- Wind Farm dashboards
- Hybrid Plant dashboards

You have access to various data sources and can perform web searches for the latest information. You can also generate comprehensive 
reports based on your analysis.

Always be helpful, informative, and focused on providing accurate information about renewable energy with visual aids whenever possible.
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
        
        # Check if MCP client is available
        if not mcp_client:
            return jsonify({
                'error': 'MCP client is not available. Please check server configuration.',
                'session_id': session.get('session_id')
            }), 500
        
        # Process query using MCP client
        try:
            # Check if we have similar questions in the vector store
            similar_qa = vector_store.query_chat(user_message)
            
            # Add context from vector store to the system prompt if available
            enhanced_system_prompt = SYSTEM_PROMPT
            if similar_qa:
                context_from_vector_store = "\n\nHere are some relevant previous Q&A pairs that might help with this query:\n"
                for i, qa in enumerate(similar_qa, 1):
                    context_from_vector_store += f"\nQ{i}: {qa.get('question', '')}\nA{i}: {qa.get('answer', '')}\n"
                enhanced_system_prompt += context_from_vector_store
            
            # Process the query using MCP client
            result = mcp_client.process_query(user_message, enhanced_system_prompt)
            
            if result.get('error', False):
                logging.error(f"Error from MCP client: {result.get('response')}")
                return jsonify({
                    'error': result.get('response'),
                    'session_id': session.get('session_id')
                }), 500
            
            response = result.get('response', '')
            
            # Store the Q&A pair in the vector store for future reference
            try:
                vector_store.store_chat_data(
                    question=user_message,
                    answer=response,
                    metadata={
                        "provider": "mcp",
                        "session_id": session.get('session_id'),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logging.error(f"Error storing chat data in vector store: {str(e)}")
            
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
                'session_id': session.get('session_id'),
                'provider': 'mcp',
                'tool_results': result.get('tool_results', [])
            })
            
        except Exception as e:
            logging.error(f"Error processing query with MCP client: {str(e)}")
            return jsonify({
                'error': f"Error processing your query: {str(e)}",
                'session_id': session.get('session_id')
            }), 500
    
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

@app.route('/static/dashboards/<dashboard_id>.html')
def serve_dashboard(dashboard_id):
    """
    Serve a static dashboard HTML file.
    """
    try:
        return send_from_directory(os.path.join(app.static_folder, 'dashboards'), f"{dashboard_id}.html")
    except Exception as e:
        logging.error(f"Error serving dashboard {dashboard_id}: {str(e)}")
        return f"Dashboard not found: {dashboard_id}", 404

# Clean up resources when the app is shutting down
@app.teardown_appcontext
def cleanup_resources(exception=None):
    if mcp_client:
        try:
            mcp_client.cleanup()
            logging.info("MCP client resources cleaned up")
        except Exception as e:
            logging.error(f"Error cleaning up MCP client: {str(e)}")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000) 