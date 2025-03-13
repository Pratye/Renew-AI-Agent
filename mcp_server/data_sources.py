import requests
import os
import pandas as pd
from datetime import datetime, timedelta
import logging

class DataSource:
    def __init__(self, api_key=None):
        self.api_key = api_key

    async def fetch_data(self, query_params):
        """Base method to be implemented by specific data sources"""
        raise NotImplementedError

class OpenEnergyData(DataSource):
    """Integration with Open Energy Data Initiative API"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.eia.gov/v2"
        self.api_key = os.getenv("EIA_API_KEY")

    async def fetch_data(self, query_params):
        try:
            # Get renewable energy generation data
            endpoint = f"{self.base_url}/electricity/facility-fuel/data"
            params = {
                "api_key": self.api_key,
                "frequency": "monthly",
                "data": ["generation"],
                "facets": {"fuel": ["SUN", "WND", "HYC"]},  # Solar, Wind, Hydroelectric
                "start": query_params.get("start_date"),
                "end": query_params.get("end_date"),
                "sort": [{"column": "period", "direction": "desc"}]
            }
            
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching data from EIA: {str(e)}")
            return None

class SolarGIS(DataSource):
    """Integration with SolarGIS API for solar resource data"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.solargis.com/v2"
        self.api_key = os.getenv("SOLARGIS_API_KEY")

    async def fetch_data(self, query_params):
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Get solar radiation and PV power potential data
            endpoint = f"{self.base_url}/solardata"
            params = {
                "latitude": query_params.get("latitude"),
                "longitude": query_params.get("longitude"),
                "parameters": ["GHI", "DNI", "DIF", "TEMP", "PVout"],
                "timestep": "hourly",
                "startDate": query_params.get("start_date"),
                "endDate": query_params.get("end_date")
            }
            
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching data from SolarGIS: {str(e)}")
            return None

class WindEurope(DataSource):
    """Integration with WindEurope API for wind energy data"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.windeurope.org/v1"
        self.api_key = os.getenv("WINDEUROPE_API_KEY")

    async def fetch_data(self, query_params):
        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Get wind power generation and forecast data
            endpoint = f"{self.base_url}/generation"
            params = {
                "country": query_params.get("country", "all"),
                "startTime": query_params.get("start_date"),
                "endTime": query_params.get("end_date"),
                "resolution": "hourly"
            }
            
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching data from WindEurope: {str(e)}")
            return None

class RESTrendAnalyzer:
    """Analyzes renewable energy trends and patterns"""
    
    @staticmethod
    def analyze_generation_trends(data, timeframe="daily"):
        try:
            df = pd.DataFrame(data)
            
            if timeframe == "daily":
                df = df.resample('D').sum()
            elif timeframe == "weekly":
                df = df.resample('W').sum()
            elif timeframe == "monthly":
                df = df.resample('M').sum()
            
            # Calculate basic statistics
            stats = {
                "total_generation": df.sum().to_dict(),
                "average_generation": df.mean().to_dict(),
                "peak_generation": df.max().to_dict(),
                "growth_rate": df.pct_change().mean().to_dict()
            }
            
            # Identify trends
            trends = {
                "upward_trend": df.pct_change().rolling(window=7).mean() > 0,
                "peak_hours": df.groupby(df.index.hour).mean().nlargest(3).index.tolist(),
                "seasonal_pattern": df.groupby(df.index.month).mean().to_dict()
            }
            
            return {
                "statistics": stats,
                "trends": trends
            }
        except Exception as e:
            logging.error(f"Error analyzing generation trends: {str(e)}")
            return None

class DataAggregator:
    """Aggregates and processes data from multiple sources"""
    def __init__(self):
        self.data_sources = {
            "eia": OpenEnergyData(),
            "solargis": SolarGIS(),
            "windeurope": WindEurope()
        }
        self.analyzer = RESTrendAnalyzer()

    async def fetch_comprehensive_data(self, query):
        """
        Fetch and aggregate data from all available sources
        
        Args:
            query (dict): Query parameters including:
                - start_date
                - end_date
                - location (lat/long or country)
                - data_types (list of required data types)
        """
        try:
            all_data = {}
            
            # Prepare query parameters
            query_params = {
                "start_date": query.get("start_date", (datetime.now() - timedelta(days=30)).isoformat()),
                "end_date": query.get("end_date", datetime.now().isoformat()),
                "latitude": query.get("latitude"),
                "longitude": query.get("longitude"),
                "country": query.get("country")
            }
            
            # Fetch data from each source
            for source_name, source in self.data_sources.items():
                source_data = await source.fetch_data(query_params)
                if source_data:
                    all_data[source_name] = source_data
            
            # Analyze trends if data is available
            if all_data:
                analysis = self.analyzer.analyze_generation_trends(all_data)
                all_data["analysis"] = analysis
            
            return all_data
        except Exception as e:
            logging.error(f"Error aggregating data: {str(e)}")
            return None 