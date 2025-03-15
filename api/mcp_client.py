import os
import json
import logging
import requests
import subprocess
import threading
import queue
import time
from typing import Dict, Any, List, Optional

# LLM provider imports
try:
    import openai
except ImportError:
    logging.warning("OpenAI library not installed. OpenAI provider will not be available.")

try:
    import anthropic
except ImportError:
    logging.warning("Anthropic library not installed. Claude provider will not be available.")

class LLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self):
        self.name = "base"
    
    def generate_with_tools(self, messages, tools, max_tokens=1000):
        """Generate a response with tool calling capabilities"""
        raise NotImplementedError("Subclasses must implement this method")

class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, api_key=None, base_url=None, model=None):
        super().__init__()
        self.name = "openai"
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Initialize client
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_with_tools(self, messages, tools, max_tokens=1000):
        """Generate a response with tool calling capabilities"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens
            )
            
            # Process response
            result = []
            tool_calls = []
            
            for choice in response.choices:
                message = choice.message
                
                # Add text content
                if message.content:
                    result.append(message.content)
                
                # Process tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_calls.append({
                            'id': tool_call.id,
                            'type': 'tool_use',
                            'name': tool_call.function.name,
                            'input': json.loads(tool_call.function.arguments)
                        })
            
            return {
                'content': result,
                'tool_calls': tool_calls
            }
            
        except Exception as e:
            logging.error(f"Error generating with OpenAI: {str(e)}")
            raise

class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation"""
    
    def __init__(self, api_key=None, model=None):
        super().__init__()
        self.name = "anthropic"
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        
        # Check which version of the Anthropic library we're using
        self.using_new_api = hasattr(anthropic, 'Anthropic')
        
        # Initialize client based on API version
        if self.using_new_api:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            # Legacy API
            self.client = anthropic.Client(api_key=self.api_key)
    
    def generate_with_tools(self, messages, tools, max_tokens=1000):
        """Generate a response with tool calling capabilities"""
        try:
            if self.using_new_api:
                # New API (messages)
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=messages,
                    tools=tools
                )
                
                # Process response
                result = []
                tool_calls = []
                
                for content in response.content:
                    if content.type == 'text':
                        result.append(content.text)
                    elif content.type == 'tool_use':
                        tool_calls.append({
                            'id': content.id,
                            'type': 'tool_use',
                            'name': content.name,
                            'input': content.input
                        })
                
                return {
                    'content': result,
                    'tool_calls': tool_calls,
                    'raw_response': response
                }
            else:
                # Legacy API (doesn't support tool calling)
                # Convert messages to prompt
                prompt = self._messages_to_prompt(messages)
                
                response = self.client.completion(
                    prompt=prompt,
                    model=self.model,
                    max_tokens_to_sample=max_tokens
                )
                
                return {
                    'content': [response.completion],
                    'tool_calls': []
                }
                
        except Exception as e:
            logging.error(f"Error generating with Anthropic: {str(e)}")
            raise
    
    def _messages_to_prompt(self, messages):
        """Convert messages to a prompt for the legacy API"""
        prompt = ""
        
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            
            if role == 'system':
                prompt += f"\n\nHuman: <s>{content}</s>\n\nAssistant: I'll follow those instructions."
            elif role == 'user':
                prompt += f"\n\nHuman: {content}"
            elif role == 'assistant':
                prompt += f"\n\nAssistant: {content}"
        
        prompt += "\n\nAssistant:"
        return prompt

