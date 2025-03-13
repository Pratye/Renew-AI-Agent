from typing import Dict, Any, List
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class DashboardFactory:
    """Factory class for creating different types of dashboards"""
    
    @staticmethod
    def create_dashboard(dashboard_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a dashboard based on type"""
        if dashboard_type == 'cbg':
            return CBGDashboard.generate_layout(data)
        elif dashboard_type == 'solar_farm':
            return SolarFarmDashboard.generate_layout(data)
        elif dashboard_type == 'wind_farm':
            return WindFarmDashboard.generate_layout(data)
        elif dashboard_type == 'hybrid_plant':
            return HybridPlantDashboard.generate_layout(data)
        else:
            raise ValueError(f"Unsupported dashboard type: {dashboard_type}")

class DashboardBase:
    """Base class for dashboard templates"""
    
    @staticmethod
    def create_summary_stats(data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary statistics widget"""
        return {
            'type': 'summary_stats',
            'data': {
                'total_generation': data.get('total_generation', 0),
                'average_generation': data.get('average_generation', 0),
                'peak_generation': data.get('peak_generation', 0),
                'carbon_offset': data.get('carbon_offset', 0)
            }
        }
    
    @staticmethod
    def create_generation_chart(data: Dict[str, Any]) -> Dict[str, Any]:
        """Create generation time series chart"""
        return {
            'type': 'line_chart',
            'data': {
                'x': data.get('timestamps', []),
                'y': data.get('generation_values', []),
                'title': 'Generation Over Time'
            }
        }
    
    @staticmethod
    def create_forecast_widget(data: Dict[str, Any]) -> Dict[str, Any]:
        """Create forecast widget"""
        return {
            'type': 'forecast',
            'data': {
                'short_term': data.get('short_term_forecast', []),
                'long_term': data.get('long_term_forecast', []),
                'confidence_intervals': data.get('forecast_confidence', [])
            }
        }

class CBGDashboard(DashboardBase):
    """Community Based Generation Dashboard"""
    
    @staticmethod
    def generate_layout(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate layout for CBG dashboard"""
        layout = {
            'grid': {
                'rows': 3,
                'cols': 4,
                'gap': '1rem',
                'widgets': []
            }
        }
        
        # Summary statistics widget (top left)
        layout['grid']['widgets'].append({
            'type': 'summary_stats',
            'position': {'row': 1, 'col': 1, 'width': 1, 'height': 1},
            'data': CBGDashboard.create_summary_stats(data)
        })
        
        # Real-time generation gauge (top center)
        layout['grid']['widgets'].append({
            'type': 'gauge',
            'position': {'row': 1, 'col': 2, 'width': 1, 'height': 1},
            'data': {
                'value': data.get('current_generation', 0),
                'max': data.get('capacity', 100),
                'title': 'Current Generation'
            }
        })
        
        # Generation vs Consumption (top right)
        layout['grid']['widgets'].append({
            'type': 'line_chart',
            'position': {'row': 1, 'col': 3, 'width': 2, 'height': 1},
            'data': {
                'series': [
                    {'name': 'Generation', 'values': data.get('generation_values', [])},
                    {'name': 'Consumption', 'values': data.get('consumption_values', [])}
                ],
                'title': 'Generation vs Consumption'
            }
        })
        
        # Community participation map (middle left)
        layout['grid']['widgets'].append({
            'type': 'map',
            'position': {'row': 2, 'col': 1, 'width': 2, 'height': 1},
            'data': {
                'locations': data.get('participant_locations', []),
                'values': data.get('participant_generation', []),
                'title': 'Community Participation'
            }
        })
        
        # Financial benefits (middle right)
        layout['grid']['widgets'].append({
            'type': 'bar_chart',
            'position': {'row': 2, 'col': 3, 'width': 2, 'height': 1},
            'data': {
                'categories': data.get('benefit_categories', []),
                'values': data.get('benefit_values', []),
                'title': 'Financial Benefits'
            }
        })
        
        # Environmental impact (bottom left)
        layout['grid']['widgets'].append({
            'type': 'donut_chart',
            'position': {'row': 3, 'col': 1, 'width': 2, 'height': 1},
            'data': {
                'labels': ['CO2 Avoided', 'Trees Saved', 'Water Conserved'],
                'values': [
                    data.get('co2_avoided', 0),
                    data.get('trees_equivalent', 0),
                    data.get('water_saved', 0)
                ],
                'title': 'Environmental Impact'
            }
        })
        
        # Forecast and recommendations (bottom right)
        layout['grid']['widgets'].append({
            'type': 'forecast',
            'position': {'row': 3, 'col': 3, 'width': 2, 'height': 1},
            'data': CBGDashboard.create_forecast_widget(data)
        })
        
        return layout

class SolarFarmDashboard(DashboardBase):
    """Solar Farm Dashboard"""
    
    @staticmethod
    def generate_layout(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate layout for solar farm dashboard"""
        layout = {
            'grid': {
                'rows': 3,
                'cols': 4,
                'gap': '1rem',
                'widgets': []
            }
        }
        
        # Add solar-specific widgets here
        # TODO: Implement solar farm specific layout
        
        return layout

class WindFarmDashboard(DashboardBase):
    """Wind Farm Dashboard"""
    
    @staticmethod
    def generate_layout(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate layout for wind farm dashboard"""
        layout = {
            'grid': {
                'rows': 3,
                'cols': 4,
                'gap': '1rem',
                'widgets': []
            }
        }
        
        # Add wind-specific widgets here
        # TODO: Implement wind farm specific layout
        
        return layout

class HybridPlantDashboard(DashboardBase):
    """Hybrid Plant Dashboard"""
    
    @staticmethod
    def generate_layout(data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate layout for hybrid plant dashboard"""
        layout = {
            'grid': {
                'rows': 3,
                'cols': 4,
                'gap': '1rem',
                'widgets': []
            }
        }
        
        # Add hybrid plant specific widgets here
        # TODO: Implement hybrid plant specific layout
        
        return layout

def process_dashboard_data(raw_data: Dict[str, Any], dashboard_type: str) -> Dict[str, Any]:
    """Process raw data for dashboard visualization"""
    processed_data = {}
    
    try:
        # Common processing for all dashboard types
        if 'generation' in raw_data:
            df = pd.DataFrame(raw_data['generation'])
            processed_data.update({
                'total_generation': df['value'].sum(),
                'average_generation': df['value'].mean(),
                'peak_generation': df['value'].max(),
                'generation_values': df['value'].tolist(),
                'timestamps': df['timestamp'].tolist()
            })
        
        # Type-specific processing
        if dashboard_type == 'cbg':
            if 'community' in raw_data:
                community_df = pd.DataFrame(raw_data['community'])
                processed_data.update({
                    'participant_locations': community_df[['latitude', 'longitude']].to_dict('records'),
                    'participant_generation': community_df['generation'].tolist(),
                    'benefit_categories': ['Cost Savings', 'Grid Credits', 'Tax Incentives'],
                    'benefit_values': [
                        community_df['cost_savings'].sum(),
                        community_df['grid_credits'].sum(),
                        community_df['tax_incentives'].sum()
                    ]
                })
        
        # Add forecast data if available
        if 'forecast' in raw_data:
            forecast_df = pd.DataFrame(raw_data['forecast'])
            processed_data.update({
                'short_term_forecast': forecast_df[forecast_df['horizon'] <= '24h']['value'].tolist(),
                'long_term_forecast': forecast_df[forecast_df['horizon'] > '24h']['value'].tolist(),
                'forecast_confidence': forecast_df['confidence'].tolist()
            })
        
        return processed_data
        
    except Exception as e:
        logging.error(f"Error processing dashboard data: {str(e)}")
        return None 