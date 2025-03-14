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
llm_clients = {}

# Initialize OpenAI/GroQ/Ollama API (primary)
try:
    openai_api = OpenAIAPI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model=os.getenv("OPENAI_MODEL")
    )
    llm_clients['openai'] = openai_api
    logging.info("OpenAI/Compatible API initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize OpenAI API: {str(e)}")

# Initialize Claude API (optional)
if os.getenv("ANTHROPIC_API_KEY"):
    try:
        claude_api = ClaudeAPI(api_key=os.getenv("ANTHROPIC_API_KEY"))
        llm_clients['claude'] = claude_api
        logging.info("Claude API initialized successfully")
    except Exception as e:
        logging.warning(f"Failed to initialize Claude API: {str(e)}. Continuing without Claude.")

# Initialize MCP server if credentials are available
mcp_server = None
if os.getenv("MCP_SERVER_URL"):
    try:
        mcp_server = MCPServer(
            server_url=os.getenv("MCP_SERVER_URL"),
            api_key=None,  # Don't use pre-defined key
            auto_generate_key=True  # Generate new key using client credentials
        )
        logging.info("MCP server initialized successfully")
    except Exception as e:
        logging.warning(f"Failed to initialize MCP server: {str(e)}. Some features may be limited.")

# Initialize utility classes
data_processor = DataProcessor()
report_generator = ReportGenerator()

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
        provider = data.get('provider', 'openai').lower()  # Default to OpenAI if not specified
        
        # Get conversation history from session
        conversation_history = session.get('conversation_history', [])
        
        # Add user message to conversation history
        conversation_history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Check if the requested provider is available
        if provider not in llm_clients:
            available_providers = list(llm_clients.keys())
            if not available_providers:
                return jsonify({'error': 'No LLM providers available'}), 500
            provider = available_providers[0]
            logging.warning(f"Requested provider '{provider}' not available. Using {provider} instead.")
        
        # Generate AI response using the selected provider
        try:
            response = llm_clients[provider].generate_response(
                SYSTEM_PROMPT,
                conversation_history,
                max_tokens=500 if context == 'info_panel' else 1000
            )
        except Exception as e:
            logging.error(f"Error with {provider}: {str(e)}. Trying fallback if available.")
            # Try fallback to another available provider
            for fallback_provider, client in llm_clients.items():
                if fallback_provider != provider:
                    try:
                        response = client.generate_response(
                            SYSTEM_PROMPT,
                            conversation_history,
                            max_tokens=500 if context == 'info_panel' else 1000
                        )
                        logging.info(f"Successfully used {fallback_provider} as fallback")
                        break
                    except Exception as fallback_e:
                        logging.error(f"Fallback to {fallback_provider} also failed: {str(fallback_e)}")
            else:
                return jsonify({'error': 'All available LLM providers failed'}), 500
        
        # Check if we should use MCP server
        # Keywords that indicate dashboard/data visualization requests - expanded to be more inclusive
        dashboard_keywords = [
            'dashboard', 'model', 'create', 'deploy', 'visualization', 'graph', 'chart', 'plot', 'data', 
            'statistics', 'analytics', 'report', 'metrics', 'kpi', 'trends', 'analysis', 'build', 'generate', 
            'show me', 'display', 'visualize', 'host', 'make', 'develop', 'construct', 'design', 'implement',
            'setup', 'configure', 'prepare', 'establish', 'produce', 'render', 'showcase', 'demonstrate',
            'illustrate', 'present', 'view', 'monitor', 'track', 'overview', 'summary', 'insights'
        ]
        
        # Model type keywords - used only for customizing the dashboard if a specific type is mentioned
        model_types = {
            'cbg': ['cbg', 'community', 'community-based', 'community based', 'community generation', 'compressed bio gas', 'bio gas', 'biogas', 'methane', 'organic waste'],
            'solar_farm': ['solar farm', 'solar panel', 'photovoltaic', 'solar energy', 'solar power', 'pv', 'solar array'],
            'wind_farm': ['wind farm', 'wind turbine', 'wind power', 'wind energy', 'windmill', 'wind generation'],
            'hybrid_plant': ['hybrid', 'mixed', 'multi-source', 'combined', 'integrated', 'multiple sources']
        }
        
        # Autonomous dashboard creation detection
        # 1. Check for explicit dashboard creation intent
        dashboard_creation_keywords = ['create', 'build', 'generate', 'make', 'develop', 'host', 'deploy', 'setup', 'implement']
        explicit_dashboard_intent = any(keyword in user_message.lower() for keyword in dashboard_creation_keywords) and ('dashboard' in user_message.lower())
        
        # 2. Check for implicit dashboard intent (asking for visualization or data presentation)
        visualization_keywords = ['show', 'display', 'visualize', 'graph', 'chart', 'plot', 'see', 'view']
        data_subject_keywords = ['data', 'statistics', 'metrics', 'performance', 'results', 'numbers', 'figures', 'trends']
        implicit_dashboard_intent = any(v_keyword in user_message.lower() for v_keyword in visualization_keywords) and any(d_keyword in user_message.lower() for d_keyword in data_subject_keywords)
        
        # 3. Check for domain-specific requests that would benefit from a dashboard
        domain_specific_intent = any(term in user_message.lower() for term in ['energy production', 'power generation', 'efficiency analysis', 'performance metrics', 'renewable output', 'generation capacity'])
        
        # 4. Check if the query is asking about a specific model or system that would benefit from visualization
        model_mention = any(any(keyword in user_message.lower() for keyword in keywords) for keywords in model_types.values())
        
        # Combine all intent signals - be more aggressive in creating dashboards
        dashboard_intent = explicit_dashboard_intent or implicit_dashboard_intent or (domain_specific_intent and model_mention)
        
        # Always use MCP for data-related queries, but prioritize dashboard creation for dashboard intents
        should_use_mcp = dashboard_intent or any(keyword in user_message.lower() for keyword in dashboard_keywords)
        
        # Log the decision process
        logging.info(f"Dashboard detection - Explicit: {explicit_dashboard_intent}, Implicit: {implicit_dashboard_intent}, Domain: {domain_specific_intent}, Model mention: {model_mention}")
        logging.info(f"MCP server status - Available: {mcp_server is not None}, Should use: {should_use_mcp}, Dashboard intent: {dashboard_intent}")
        
        # Determine model type
        model_type = None
        message_lower = user_message.lower()
        for type_name, keywords in model_types.items():
            if any(keyword in message_lower for keyword in keywords):
                model_type = type_name
                break
        
        # If no specific model type is detected but dashboard creation is requested,
        # default to a general dashboard or try to infer from context
        if should_use_mcp and not model_type:
            # Try to infer dashboard type from context
            if any(term in message_lower for term in ['renewable', 'energy', 'power', 'electricity', 'generation']):
                if any(term in message_lower for term in ['solar', 'sun', 'photovoltaic', 'pv']):
                    model_type = 'solar_farm'
                elif any(term in message_lower for term in ['wind', 'turbine', 'windmill']):
                    model_type = 'wind_farm'
                elif any(term in message_lower for term in ['bio', 'gas', 'methane', 'organic', 'waste', 'community']):
                    model_type = 'cbg'
                elif any(term in message_lower for term in ['multiple', 'combined', 'hybrid', 'mix', 'integrated']):
                    model_type = 'hybrid_plant'
                else:
                    # Default to CBG if no specific type is mentioned but energy-related
                    model_type = 'cbg'
        
        # Try to use MCP server if available and relevant
        if mcp_server and should_use_mcp:
            try:
                logging.info("Attempting to use MCP server for data processing")
                # Fetch relevant data from MCP server
                dashboard_type = model_type if model_type else ('cbg' if dashboard_intent else None)
                mcp_data = mcp_server.fetch_data(user_message, dashboard_type=dashboard_type)
                logging.info("Successfully fetched data from MCP server")
                
                # Process the data
                processed_data = data_processor.process(mcp_data)
                
                # Always create a dashboard for data-related queries
                try:
                    # If model_type is still None, default to 'cbg' for dashboard creation
                    dashboard_type = model_type if model_type else 'cbg'
                    
                    # Create a more descriptive title based on the query
                    query_keywords = user_message.lower().split()
                    title_keywords = [word.capitalize() for word in query_keywords if len(word) > 3 and word not in ['what', 'when', 'where', 'which', 'how', 'can', 'will', 'should', 'could', 'would', 'about', 'with', 'from', 'that', 'this', 'these', 'those']]
                    title_suffix = ' '.join(title_keywords[:5]) if title_keywords else user_message[:50]
                    
                    dashboard_info = mcp_server.create_dashboard(
                        title=f"Renewable Energy Dashboard - {dashboard_type.upper()} - {title_suffix}",
                        description=f"Dashboard generated based on query: {user_message}",
                        data=processed_data,
                        layout={"type": dashboard_type},
                        auto_refresh=True
                    )
                    
                    # Customize response based on dashboard type and query intent
                    dashboard_type_display = dashboard_type.replace('_', ' ').title()
                    if dashboard_type == 'cbg':
                        if "compressed bio gas" in message_lower:
                            dashboard_type_display = "Compressed Bio Gas"
                        elif "biogas" in message_lower:
                            dashboard_type_display = "Biogas"
                        else:
                            dashboard_type_display = "Community Based Generation"
                    
                    # Customize the response based on the detected intent
                    if explicit_dashboard_intent:
                        response += f"\n\nI've created an interactive {dashboard_type_display} dashboard for you as requested: {dashboard_info['url']}"
                    elif implicit_dashboard_intent:
                        response += f"\n\nTo help visualize this data, I've created an interactive {dashboard_type_display} dashboard for you: {dashboard_info['url']}"
                    elif domain_specific_intent:
                        response += f"\n\nI've prepared a {dashboard_type_display} dashboard to help you analyze this information: {dashboard_info['url']}"
                    else:
                        response += f"\n\nI've also created a {dashboard_type_display} dashboard to help visualize this data: {dashboard_info['url']}"
                    
                    if dashboard_info.get('embed_code'):
                        response += f"\nYou can embed this dashboard using the provided code."
                    
                    logging.info(f"Successfully created dashboard: {dashboard_info.get('url')}")
                except Exception as e:
                    logging.error(f"Error creating dashboard: {str(e)}")
                    response += "\n\nI encountered an error while creating the dashboard, but I can still provide you with the data analysis."
                
                # Generate report if specifically requested
                if 'report' in user_message.lower():
                    try:
                        report_url = report_generator.generate_report(processed_data, user_message)
                        response += f"\n\nI've also generated a detailed report for you: {report_url}"
                        logging.info(f"Successfully generated report: {report_url}")
                    except Exception as e:
                        logging.error(f"Error generating report: {str(e)}")
            
            except Exception as e:
                logging.error(f"Error processing MCP data: {str(e)}")
                response += "\n\nI apologize, but I encountered an error while trying to fetch additional data. I've provided the best response I can based on my knowledge."
        else:
            if not mcp_server:
                logging.warning("MCP server is not available")
            if not should_use_mcp:
                logging.info("Request does not require MCP server")
        
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
            'used_mcp': bool(mcp_server and should_use_mcp)
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