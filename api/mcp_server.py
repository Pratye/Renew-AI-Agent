import requests
import json
import os
import logging
from urllib.parse import urljoin
import time

class MCPServer:
    def __init__(self, server_url=None, api_key=None):
        """
        Initialize the MCP server client.
        
        Args:
            server_url (str, optional): The URL of the MCP server. Defaults to None.
            api_key (str, optional): The API key for the MCP server. Defaults to None.
        """
        self.server_url = server_url or os.getenv("MCP_SERVER_URL")
        self.api_key = api_key or os.getenv("MCP_API_KEY")
        
        if not self.server_url or not self.api_key:
            logging.warning("MCP server URL or API key not provided. Some features will be limited.")
            return
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logging.info("MCP server client initialized")
    
    def fetch_data(self, query, timeout=60):
        """
        Fetch data from the MCP server based on a query.
        
        Args:
            query (str): The query to fetch data for
            timeout (int, optional): Timeout in seconds. Defaults to 60.
            
        Returns:
            dict: The fetched data
        """
        try:
            # Prepare the request payload
            payload = {
                "query": query,
                "data_sources": ["renewable_energy_db", "web_scraping", "external_apis"],
                "format": "json"
            }
            
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
            
            return data
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data from MCP server: {str(e)}")
            raise Exception(f"Failed to fetch data: {str(e)}")
    
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
        try:
            if not self.server_url or not self.api_key:
                raise ValueError("MCP server not properly configured")
            
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
            response = requests.post(
                urljoin(self.server_url, "api/dashboards/create"),
                headers=self.headers,
                json=dashboard_config
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
        
        except Exception as e:
            logging.error(f"Error creating dashboard: {str(e)}")
            raise Exception(f"Failed to create dashboard: {str(e)}")
    
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