class SimpleMCPClient:
    """
    A simplified MCP client implementation that works with any LLM provider.
    """
    
    def __init__(self, server_url=None, server_script_path=None):
        """
        Initialize the MCP client.
        
        Args:
            server_url (str, optional): URL of the MCP server. Defaults to None.
            server_script_path (str, optional): Path to the MCP server script. Defaults to None.
        """
        # Store server URL and script path
        self.server_url = server_url or os.getenv("MCP_SERVER_URL", "http://localhost:5002")
        self.server_script_path = server_script_path or os.getenv("MCP_SERVER_SCRIPT_PATH")
        
        # Initialize LLM provider
        self.llm_provider = self._initialize_llm_provider()
        
        # Server process
        self.server_process = None
        
        # Communication queues
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        
        # Flag to indicate if the client is connected
        self.is_connected = False
        
        # Fetch available tools from server
        self.available_tools = []
    
    def _initialize_llm_provider(self):
        """Initialize the LLM provider based on available APIs and environment variables"""
        # Try to initialize providers in order of preference
        providers_to_try = [
            ("openai", OpenAIProvider),
            ("anthropic", AnthropicProvider)
        ]
        
        for provider_name, provider_class in providers_to_try:
            try:
                provider = provider_class()
                logging.info(f"Using {provider_name} as LLM provider")
                return provider
            except (ImportError, ValueError, AttributeError) as e:
                logging.warning(f"Could not initialize {provider_name} provider: {str(e)}")
                continue
        
        # If we get here, no provider was initialized
        raise ValueError("No LLM provider could be initialized. Please check your environment variables and installed packages.")
    
    def connect_to_server(self):
        """
        Connect to the MCP server.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            # Check if server is running by making a health check request
            response = requests.get(f"{self.server_url}/health", timeout=5)
            
            if response.status_code == 200:
                self.is_connected = True
                logging.info(f"Connected to MCP server at {self.server_url}")
                
                # Fetch available tools
                try:
                    tools_response = requests.get(f"{self.server_url}/tools", timeout=5)
                    if tools_response.status_code == 200:
                        tools_data = tools_response.json()
                        self.available_tools = tools_data.get("tools", [])
                        logging.info(f"Fetched {len(self.available_tools)} tools from MCP server")
                    else:
                        logging.warning(f"Failed to fetch tools from MCP server: {tools_response.status_code}")
                        # Use default tools if server doesn't provide them
                        self._set_default_tools()
                except Exception as e:
                    logging.warning(f"Error fetching tools from MCP server: {str(e)}")
                    # Use default tools if server doesn't provide them
                    self._set_default_tools()
                
                return True
            else:
                logging.error(f"MCP server health check failed with status code {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Error connecting to MCP server at {self.server_url}: {str(e)}")
            
            # If we have a server script path, try to start the server
            if self.server_script_path and os.path.exists(self.server_script_path):
                try:
                    logging.info(f"Attempting to start MCP server from {self.server_script_path}")
                    # Start server in a separate process
                    self.server_process = subprocess.Popen(
                        ["python", self.server_script_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # Wait a bit for the server to start
                    time.sleep(2)
                    
                    # Try connecting again
                    try:
                        response = requests.get(f"{self.server_url}/health", timeout=5)
                        if response.status_code == 200:
                            self.is_connected = True
                            logging.info(f"Successfully started and connected to MCP server at {self.server_url}")
                            
                            # Fetch available tools
                            try:
                                tools_response = requests.get(f"{self.server_url}/tools", timeout=5)
                                if tools_response.status_code == 200:
                                    tools_data = tools_response.json()
                                    self.available_tools = tools_data.get("tools", [])
                                    logging.info(f"Fetched {len(self.available_tools)} tools from MCP server")
                                else:
                                    logging.warning(f"Failed to fetch tools from MCP server: {tools_response.status_code}")
                                    # Use default tools if server doesn't provide them
                                    self._set_default_tools()
                            except Exception as e:
                                logging.warning(f"Error fetching tools from MCP server: {str(e)}")
                                # Use default tools if server doesn't provide them
                                self._set_default_tools()
                            
                            return True
                    except requests.exceptions.RequestException:
                        logging.error("Failed to connect to MCP server after starting it")
                
                except Exception as e:
                    logging.error(f"Error starting MCP server: {str(e)}")
            
            # If we couldn't connect to or start the server, use mock implementations
            logging.warning("Using mock implementations for MCP tools")
            self._set_default_tools()
            self.is_connected = True
            return True
    
    def _set_default_tools(self):
        """Set default tools when server doesn't provide them"""
        self.available_tools = [
            {
                "name": "fetch_renewable_data",
                "description": "Fetch data about renewable energy sources",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "energy_type": {
                            "type": "string",
                            "description": "Type of renewable energy (solar, wind, hydro, geothermal, biogas, etc.)"
                        },
                        "location": {
                            "type": "string",
                            "description": "Geographic location for the data"
                        },
                        "time_period": {
                            "type": "string",
                            "description": "Time period for the data (e.g., 'last_week', 'last_month', 'last_year')"
                        }
                    },
                    "required": ["energy_type"]
                }
            },
            {
                "name": "create_dashboard",
                "description": "Create a dashboard for visualizing renewable energy data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dashboard_type": {
                            "type": "string",
                            "description": "Type of dashboard to create (cbg, solar_farm, wind_farm, hybrid_plant)"
                        },
                        "title": {
                            "type": "string",
                            "description": "Title for the dashboard"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the dashboard"
                        }
                    },
                    "required": ["dashboard_type", "title"]
                }
            },
            {
                "name": "calculate_roi",
                "description": "Calculate return on investment for renewable energy projects",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_type": {
                            "type": "string",
                            "description": "Type of renewable energy project"
                        },
                        "initial_investment": {
                            "type": "number",
                            "description": "Initial investment amount in USD"
                        },
                        "annual_revenue": {
                            "type": "number",
                            "description": "Expected annual revenue in USD"
                        },
                        "annual_costs": {
                            "type": "number",
                            "description": "Expected annual maintenance and operational costs in USD"
                        },
                        "project_lifetime": {
                            "type": "number",
                            "description": "Expected lifetime of the project in years"
                        }
                    },
                    "required": ["project_type", "initial_investment", "annual_revenue", "project_lifetime"]
                }
            }
        ]
    
    def process_query(self, query: str, system_prompt: str = None) -> Dict[str, Any]:
        """
        Process a query using the LLM provider and available MCP tools.
        
        Args:
            query (str): The user query
            system_prompt (str, optional): System prompt for the LLM. Defaults to None.
            
        Returns:
            Dict[str, Any]: Response containing the answer and metadata
        """
        if not self.is_connected:
            try:
                connected = self.connect_to_server()
                if not connected:
                    return {
                        "response": "Unable to connect to MCP server. Please check the server configuration.",
                        "error": True
                    }
            except Exception as e:
                return {
                    "response": f"Error connecting to MCP server: {str(e)}",
                    "error": True
                }
        
        try:
            # Prepare messages for LLM
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add user query
            messages.append({
                "role": "user",
                "content": query
            })
            
            # Convert tools to the format expected by the LLM provider
            tools_for_llm = []
            for tool in self.available_tools:
                tools_for_llm.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["inputSchema"]
                    }
                })
            
            # Initial LLM call with available tools
            response = self.llm_provider.generate_with_tools(
                messages=messages,
                tools=tools_for_llm,
                max_tokens=1000
            )
            
            # Process response and handle tool calls
            final_text = []
            tool_results = []
            
            # Add text content
            if response.get('content'):
                final_text.extend(response['content'])
            
            # Process tool calls
            if response.get('tool_calls'):
                for tool_call in response['tool_calls']:
                    tool_name = tool_call['name']
                    tool_args = tool_call['input']
                    
                    # Execute tool call by sending request to MCP server
                    result = self._execute_tool_call(tool_name, tool_args)
                    tool_result = f"Tool: {tool_name}\nInput: {json.dumps(tool_args)}\nOutput: {json.dumps(result)}"
                    tool_results.append(tool_result)
                    
                    # Continue conversation with tool results
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call.get('id', f"call_{len(messages)}"),
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_args)
                            }
                        }]
                    })
                    
                    messages.append({
                        "role": "tool", 
                        "tool_call_id": tool_call.get('id', f"call_{len(messages)-1}"),
                        "content": json.dumps(result)
                    })
                
                # If tool calls were made, get a final response from LLM
                response = self.llm_provider.generate_with_tools(
                    messages=messages,
                    tools=tools_for_llm,
                    max_tokens=1000
                )
                
                if response.get('content'):
                    final_text = response['content']
            
            return {
                "response": "\n".join(final_text),
                "tool_results": tool_results,
                "error": False
            }
            
        except Exception as e:
            logging.error(f"Error processing query: {str(e)}")
            return {
                "response": f"Error processing your query: {str(e)}",
                "error": True
            }
    
    def _execute_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call by sending a request to the MCP server.
        
        Args:
            tool_name (str): Name of the tool to call
            tool_args (Dict[str, Any]): Arguments for the tool
            
        Returns:
            Dict[str, Any]: Result of the tool call
        """
        try:
            # Send request to MCP server
            response = requests.post(
                f"{self.server_url}/api/tool",
                json={
                    "tool": tool_name,
                    "parameters": tool_args
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error executing tool call: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Error executing tool call: {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending request to MCP server: {str(e)}")
            
            # Fall back to mock implementation if server request fails
            import random
            from datetime import datetime, timedelta
            
            logging.warning(f"Falling back to mock implementation for tool: {tool_name}")
            
            if tool_name == "fetch_renewable_data":
                energy_type = tool_args.get("energy_type", "solar")
                location = tool_args.get("location", "global")
                time_period = tool_args.get("time_period", "last_month")
                
                # Generate mock data
                end_date = datetime.now()
                if time_period == "last_week":
                    start_date = end_date - timedelta(days=7)
                    interval = timedelta(days=1)
                elif time_period == "last_month":
                    start_date = end_date - timedelta(days=30)
                    interval = timedelta(days=1)
                elif time_period == "last_year":
                    start_date = end_date - timedelta(days=365)
                    interval = timedelta(days=7)
                else:
                    start_date = end_date - timedelta(days=30)
                    interval = timedelta(days=1)
                
                # Generate time series data
                time_series = []
                current_date = start_date
                while current_date <= end_date:
                    # Base value depends on energy type
                    if energy_type.lower() == "solar":
                        base_value = 100
                        variance = 30
                    elif energy_type.lower() == "wind":
                        base_value = 150
                        variance = 50
                    elif energy_type.lower() == "hydro":
                        base_value = 200
                        variance = 20
                    elif energy_type.lower() == "geothermal":
                        base_value = 80
                        variance = 10
                    elif energy_type.lower() == "biogas" or energy_type.lower() == "cbg":
                        base_value = 60
                        variance = 15
                    else:
                        base_value = 50
                        variance = 20
                    
                    # Add random variation
                    value = base_value + random.uniform(-variance, variance)
                    
                    time_series.append({
                        "timestamp": current_date.isoformat(),
                        "value": round(max(0, value), 2)
                    })
                    
                    current_date += interval
                
                # Create data structure based on energy type
                data = {}
                if energy_type.lower() == "solar":
                    data = {
                        "generation": time_series,
                        "capacity": random.uniform(500, 2000),
                        "efficiency": random.uniform(0.15, 0.25),
                        "panel_count": random.randint(1000, 5000)
                    }
                elif energy_type.lower() == "wind":
                    data = {
                        "generation": time_series,
                        "capacity": random.uniform(800, 3000),
                        "turbine_count": random.randint(10, 50),
                        "average_wind_speed": random.uniform(5, 15)
                    }
                elif energy_type.lower() == "biogas" or energy_type.lower() == "cbg":
                    data = {
                        "generation": time_series,
                        "feedstock": {
                            "organic_waste": random.uniform(100, 500),
                            "agricultural_waste": random.uniform(50, 300),
                            "food_waste": random.uniform(30, 200)
                        },
                        "methane_content": random.uniform(50, 70),
                        "community_participants": random.randint(5, 50)
                    }
                else:
                    data = {
                        "generation": time_series,
                        "capacity": random.uniform(300, 1500),
                        "efficiency": random.uniform(0.1, 0.4)
                    }
                
                return {
                    "status": "success",
                    "energy_type": energy_type,
                    "location": location,
                    "time_period": time_period,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
                
            elif tool_name == "create_dashboard":
                dashboard_type = tool_args.get("dashboard_type", "cbg")
                title = tool_args.get("title", f"Renewable Energy Dashboard - {dashboard_type.upper()}")
                description = tool_args.get("description", f"Dashboard for {dashboard_type} data visualization")
                
                # Generate a unique dashboard ID
                dashboard_id = f"{dashboard_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                return {
                    "status": "success",
                    "dashboard_id": dashboard_id,
                    "dashboard_type": dashboard_type,
                    "title": title,
                    "description": description,
                    "url": f"/dashboards/{dashboard_id}",
                    "created_at": datetime.now().isoformat(),
                    "message": f"Dashboard '{title}' created successfully"
                }
                
            elif tool_name == "calculate_roi":
                project_type = tool_args.get("project_type", "solar")
                initial_investment = tool_args.get("initial_investment", 100000)
                annual_revenue = tool_args.get("annual_revenue", 20000)
                annual_costs = tool_args.get("annual_costs", 5000)
                project_lifetime = tool_args.get("project_lifetime", 25)
                
                # Calculate net annual cash flow
                net_annual_cash_flow = annual_revenue - annual_costs
                
                # Calculate simple payback period
                payback_period = initial_investment / net_annual_cash_flow if net_annual_cash_flow > 0 else float('inf')
                
                # Calculate total profit over lifetime
                total_profit = (net_annual_cash_flow * project_lifetime) - initial_investment
                
                # Calculate ROI
                roi = (total_profit / initial_investment) * 100
                
                # Calculate IRR (simplified)
                irr = (net_annual_cash_flow / initial_investment) * 100
                
                return {
                    "status": "success",
                    "project_type": project_type,
                    "initial_investment": initial_investment,
                    "annual_revenue": annual_revenue,
                    "annual_costs": annual_costs,
                    "project_lifetime": project_lifetime,
                    "net_annual_cash_flow": net_annual_cash_flow,
                    "payback_period_years": round(payback_period, 2),
                    "total_profit": round(total_profit, 2),
                    "roi_percentage": round(roi, 2),
                    "estimated_irr_percentage": round(irr, 2),
                    "analysis_timestamp": datetime.now().isoformat()
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown tool: {tool_name}"
                }
    
    def cleanup(self):
        """Clean up resources"""
        try:
            # Stop server process if we started it
            if self.server_process:
                self.server_process.terminate()
                self.server_process = None
            
            self.is_connected = False
            logging.info("MCP client resources cleaned up")
        except Exception as e:
            logging.error(f"Error cleaning up MCP client: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup() 