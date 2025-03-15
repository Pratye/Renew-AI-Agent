#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Tool definitions
TOOLS = [
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
    },
    {
        "name": "get_policy_information",
        "description": "Get information about renewable energy policies and incentives",
        "inputSchema": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "Country for policy information"
                },
                "region": {
                    "type": "string",
                    "description": "Region or state within the country (optional)"
                },
                "policy_type": {
                    "type": "string",
                    "description": "Type of policy (tax_incentives, subsidies, regulations, etc.)"
                }
            },
            "required": ["country"]
        }
    },
    {
        "name": "search_renewable_database",
        "description": "Search the renewable energy database for specific information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "filter_by": {
                    "type": "string",
                    "description": "Category to filter by (technology, location, company, project, etc.)"
                },
                "max_results": {
                    "type": "number",
                    "description": "Maximum number of results to return"
                }
            },
            "required": ["query"]
        }
    }
]

class RenewableEnergyMCPServer:
    """
    MCP Server for the Renewable Energy Consultant.
    Provides tools for fetching renewable energy data, creating dashboards,
    calculating ROI, and more.
    """
    
    def __init__(self):
        """Initialize the server"""
        self.tools = TOOLS
    
    def handle_fetch_renewable_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle fetch_renewable_data tool calls.
        
        Args:
            params: Tool parameters
            
        Returns:
            Dict containing the fetched data
        """
        energy_type = params.get("energy_type", "solar")
        location = params.get("location", "global")
        time_period = params.get("time_period", "last_month")
        
        # Generate mock data based on energy type
        data = self._generate_mock_data(energy_type, location, time_period)
        
        return {
            "status": "success",
            "energy_type": energy_type,
            "location": location,
            "time_period": time_period,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    def handle_create_dashboard(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle create_dashboard tool calls.
        
        Args:
            params: Tool parameters
            
        Returns:
            Dict containing the dashboard information
        """
        dashboard_type = params.get("dashboard_type", "cbg")
        title = params.get("title", f"Renewable Energy Dashboard - {dashboard_type.upper()}")
        description = params.get("description", f"Dashboard for {dashboard_type} data visualization")
        
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
    
    def handle_calculate_roi(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle calculate_roi tool calls.
        
        Args:
            params: Tool parameters
            
        Returns:
            Dict containing the ROI calculation results
        """
        project_type = params.get("project_type", "solar")
        initial_investment = params.get("initial_investment", 100000)
        annual_revenue = params.get("annual_revenue", 20000)
        annual_costs = params.get("annual_costs", 5000)
        project_lifetime = params.get("project_lifetime", 25)
        
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
    
    def handle_get_policy_information(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle get_policy_information tool calls.
        
        Args:
            params: Tool parameters
            
        Returns:
            Dict containing policy information
        """
        country = params.get("country", "United States")
        region = params.get("region", "")
        policy_type = params.get("policy_type", "")
        
        # Mock policy data
        policies = self._get_mock_policies(country, region, policy_type)
        
        return {
            "status": "success",
            "country": country,
            "region": region or "All regions",
            "policy_type": policy_type or "All policies",
            "policies": policies,
            "last_updated": datetime.now().isoformat()
        }
    
    def handle_search_renewable_database(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle search_renewable_database tool calls.
        
        Args:
            params: Tool parameters
            
        Returns:
            Dict containing search results
        """
        query = params.get("query", "")
        filter_by = params.get("filter_by", "")
        max_results = params.get("max_results", 5)
        
        # Mock search results
        results = self._get_mock_search_results(query, filter_by, max_results)
        
        return {
            "status": "success",
            "query": query,
            "filter_by": filter_by or "All categories",
            "results_count": len(results),
            "results": results,
            "search_timestamp": datetime.now().isoformat()
        }
    
    def _generate_mock_data(self, energy_type: str, location: str, time_period: str) -> Dict[str, Any]:
        """
        Generate mock data for renewable energy sources.
        
        Args:
            energy_type: Type of renewable energy
            location: Geographic location
            time_period: Time period for the data
            
        Returns:
            Dict containing mock data
        """
        # Determine date range based on time period
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
        if energy_type.lower() == "solar":
            return {
                "generation": time_series,
                "capacity": random.uniform(500, 2000),
                "efficiency": random.uniform(0.15, 0.25),
                "panel_count": random.randint(1000, 5000)
            }
        elif energy_type.lower() == "wind":
            return {
                "generation": time_series,
                "capacity": random.uniform(800, 3000),
                "turbine_count": random.randint(10, 50),
                "average_wind_speed": random.uniform(5, 15)
            }
        elif energy_type.lower() == "biogas" or energy_type.lower() == "cbg":
            return {
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
            return {
                "generation": time_series,
                "capacity": random.uniform(300, 1500),
                "efficiency": random.uniform(0.1, 0.4)
            }
    
    def _get_mock_policies(self, country: str, region: str, policy_type: str) -> List[Dict[str, Any]]:
        """
        Get mock policy data.
        
        Args:
            country: Country for policy information
            region: Region within the country
            policy_type: Type of policy
            
        Returns:
            List of policy information
        """
        policies = []
        
        # US policies
        if country.lower() in ["us", "usa", "united states"]:
            policies.extend([
                {
                    "name": "Federal Investment Tax Credit (ITC)",
                    "type": "tax_incentives",
                    "description": "Tax credit for solar, wind, and geothermal installations",
                    "benefit": "26% tax credit for projects that begin construction in 2022",
                    "eligibility": "Residential and commercial properties",
                    "expiration": "Phases down to 22% in 2023, 10% in 2024 for commercial only"
                },
                {
                    "name": "Modified Accelerated Cost Recovery System (MACRS)",
                    "type": "tax_incentives",
                    "description": "Depreciation deduction for renewable energy properties",
                    "benefit": "5-year depreciation schedule for most renewable technologies",
                    "eligibility": "Business owners who install renewable energy systems"
                },
                {
                    "name": "Renewable Portfolio Standards (RPS)",
                    "type": "regulations",
                    "description": "State-level requirements for renewable energy procurement",
                    "benefit": "Creates market demand for renewable energy",
                    "eligibility": "Varies by state"
                }
            ])
            
            # California-specific policies
            if region.lower() == "california":
                policies.extend([
                    {
                        "name": "California Solar Initiative (CSI)",
                        "type": "subsidies",
                        "description": "Rebates for solar installations",
                        "benefit": "Varies based on system size and performance",
                        "eligibility": "California residents and businesses"
                    },
                    {
                        "name": "Net Energy Metering (NEM)",
                        "type": "regulations",
                        "description": "Credit for excess electricity sent to the grid",
                        "benefit": "Retail rate compensation for excess generation",
                        "eligibility": "California utility customers with renewable systems"
                    }
                ])
        
        # EU policies
        elif country.lower() in ["eu", "european union"]:
            policies.extend([
                {
                    "name": "Renewable Energy Directive (RED II)",
                    "type": "regulations",
                    "description": "Sets targets for renewable energy consumption",
                    "benefit": "32% renewable energy target by 2030",
                    "eligibility": "All EU member states"
                },
                {
                    "name": "European Green Deal",
                    "type": "funding",
                    "description": "Investment plan for sustainable EU economy",
                    "benefit": "€1 trillion in sustainable investments over 10 years",
                    "eligibility": "Various stakeholders across EU member states"
                }
            ])
        
        # Filter by policy type if specified
        if policy_type:
            policies = [p for p in policies if p["type"].lower() == policy_type.lower()]
        
        return policies
    
    def _get_mock_search_results(self, query: str, filter_by: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Get mock search results.
        
        Args:
            query: Search query
            filter_by: Category to filter by
            max_results: Maximum number of results to return
            
        Returns:
            List of search results
        """
        all_results = [
            {
                "title": "Solar PV Efficiency Breakthrough",
                "category": "technology",
                "summary": "New perovskite-silicon tandem solar cells achieve 29.8% efficiency",
                "source": "Renewable Energy Journal",
                "date": "2023-05-15"
            },
            {
                "title": "Wind Farm Development in North Sea",
                "category": "project",
                "summary": "New 1.5 GW offshore wind farm to be developed off the coast of Denmark",
                "source": "Wind Power Monthly",
                "date": "2023-06-22"
            },
            {
                "title": "Community Biogas Initiative in Rural India",
                "category": "project",
                "summary": "50 villages implement community-scale biogas plants for cooking and electricity",
                "source": "Bioenergy International",
                "date": "2023-04-10"
            },
            {
                "title": "NextEra Energy Expands Renewable Portfolio",
                "category": "company",
                "summary": "Company announces 2.8 GW of new solar and wind projects",
                "source": "Clean Energy Wire",
                "date": "2023-07-05"
            },
            {
                "title": "Geothermal Energy Potential in East Africa",
                "category": "location",
                "summary": "Study identifies 10 GW of untapped geothermal potential in East African Rift",
                "source": "Geothermal Resources Council",
                "date": "2023-03-18"
            },
            {
                "title": "Hydrogen Production from Renewable Sources",
                "category": "technology",
                "summary": "Advances in electrolysis technology reduce green hydrogen production costs",
                "source": "International Journal of Hydrogen Energy",
                "date": "2023-02-28"
            },
            {
                "title": "Battery Storage Integration with Renewable Energy",
                "category": "technology",
                "summary": "New battery management systems optimize renewable energy storage",
                "source": "Energy Storage News",
                "date": "2023-08-12"
            }
        ]
        
        # Filter by category if specified
        if filter_by:
            results = [r for r in all_results if r["category"].lower() == filter_by.lower()]
        else:
            results = all_results
        
        # Filter by query if specified
        if query:
            query_lower = query.lower()
            filtered_results = []
            for result in results:
                if (query_lower in result["title"].lower() or 
                    query_lower in result["summary"].lower() or 
                    query_lower in result["category"].lower()):
                    filtered_results.append(result)
            results = filtered_results
        
        # Limit results
        return results[:max_results]

class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the MCP server"""
    
    def __init__(self, *args, **kwargs):
        self.server_instance = RenewableEnergyMCPServer()
        super().__init__(*args, **kwargs)
    
    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def do_GET(self):
        if self.path == "/health":
            self._set_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode())
        elif self.path == "/tools":
            self._set_headers()
            self.wfile.write(json.dumps({"tools": TOOLS}).encode())
        else:
            self._set_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            
            if self.path == "/api/tool":
                tool_name = data.get("tool")
                parameters = data.get("parameters", {})
                
                if tool_name == "fetch_renewable_data":
                    result = self.server_instance.handle_fetch_renewable_data(parameters)
                elif tool_name == "create_dashboard":
                    result = self.server_instance.handle_create_dashboard(parameters)
                elif tool_name == "calculate_roi":
                    result = self.server_instance.handle_calculate_roi(parameters)
                elif tool_name == "get_policy_information":
                    result = self.server_instance.handle_get_policy_information(parameters)
                elif tool_name == "search_renewable_database":
                    result = self.server_instance.handle_search_renewable_database(parameters)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
                
                self._set_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self._set_headers()
                self.wfile.write(json.dumps({"error": "Not found"}).encode())
        
        except json.JSONDecodeError:
            self._set_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
        except Exception as e:
            self._set_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

def run_server(port=5002):
    """Run the HTTP server"""
    server_address = ("", port)
    httpd = HTTPServer(server_address, MCPRequestHandler)
    logging.info(f"Starting MCP server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    try:
        port = int(os.getenv("SERVER_PORT", 5002))
        run_server(port)
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        sys.exit(1) 