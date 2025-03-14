import requests
import os
import pandas as pd
from datetime import datetime, timedelta
import logging
import numpy as np
from bs4 import BeautifulSoup
import json
import aiohttp
import asyncio
from .vector_store import VectorStore

class WebDataSource:
    """Web scraping fallback for renewable energy data"""
    
    def __init__(self):
        """Initialize WebDataSource with vector store"""
        self.vector_store = VectorStore()
    
    @staticmethod
    async def search_web(query):
        """Generic web search function"""
        try:
            async with aiohttp.ClientSession() as session:
                # Use DuckDuckGo's HTML API (no API key needed)
                url = f"https://html.duckduckgo.com/html/"
                params = {
                    "q": query,
                    "kl": "us-en",  # Language/region
                    "k1": "-1"      # Safe search off
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                
                async with session.post(url, data=params, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        results = []
                        
                        # Extract search results
                        for result in soup.select('.result'):
                            title = result.select_one('.result__title')
                            snippet = result.select_one('.result__snippet')
                            if title and snippet:
                                results.append({
                                    'title': title.get_text(strip=True),
                                    'snippet': snippet.get_text(strip=True)
                                })
                        
                        return results[:5]  # Return top 5 results
                    else:
                        logging.warning(f"Web search failed with status: {response.status}")
                        return None
        except Exception as e:
            logging.error(f"Error during web search: {str(e)}")
            return None

    @staticmethod
    async def fetch_eia_data(query_params):
        """Fetch EIA data from public sources"""
        try:
            # First, try to get similar data from vector store
            similar_data = await self.vector_store.query_data(
                "eia",
                f"renewable energy generation statistics {query_params.get('start_date')} to {query_params.get('end_date')}",
                n_results=5
            )
            
            if similar_data:
                logging.info("Found relevant EIA data in vector store")
                return {
                    "data": [item["data"] for item in similar_data],
                    "source": "vector_store"
                }
            
            # If no relevant data found, scrape from web
            start_date = pd.to_datetime(query_params.get("start_date")).strftime("%B %Y")
            end_date = pd.to_datetime(query_params.get("end_date")).strftime("%B %Y")
            query = f"US renewable energy generation statistics {start_date} to {end_date} EIA data"
            
            results = await WebDataSource.search_web(query)
            if not results:
                return None
            
            # Process search results into a structured format
            data = []
            for result in results:
                # Extract numerical data from snippets using regex
                import re
                numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(GWh|MWh|kWh|MW|GW|kW)', result['snippet'])
                if numbers:
                    for value, unit in numbers:
                        data.append({
                            "value": float(value),
                            "unit": unit,
                            "source": result['title'],
                            "description": result['snippet']
                        })
            
            # Store the scraped data in vector store
            if data:
                await self.vector_store.store_data("eia", data)
            
            return {
                "data": data,
                "source": "web_scraping",
                "period": f"{start_date} to {end_date}"
            }
        except Exception as e:
            logging.error(f"Error processing EIA web data: {str(e)}")
            return None

    @staticmethod
    async def fetch_solar_data(query_params):
        """Fetch solar data from public sources"""
        try:
            # First, try to get similar data from vector store
            lat = query_params.get("latitude", 40.7128)
            lon = query_params.get("longitude", -74.0060)
            similar_data = await self.vector_store.query_data(
                "solar",
                f"solar irradiance data {lat:.2f}N {abs(lon):.2f}{'E' if lon >= 0 else 'W'}",
                n_results=5
            )
            
            if similar_data:
                logging.info("Found relevant solar data in vector store")
                return {
                    "data": [item["data"] for item in similar_data],
                    "source": "vector_store"
                }
            
            # If no relevant data found, scrape from web
            query = f"solar irradiance data {lat:.2f}N {abs(lon):.2f}{'E' if lon >= 0 else 'W'} current statistics"
            
            results = await WebDataSource.search_web(query)
            if not results:
                return None
            
            # Process search results
            data = []
            for result in results:
                # Extract numerical data from snippets
                import re
                numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(W/m²|kWh/m²/day|MJ/m²)', result['snippet'])
                if numbers:
                    for value, unit in numbers:
                        data.append({
                            "value": float(value),
                            "unit": unit,
                            "source": result['title'],
                            "description": result['snippet'],
                            "location": {"latitude": lat, "longitude": lon}
                        })
            
            # Store the scraped data in vector store
            if data:
                await self.vector_store.store_data("solar", data)
            
            return {
                "data": data,
                "source": "web_scraping",
                "location": {"latitude": lat, "longitude": lon}
            }
        except Exception as e:
            logging.error(f"Error processing solar web data: {str(e)}")
            return None

    @staticmethod
    async def fetch_wind_data(query_params):
        """Fetch wind data from public sources"""
        try:
            # First, try to get similar data from vector store
            country = query_params.get("country", "global")
            similar_data = await self.vector_store.query_data(
                "wind",
                f"wind power generation statistics {country}",
                n_results=5
            )
            
            if similar_data:
                logging.info("Found relevant wind data in vector store")
                return {
                    "data": [item["data"] for item in similar_data],
                    "source": "vector_store"
                }
            
            # If no relevant data found, scrape from web
            query = f"wind power generation statistics {country} current data"
            
            results = await WebDataSource.search_web(query)
            if not results:
                return None
            
            # Process search results
            data = []
            for result in results:
                # Extract numerical data from snippets
                import re
                numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(GW|MW|TWh|GWh|MWh)', result['snippet'])
                if numbers:
                    for value, unit in numbers:
                        data.append({
                            "value": float(value),
                            "unit": unit,
                            "source": result['title'],
                            "description": result['snippet'],
                            "region": country
                        })
            
            # Store the scraped data in vector store
            if data:
                await self.vector_store.store_data("wind", data)
            
            return {
                "data": data,
                "source": "web_scraping",
                "region": country
            }
        except Exception as e:
            logging.error(f"Error processing wind web data: {str(e)}")
            return None

class DataSource:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.web_source = WebDataSource()

    async def fetch_data(self, query_params):
        """Base method to be implemented by specific data sources"""
        raise NotImplementedError

class OpenEnergyData(DataSource):
    """Integration with Open Energy Data Initiative API"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.eia.gov/v2"
        self.api_key = os.getenv("EIA_API_KEY")
        if not self.api_key:
            logging.warning("EIA_API_KEY not found in environment variables. Will try web scraping, then fall back to mock data.")

    async def fetch_data(self, query_params):
        try:
            if not self.api_key:
                # Try web scraping first
                web_data = await WebDataSource.fetch_eia_data(query_params)
                if web_data:
                    logging.info("Successfully fetched EIA data from web scraping")
                    return web_data
                
                logging.info("Web scraping failed, using mock data for EIA")
                return self._generate_mock_data(query_params)

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
            # Try web scraping as fallback
            web_data = await WebDataSource.fetch_eia_data(query_params)
            if web_data:
                logging.info("Successfully fetched EIA data from web scraping")
                return web_data
            
            logging.info("Web scraping failed, falling back to mock data for EIA")
            return self._generate_mock_data(query_params)

    def _generate_mock_data(self, query_params):
        """Generate mock data for EIA"""
        start_date = pd.to_datetime(query_params.get("start_date"))
        end_date = pd.to_datetime(query_params.get("end_date"))
        dates = pd.date_range(start=start_date, end=end_date, freq='M')
        
        return {
            "data": [
                {
                    "period": d.strftime("%Y-%m"),
                    "generation": np.random.normal(1000, 100),
                    "fuel": fuel
                }
                for d in dates
                for fuel in ["SUN", "WND", "HYC"]
            ]
        }

class SolarGIS(DataSource):
    """Integration with SolarGIS API for solar resource data"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.solargis.com/v2"
        self.api_key = os.getenv("SOLARGIS_API_KEY")
        if not self.api_key:
            logging.warning("SOLARGIS_API_KEY not found in environment variables. Will try web scraping, then fall back to mock data.")

    async def fetch_data(self, query_params):
        try:
            if not self.api_key:
                # Try web scraping first
                web_data = await WebDataSource.fetch_solar_data(query_params)
                if web_data:
                    logging.info("Successfully fetched solar data from web scraping")
                    return web_data
                
                logging.info("Web scraping failed, using mock data for SolarGIS")
                return self._generate_mock_data(query_params)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            endpoint = f"{self.base_url}/solardata"
            params = {
                "latitude": query_params.get("latitude", 40.7128),  # Default to NYC
                "longitude": query_params.get("longitude", -74.0060),
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
            # Try web scraping as fallback
            web_data = await WebDataSource.fetch_solar_data(query_params)
            if web_data:
                logging.info("Successfully fetched solar data from web scraping")
                return web_data
            
            logging.info("Web scraping failed, falling back to mock data for SolarGIS")
            return self._generate_mock_data(query_params)

    def _generate_mock_data(self, query_params):
        """Generate mock data for SolarGIS"""
        start_date = pd.to_datetime(query_params.get("start_date"))
        end_date = pd.to_datetime(query_params.get("end_date"))
        dates = pd.date_range(start=start_date, end=end_date, freq='H')
        
        return {
            "current_generation": np.random.normal(800, 50),
            "capacity": 1000,
            "data": [
                {
                    "timestamp": d.isoformat(),
                    "ghi": np.random.normal(500, 50),
                    "dni": np.random.normal(700, 70),
                    "temp": np.random.normal(25, 5),
                    "pvout": np.random.normal(400, 40)
                }
                for d in dates
            ]
        }

class WindEurope(DataSource):
    """Integration with WindEurope API for wind energy data"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.windeurope.org/v1"
        self.api_key = os.getenv("WINDEUROPE_API_KEY")
        if not self.api_key:
            logging.warning("WINDEUROPE_API_KEY not found in environment variables. Will try web scraping, then fall back to mock data.")

    async def fetch_data(self, query_params):
        try:
            if not self.api_key:
                # Try web scraping first
                web_data = await WebDataSource.fetch_wind_data(query_params)
                if web_data:
                    logging.info("Successfully fetched wind data from web scraping")
                    return web_data
                
                logging.info("Web scraping failed, using mock data for WindEurope")
                return self._generate_mock_data(query_params)

            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
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
            # Try web scraping as fallback
            web_data = await WebDataSource.fetch_wind_data(query_params)
            if web_data:
                logging.info("Successfully fetched wind data from web scraping")
                return web_data
            
            logging.info("Web scraping failed, falling back to mock data for WindEurope")
            return self._generate_mock_data(query_params)

    def _generate_mock_data(self, query_params):
        """Generate mock data for WindEurope"""
        start_date = pd.to_datetime(query_params.get("start_date"))
        end_date = pd.to_datetime(query_params.get("end_date"))
        dates = pd.date_range(start=start_date, end=end_date, freq='H')
        
        return {
            "data": [
                {
                    "timestamp": d.isoformat(),
                    "generation": np.random.normal(600, 60),
                    "capacity": 800,
                    "wind_speed": np.random.normal(8, 2),
                    "direction": np.random.randint(0, 360)
                }
                for d in dates
            ]
        }

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