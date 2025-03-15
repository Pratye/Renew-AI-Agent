import requests
import json
import os
import logging
from urllib.parse import urljoin
import time
import uuid

class MCPServer:
    def __init__(self, server_url=None, api_key=None, auto_generate_key=False):
        """
        Initialize the MCP server client.
        
        Args:
            server_url (str, optional): The URL of the MCP server. Defaults to None.
            api_key (str, optional): The API key for the MCP server. Defaults to None.
            auto_generate_key (bool, optional): Whether to automatically generate a new key if none exists. Defaults to False.
        """
        self.server_url = server_url or os.getenv("MCP_SERVER_URL")
        if not self.server_url:
            raise ValueError("MCP server URL is required")
            
        # Fix server URL if it's pointing to mcp-server:5001
        if "mcp-server:5001" in self.server_url:
            self.server_url = "http://localhost:5002"
            logging.info(f"Updated server URL from mcp-server:5001 to {self.server_url}")
        
        # API key handling
        self.api_key = api_key or os.getenv("MCP_API_KEY")
        if not self.api_key and auto_generate_key:
            logging.info("No API key found, attempting to generate one...")
            self.api_key = self._get_api_key()
        elif not self.api_key:
            raise ValueError("MCP API key is required. Either provide it directly, set MCP_API_KEY in environment, or set auto_generate_key=True")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Flag to indicate if we should use mock data instead of real API calls
        self.use_mock_mode = False
        
        logging.info("MCP server client initialized")
    
    def _get_api_key(self):
        """
        Get an API key from the MCP server.
        
        Returns:
            str: The API key
        """
        try:
            # Check if we're trying to connect to mcp-server:5001 and fix it
            if "mcp-server:5001" in self.server_url:
                self.server_url = "http://localhost:5002"
                logging.info(f"Updated server URL to {self.server_url}")
                
            # Get client credentials from environment
            client_id = os.getenv("MCP_CLIENT_ID")
            client_secret = os.getenv("MCP_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                raise ValueError("MCP client credentials not found in environment")
            
            # Request new API key from server
            response = requests.post(
                urljoin(self.server_url, "api/generate_key"),
                json={
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            if "error" in data:
                raise Exception(f"MCP server error: {data['error']}")
            
            # Store the API key in environment for future use
            os.environ["MCP_API_KEY"] = data["api_key"]
            
            return data["api_key"]
        
        except Exception as e:
            logging.error(f"Error getting API key from MCP server: {str(e)}")
            raise Exception(f"Failed to get API key: {str(e)}")
    
    def refresh_api_key(self):
        """
        Refresh the API key.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            new_api_key = self._get_api_key()
            self.api_key = new_api_key
            self.headers["Authorization"] = f"Bearer {new_api_key}"
            return True
        except Exception as e:
            logging.error(f"Error refreshing API key: {str(e)}")
            return False
    
    def fetch_data(self, query, timeout=60, dashboard_type=None):
        """
        Fetch data from the MCP server based on a query.
        
        Args:
            query (str): The query to fetch data for
            timeout (int, optional): Timeout in seconds. Defaults to 60.
            dashboard_type (str, optional): Type of dashboard to fetch data for. Defaults to None.
            
        Returns:
            dict: The fetched data
        """
        # If in mock mode, always generate mock data
        if self.use_mock_mode:
            logging.info(f"Using mock data for query: {query}")
            dashboard_type = dashboard_type or self._infer_dashboard_type_from_query(query)
            return self._generate_mock_data(dashboard_type, query)
            
        try:
            # Prepare the request payload
            payload = {
                "query": query,
                "data_sources": ["renewable_energy_db", "web_scraping", "external_apis"],
                "format": "json"
            }
            
            # Add dashboard-specific parameters if a dashboard type is specified
            if dashboard_type:
                payload["dashboard_type"] = dashboard_type
                payload["include_visualization_data"] = True
                
                # Add specific data requirements based on dashboard type
                if dashboard_type == "cbg":
                    payload["data_requirements"] = ["generation", "community", "forecast", "environmental_impact"]
                elif dashboard_type == "solar_farm":
                    payload["data_requirements"] = ["solar_generation", "irradiance", "efficiency", "forecast"]
                elif dashboard_type == "wind_farm":
                    payload["data_requirements"] = ["wind_generation", "wind_speed", "turbine_efficiency", "forecast"]
                elif dashboard_type == "hybrid_plant":
                    payload["data_requirements"] = ["generation_mix", "efficiency_comparison", "forecast", "optimization"]
            
            # Send the request to the MCP server
            response = requests.post(
                urljoin(self.server_url, "api/data/fetch"),
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Check if the response contains an error
            if "error" in data:
                raise Exception(f"MCP server error: {data['error']}")
            
            # If no data was returned but a dashboard was requested, generate mock data
            if not data.get("data") and dashboard_type:
                logging.warning(f"No data returned from MCP server for dashboard type {dashboard_type}. Generating mock data.")
                data = self._generate_mock_data(dashboard_type, query)
            
            return data
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data from MCP server: {str(e)}")
            # If there's an error but a dashboard was requested, generate mock data
            if dashboard_type:
                logging.warning(f"Error connecting to MCP server. Generating mock data for {dashboard_type} dashboard.")
                return self._generate_mock_data(dashboard_type, query)
            raise Exception(f"Failed to fetch data: {str(e)}")
    
    def _infer_dashboard_type_from_query(self, query):
        """
        Infer the dashboard type from a query.
        
        Args:
            query (str): The query to analyze
            
        Returns:
            str: The inferred dashboard type
        """
        query_lower = query.lower()
        
        # Check for specific energy types
        if any(term in query_lower for term in ['solar', 'sun', 'photovoltaic', 'pv']):
            return 'solar_farm'
        elif any(term in query_lower for term in ['wind', 'turbine', 'windmill']):
            return 'wind_farm'
        elif any(term in query_lower for term in ['bio', 'gas', 'methane', 'organic', 'waste', 'community', 'compressed']):
            return 'cbg'
        elif any(term in query_lower for term in ['multiple', 'combined', 'hybrid', 'mix', 'integrated']):
            return 'hybrid_plant'
        
        # Default to CBG if no specific type is mentioned
        return 'cbg'
    
    def _generate_mock_data(self, dashboard_type, query):
        """
        Generate mock data for dashboard creation when real data is unavailable.
        
        Args:
            dashboard_type (str): Type of dashboard to generate data for
            query (str): The original query
            
        Returns:
            dict: Mock data for dashboard creation
        """
        import random
        from datetime import datetime, timedelta
        
        # Generate timestamps for time series data (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        timestamps = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(31)]
        
        mock_data = {"data": {}}
        
        # Generate common data for all dashboard types
        mock_data["data"]["generation"] = [
            {"timestamp": ts, "value": random.uniform(50, 200)} for ts in timestamps
        ]
        
        # Generate dashboard-specific mock data
        if dashboard_type == "cbg":
            # Community data
            mock_data["data"]["community"] = [
                {
                    "participant_id": f"user_{i}",
                    "latitude": random.uniform(40, 42),
                    "longitude": random.uniform(-74, -72),
                    "generation": random.uniform(5, 20),
                    "cost_savings": random.uniform(100, 500),
                    "grid_credits": random.uniform(50, 200),
                    "tax_incentives": random.uniform(20, 100)
                } for i in range(10)
            ]
            
            # Environmental impact
            mock_data["data"]["environmental_impact"] = {
                "co2_avoided": random.uniform(1000, 5000),
                "trees_equivalent": random.uniform(50, 200),
                "water_saved": random.uniform(5000, 20000)
            }
            
        elif dashboard_type == "solar_farm":
            # Solar-specific data
            mock_data["data"]["solar"] = {
                "capacity": random.uniform(500, 2000),
                "efficiency": random.uniform(0.15, 0.25),
                "panel_count": random.randint(1000, 5000),
                "irradiance_data": [
                    {"timestamp": ts, "value": random.uniform(3, 7)} for ts in timestamps
                ]
            }
            
        elif dashboard_type == "wind_farm":
            # Wind-specific data
            mock_data["data"]["wind"] = {
                "capacity": random.uniform(800, 3000),
                "turbine_count": random.randint(10, 50),
                "average_wind_speed": random.uniform(5, 15),
                "wind_data": [
                    {"timestamp": ts, "value": random.uniform(3, 20)} for ts in timestamps
                ]
            }
            
        elif dashboard_type == "hybrid_plant":
            # Hybrid plant data
            mock_data["data"]["mix"] = {
                "solar_percentage": random.uniform(0.3, 0.6),
                "wind_percentage": random.uniform(0.2, 0.5),
                "other_percentage": random.uniform(0.1, 0.3),
                "total_capacity": random.uniform(1000, 5000)
            }
        
        # Add forecast data
        mock_data["data"]["forecast"] = [
            {"timestamp": (end_date + timedelta(days=i)).strftime("%Y-%m-%d"), 
             "value": random.uniform(50, 200),
             "horizon": "24h" if i < 1 else "7d",
             "confidence": random.uniform(0.7, 0.95)} 
            for i in range(1, 8)
        ]
        
        return mock_data
    
    def web_search(self, query, timeout=30):
        """
        Perform a web search through the MCP server.
        
        Args:
            query (str): The search query
            timeout (int, optional): Timeout in seconds. Defaults to 30.
            
        Returns:
            dict: The search results
        """
        try:
            # Prepare the request payload
            payload = {
                "query": query,
                "num_results": 10,
                "include_snippets": True
            }
            
            # Send the request to the MCP server
            response = requests.post(
                urljoin(self.server_url, "api/web/search"),
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Check if the response contains an error
            if "error" in data:
                raise Exception(f"MCP server error: {data['error']}")
            
            return data
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Error performing web search through MCP server: {str(e)}")
            raise Exception(f"Failed to perform web search: {str(e)}")
    
    def run_data_analysis(self, data, analysis_type, parameters=None):
        """
        Run data analysis on the MCP server.
        
        Args:
            data (dict): The data to analyze
            analysis_type (str): The type of analysis to run
            parameters (dict, optional): Additional parameters for the analysis. Defaults to None.
            
        Returns:
            dict: The analysis results
        """
        try:
            # Prepare the request payload
            payload = {
                "data": data,
                "analysis_type": analysis_type,
                "parameters": parameters or {}
            }
            
            # Send the request to the MCP server
            response = requests.post(
                urljoin(self.server_url, "api/data/analyze"),
                headers=self.headers,
                json=payload
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Check if the response contains an error
            if "error" in result:
                raise Exception(f"MCP server error: {result['error']}")
            
            return result
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Error running data analysis on MCP server: {str(e)}")
            raise Exception(f"Failed to run data analysis: {str(e)}")
    
    def generate_visualization(self, data, visualization_type, parameters=None):
        """
        Generate a visualization on the MCP server.
        
        Args:
            data (dict): The data to visualize
            visualization_type (str): The type of visualization to generate
            parameters (dict, optional): Additional parameters for the visualization. Defaults to None.
            
        Returns:
            str: The URL of the generated visualization
        """
        try:
            # Prepare the request payload
            payload = {
                "data": data,
                "visualization_type": visualization_type,
                "parameters": parameters or {}
            }
            
            # Send the request to the MCP server
            response = requests.post(
                urljoin(self.server_url, "api/visualization/generate"),
                headers=self.headers,
                json=payload
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Check if the response contains an error
            if "error" in result:
                raise Exception(f"MCP server error: {result['error']}")
            
            # Return the URL of the generated visualization
            return result.get("visualization_url")
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Error generating visualization on MCP server: {str(e)}")
            raise Exception(f"Failed to generate visualization: {str(e)}")
    
    def create_dashboard(self, title, description, data, layout=None, auto_refresh=False, refresh_interval=300):
        """
        Create a new dashboard on the MCP server.
        
        Args:
            title (str): Dashboard title
            description (str): Dashboard description
            data (dict): Data to be displayed in the dashboard
            layout (dict, optional): Custom layout configuration. Defaults to None.
            auto_refresh (bool, optional): Whether to auto-refresh the dashboard. Defaults to False.
            refresh_interval (int, optional): Refresh interval in seconds. Defaults to 300.
            
        Returns:
            dict: Dashboard information including URL and ID
        """
        # If in mock mode, generate a static HTML dashboard
        if self.use_mock_mode:
            logging.info(f"Creating static HTML dashboard for: {title}")
            return self._create_static_dashboard(title, description, data, layout)
            
        try:
            if not self.server_url or not self.api_key:
                logging.warning("MCP server not properly configured, falling back to mock mode")
                self.use_mock_mode = True
                return self._create_static_dashboard(title, description, data, layout)
            
            # Ensure we have data to work with
            if not data or not isinstance(data, dict) or not data.get('data'):
                logging.warning("No valid data provided for dashboard. Generating mock data.")
                # Extract dashboard type from layout if available
                dashboard_type = layout.get('type') if layout and isinstance(layout, dict) else 'cbg'
                data = self._generate_mock_data(dashboard_type, description)
            
            # Prepare the dashboard configuration
            dashboard_config = {
                "title": title,
                "description": description,
                "data": data,
                "layout": layout or self._generate_default_layout(data),
                "settings": {
                    "auto_refresh": auto_refresh,
                    "refresh_interval": refresh_interval
                }
            }
            
            # Send request to create dashboard
            try:
                response = requests.post(
                    urljoin(self.server_url, "api/dashboards/create"),
                    headers=self.headers,
                    json=dashboard_config,
                    timeout=10  # Shorter timeout to prevent hanging
                )
                
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    raise Exception(f"MCP server error: {result['error']}")
                
                return {
                    "dashboard_id": result["dashboard_id"],
                    "url": result["dashboard_url"],
                    "embed_code": result.get("embed_code")
                }
            except requests.exceptions.RequestException as e:
                logging.error(f"Error communicating with MCP server: {str(e)}")
                # Fall back to static HTML dashboard
                self.use_mock_mode = True
                return self._create_static_dashboard(title, description, data, layout)
        
        except Exception as e:
            logging.error(f"Error creating dashboard: {str(e)}")
            # Fall back to static HTML dashboard
            self.use_mock_mode = True
            return self._create_static_dashboard(title, description, data, layout)
            
    def _create_static_dashboard(self, title, description, data, layout=None):
        """
        Create a static HTML dashboard.
        
        Args:
            title (str): Dashboard title
            description (str): Dashboard description
            data (dict): Dashboard data
            layout (dict, optional): Dashboard layout. Defaults to None.
            
        Returns:
            dict: Dashboard information
        """
        dashboard_id = str(uuid.uuid4())
        
        # Generate the dashboard HTML
        dashboard_html = self._generate_static_dashboard_html(
            dashboard_id=dashboard_id,
            title=title,
            description=description,
            data=data,
            layout=layout
        )
        
        # Save the dashboard HTML to a file
        dashboard_dir = os.path.join(os.getcwd(), 'static', 'dashboards')
        os.makedirs(dashboard_dir, exist_ok=True)
        
        dashboard_file = os.path.join(dashboard_dir, f"{dashboard_id}.html")
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_html)
        
        # Return the dashboard information with a URL that points to the static file
        return {
            "dashboard_id": dashboard_id,
            "url": f"/static/dashboards/{dashboard_id}.html",
            "embed_code": f'<iframe src="/static/dashboards/{dashboard_id}.html" width="100%" height="600px" frameborder="0"></iframe>',
            "note": "This is a static dashboard created in mock mode."
        }
    
    def _generate_static_dashboard_html(self, dashboard_id, title, description, data, layout=None):
        """
        Generate a static HTML dashboard.
        
        Args:
            dashboard_id (str): The dashboard ID
            title (str): The dashboard title
            description (str): The dashboard description
            data (dict): The dashboard data
            layout (dict, optional): The dashboard layout. Defaults to None.
            
        Returns:
            str: The HTML content for the dashboard
        """
        import json
        import plotly.graph_objects as go
        import plotly.express as px
        from plotly.subplots import make_subplots
        import pandas as pd
        from datetime import datetime
        
        # Extract dashboard type from layout
        dashboard_type = layout.get('type') if layout and isinstance(layout, dict) else 'cbg'
        
        # Create a subplot figure
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=["Production Over Time", "Key Metrics", "Resource Distribution", "Environmental Impact"],
            specs=[[{"type": "scatter"}, {"type": "indicator"}],
                   [{"type": "pie"}, {"type": "bar"}]]
        )
        
        # Process data based on dashboard type
        if dashboard_type == 'cbg':
            # Add time series data
            if 'generation' in data.get('data', {}):
                df = pd.DataFrame(data['data']['generation'])
                fig.add_trace(
                    go.Scatter(x=df['timestamp'], y=df['value'], mode='lines+markers', name='Production'),
                    row=1, col=1
                )
            
            # Add gauge for current production
            current_value = 0
            if 'generation' in data.get('data', {}):
                current_value = data['data']['generation'][-1]['value'] if data['data']['generation'] else 0
            
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=current_value,
                    title={'text': "Current Production (m³/day)"},
                    gauge={'axis': {'range': [0, 200]},
                           'bar': {'color': "darkgreen"},
                           'steps': [
                               {'range': [0, 50], 'color': "lightgray"},
                               {'range': [50, 150], 'color': "lightgreen"},
                               {'range': [150, 200], 'color': "green"}
                           ]}
                ),
                row=1, col=2
            )
            
            # Add pie chart for resource distribution
            if 'community' in data.get('data', {}):
                community_data = data['data']['community']
                resource_labels = [f"User {i+1}" for i in range(len(community_data))]
                resource_values = [item['generation'] for item in community_data]
                
                fig.add_trace(
                    go.Pie(labels=resource_labels, values=resource_values, name="Resource Distribution"),
                    row=2, col=1
                )
            
            # Add bar chart for environmental impact
            if 'environmental_impact' in data.get('data', {}):
                env_impact = data['data']['environmental_impact']
                impact_labels = list(env_impact.keys())
                impact_values = list(env_impact.values())
                
                fig.add_trace(
                    go.Bar(x=impact_labels, y=impact_values, name="Environmental Impact"),
                    row=2, col=2
                )
        
        elif dashboard_type == 'solar_farm':
            # Implement solar farm specific visualizations
            # Add time series data
            if 'generation' in data.get('data', {}):
                df = pd.DataFrame(data['data']['generation'])
                fig.add_trace(
                    go.Scatter(x=df['timestamp'], y=df['value'], mode='lines+markers', name='Solar Generation'),
                    row=1, col=1
                )
            
            # Add gauge for current production
            current_value = 0
            if 'generation' in data.get('data', {}):
                current_value = data['data']['generation'][-1]['value'] if data['data']['generation'] else 0
            
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=current_value,
                    title={'text': "Current Output (kW)"},
                    gauge={'axis': {'range': [0, 2000]},
                           'bar': {'color': "darkorange"},
                           'steps': [
                               {'range': [0, 500], 'color': "lightgray"},
                               {'range': [500, 1500], 'color': "lightyellow"},
                               {'range': [1500, 2000], 'color': "orange"}
                           ]}
                ),
                row=1, col=2
            )
            
            # Add pie chart for panel efficiency
            if 'solar' in data.get('data', {}):
                solar_data = data['data']['solar']
                fig.add_trace(
                    go.Pie(
                        labels=["Efficient", "Average", "Below Average"],
                        values=[solar_data.get('efficiency', 0.2) * 100, 
                                (1 - solar_data.get('efficiency', 0.2)) * 70, 
                                (1 - solar_data.get('efficiency', 0.2)) * 30],
                        name="Panel Efficiency"
                    ),
                    row=2, col=1
                )
            
            # Add bar chart for irradiance data
            if 'solar' in data.get('data', {}) and 'irradiance_data' in data['data']['solar']:
                irradiance_data = data['data']['solar']['irradiance_data']
                df = pd.DataFrame(irradiance_data)
                
                fig.add_trace(
                    go.Bar(x=df['timestamp'], y=df['value'], name="Solar Irradiance"),
                    row=2, col=2
                )
        
        elif dashboard_type == 'wind_farm':
            # Implement wind farm specific visualizations
            # Add time series data
            if 'generation' in data.get('data', {}):
                df = pd.DataFrame(data['data']['generation'])
                fig.add_trace(
                    go.Scatter(x=df['timestamp'], y=df['value'], mode='lines+markers', name='Wind Generation'),
                    row=1, col=1
                )
            
            # Add gauge for current production
            current_value = 0
            if 'generation' in data.get('data', {}):
                current_value = data['data']['generation'][-1]['value'] if data['data']['generation'] else 0
            
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=current_value,
                    title={'text': "Current Output (kW)"},
                    gauge={'axis': {'range': [0, 3000]},
                           'bar': {'color': "darkblue"},
                           'steps': [
                               {'range': [0, 1000], 'color': "lightgray"},
                               {'range': [1000, 2000], 'color': "lightblue"},
                               {'range': [2000, 3000], 'color': "blue"}
                           ]}
                ),
                row=1, col=2
            )
            
            # Add pie chart for turbine distribution
            if 'wind' in data.get('data', {}):
                wind_data = data['data']['wind']
                fig.add_trace(
                    go.Pie(
                        labels=["High Output", "Medium Output", "Low Output"],
                        values=[40, 35, 25],  # Example values
                        name="Turbine Performance"
                    ),
                    row=2, col=1
                )
            
            # Add bar chart for wind speed data
            if 'wind' in data.get('data', {}) and 'wind_data' in data['data']['wind']:
                wind_speed_data = data['data']['wind']['wind_data']
                df = pd.DataFrame(wind_speed_data)
                
                fig.add_trace(
                    go.Bar(x=df['timestamp'], y=df['value'], name="Wind Speed"),
                    row=2, col=2
                )
        
        elif dashboard_type == 'hybrid_plant':
            # Implement hybrid plant specific visualizations
            # Add time series data
            if 'generation' in data.get('data', {}):
                df = pd.DataFrame(data['data']['generation'])
                fig.add_trace(
                    go.Scatter(x=df['timestamp'], y=df['value'], mode='lines+markers', name='Total Generation'),
                    row=1, col=1
                )
            
            # Add gauge for current production
            current_value = 0
            if 'generation' in data.get('data', {}):
                current_value = data['data']['generation'][-1]['value'] if data['data']['generation'] else 0
            
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=current_value,
                    title={'text': "Current Output (kW)"},
                    gauge={'axis': {'range': [0, 5000]},
                           'bar': {'color': "darkpurple"},
                           'steps': [
                               {'range': [0, 1500], 'color': "lightgray"},
                               {'range': [1500, 3500], 'color': "lavender"},
                               {'range': [3500, 5000], 'color': "purple"}
                           ]}
                ),
                row=1, col=2
            )
            
            # Add pie chart for energy mix
            if 'mix' in data.get('data', {}):
                mix_data = data['data']['mix']
                fig.add_trace(
                    go.Pie(
                        labels=["Solar", "Wind", "Other"],
                        values=[
                            mix_data.get('solar_percentage', 0.4) * 100,
                            mix_data.get('wind_percentage', 0.4) * 100,
                            mix_data.get('other_percentage', 0.2) * 100
                        ],
                        name="Energy Mix"
                    ),
                    row=2, col=1
                )
            
            # Add bar chart for capacity utilization
            fig.add_trace(
                go.Bar(
                    x=["Solar", "Wind", "Other", "Total"],
                    y=[
                        data['data'].get('mix', {}).get('solar_percentage', 0.4) * data['data'].get('mix', {}).get('total_capacity', 1000),
                        data['data'].get('mix', {}).get('wind_percentage', 0.4) * data['data'].get('mix', {}).get('total_capacity', 1000),
                        data['data'].get('mix', {}).get('other_percentage', 0.2) * data['data'].get('mix', {}).get('total_capacity', 1000),
                        data['data'].get('mix', {}).get('total_capacity', 1000)
                    ],
                    name="Capacity (kW)"
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            title_text=f"{title}",
            height=800,
            width=1000,
            showlegend=True,
            template="plotly_white"
        )
        
        # Add description as annotation
        fig.add_annotation(
            text=description,
            xref="paper", yref="paper",
            x=0.5, y=-0.1,
            showarrow=False,
            font=dict(size=12)
        )
        
        # Generate HTML
        dashboard_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .dashboard-container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                }}
                .description {{
                    color: #666;
                    margin-bottom: 20px;
                }}
                .dashboard-id {{
                    color: #999;
                    font-size: 12px;
                    margin-top: 20px;
                }}
                .data-timestamp {{
                    color: #999;
                    font-size: 12px;
                    margin-top: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="dashboard-container">
                <h1>{title}</h1>
                <div class="description">{description}</div>
                <div id="dashboard"></div>
                <div class="data-timestamp">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                <div class="dashboard-id">Dashboard ID: {dashboard_id}</div>
            </div>
            <script>
                var dashboardData = {json.dumps(fig.to_dict())};
                Plotly.newPlot('dashboard', dashboardData.data, dashboardData.layout);
            </script>
        </body>
        </html>
        """
        
        return dashboard_html
    
    def update_dashboard(self, dashboard_id, data=None, layout=None, settings=None):
        """
        Update an existing dashboard on the MCP server.
        
        Args:
            dashboard_id (str): ID of the dashboard to update
            data (dict, optional): New data to update. Defaults to None.
            layout (dict, optional): New layout configuration. Defaults to None.
            settings (dict, optional): New dashboard settings. Defaults to None.
            
        Returns:
            dict: Updated dashboard information
        """
        try:
            if not self.server_url or not self.api_key:
                raise ValueError("MCP server not properly configured")
            
            # Prepare the update payload
            update_payload = {
                "dashboard_id": dashboard_id
            }
            
            if data is not None:
                update_payload["data"] = data
            if layout is not None:
                update_payload["layout"] = layout
            if settings is not None:
                update_payload["settings"] = settings
            
            # Send update request
            response = requests.put(
                urljoin(self.server_url, "api/dashboards/update"),
                headers=self.headers,
                json=update_payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise Exception(f"MCP server error: {result['error']}")
            
            return result
        
        except Exception as e:
            logging.error(f"Error updating dashboard: {str(e)}")
            raise Exception(f"Failed to update dashboard: {str(e)}")
    
    def _generate_default_layout(self, data):
        """
        Generate a default dashboard layout based on the data structure.
        
        Args:
            data (dict): The data to analyze for layout generation
            
        Returns:
            dict: Default layout configuration
        """
        try:
            layout = {
                "type": "grid",
                "columns": 2,
                "rows": [],
                "widgets": []
            }
            
            # Analyze data structure and create appropriate widgets
            if isinstance(data, dict):
                # Add summary statistics widget
                layout["widgets"].append({
                    "type": "summary",
                    "position": {"row": 0, "col": 0},
                    "size": {"width": 1, "height": 1},
                    "title": "Key Metrics",
                    "data_source": "summary_stats"
                })
                
                # Add time series chart if time-based data is present
                if any(key.lower() in ["date", "time", "timestamp"] for key in data.keys()):
                    layout["widgets"].append({
                        "type": "line_chart",
                        "position": {"row": 0, "col": 1},
                        "size": {"width": 1, "height": 1},
                        "title": "Trends Over Time",
                        "data_source": "time_series"
                    })
                
                # Add distribution chart
                layout["widgets"].append({
                    "type": "bar_chart",
                    "position": {"row": 1, "col": 0},
                    "size": {"width": 1, "height": 1},
                    "title": "Distribution Analysis",
                    "data_source": "distribution"
                })
                
                # Add data table
                layout["widgets"].append({
                    "type": "table",
                    "position": {"row": 1, "col": 1},
                    "size": {"width": 1, "height": 1},
                    "title": "Raw Data",
                    "data_source": "raw_data"
                })
            
            return layout
        
        except Exception as e:
            logging.error(f"Error generating default layout: {str(e)}")
            return {"type": "grid", "columns": 1, "widgets": [{"type": "table", "data_source": "raw_data"}]}
    
    def check_health(self):
        """
        Check if the MCP server is available and responding.
        
        Returns:
            bool: True if the server is healthy, False otherwise
        """
        try:
            # Check if we're trying to connect to mcp-server:5001 and fix it
            if "mcp-server:5001" in self.server_url:
                self.server_url = "http://localhost:5002"
                logging.info(f"Updated server URL to {self.server_url}")
                
            # Try to connect to the health endpoint
            try:
                response = requests.get(
                    urljoin(self.server_url, "api/health"),
                    headers=self.headers,
                    timeout=3  # Short timeout for health check
                )
                
                # Check if the response is successful
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "ok":
                        return True
                
                # If we get here, the health check failed
                logging.warning(f"MCP server health check failed with status code {response.status_code}")
                return False
            except requests.exceptions.RequestException as e:
                logging.warning(f"MCP server health check failed with connection error: {str(e)}")
                return False
            
        except Exception as e:
            logging.warning(f"MCP server health check failed: {str(e)}")
            return False 