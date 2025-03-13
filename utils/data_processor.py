import pandas as pd
import numpy as np
import json
import logging
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
import uuid

class DataProcessor:
    def __init__(self):
        """
        Initialize the data processor.
        """
        # Create the data directory if it doesn't exist
        os.makedirs("data/visualizations", exist_ok=True)
        os.makedirs("data/reports", exist_ok=True)
        
        logging.info("Data processor initialized")
    
    def process(self, data):
        """
        Process the data.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The processed data
        """
        try:
            # Check if the data is already in the correct format
            if isinstance(data, dict) and "data" in data:
                processed_data = data
            else:
                # Convert the data to a dictionary
                processed_data = {"data": data}
            
            # Add metadata
            processed_data["metadata"] = {
                "processed_at": datetime.now().isoformat(),
                "processor_version": "1.0.0"
            }
            
            return processed_data
        
        except Exception as e:
            logging.error(f"Error processing data: {str(e)}")
            raise Exception(f"Failed to process data: {str(e)}")
    
    def convert_to_dataframe(self, data):
        """
        Convert the data to a pandas DataFrame.
        
        Args:
            data (dict): The data to convert
            
        Returns:
            pandas.DataFrame: The converted data
        """
        try:
            # Check if the data contains a 'data' key
            if isinstance(data, dict) and "data" in data:
                data_to_convert = data["data"]
            else:
                data_to_convert = data
            
            # Check if the data is a list of dictionaries
            if isinstance(data_to_convert, list) and all(isinstance(item, dict) for item in data_to_convert):
                return pd.DataFrame(data_to_convert)
            
            # Check if the data is a dictionary of lists
            elif isinstance(data_to_convert, dict) and all(isinstance(item, list) for item in data_to_convert.values()):
                return pd.DataFrame(data_to_convert)
            
            # Check if the data is a dictionary of dictionaries
            elif isinstance(data_to_convert, dict) and all(isinstance(item, dict) for item in data_to_convert.values()):
                # Convert to a list of dictionaries
                data_list = []
                for key, value in data_to_convert.items():
                    value["id"] = key
                    data_list.append(value)
                
                return pd.DataFrame(data_list)
            
            else:
                raise ValueError("Data format not supported for conversion to DataFrame")
        
        except Exception as e:
            logging.error(f"Error converting data to DataFrame: {str(e)}")
            raise Exception(f"Failed to convert data to DataFrame: {str(e)}")
    
    def generate_visualization(self, data, visualization_type="auto"):
        """
        Generate a visualization based on the data.
        
        Args:
            data (dict): The data to visualize
            visualization_type (str, optional): The type of visualization to generate. Defaults to "auto".
            
        Returns:
            str: The URL of the generated visualization
        """
        try:
            # Convert the data to a DataFrame
            df = self.convert_to_dataframe(data)
            
            # Generate a unique ID for the visualization
            viz_id = str(uuid.uuid4())
            
            # Determine the visualization type if set to auto
            if visualization_type == "auto":
                # Check the number of columns
                if len(df.columns) == 2:
                    # Check if one column is numeric and the other is categorical
                    if df.dtypes.iloc[0] in ["int64", "float64"] and df.dtypes.iloc[1] not in ["int64", "float64"]:
                        visualization_type = "bar"
                    elif df.dtypes.iloc[1] in ["int64", "float64"] and df.dtypes.iloc[0] not in ["int64", "float64"]:
                        visualization_type = "bar"
                    else:
                        visualization_type = "scatter"
                
                # Check if there's a time column
                elif any(col.lower() in ["date", "time", "year", "month", "day"] for col in df.columns):
                    time_col = next(col for col in df.columns if col.lower() in ["date", "time", "year", "month", "day"])
                    numeric_cols = [col for col in df.columns if df[col].dtype in ["int64", "float64"]]
                    
                    if numeric_cols:
                        visualization_type = "line"
                    else:
                        visualization_type = "table"
                
                # Default to a table for complex data
                else:
                    visualization_type = "table"
            
            # Generate the visualization
            fig = None
            
            if visualization_type == "bar":
                # Identify categorical and numeric columns
                categorical_cols = [col for col in df.columns if df[col].dtype not in ["int64", "float64"]]
                numeric_cols = [col for col in df.columns if df[col].dtype in ["int64", "float64"]]
                
                if categorical_cols and numeric_cols:
                    fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0], title="Renewable Energy Data")
            
            elif visualization_type == "line":
                # Identify time and numeric columns
                time_col = next((col for col in df.columns if col.lower() in ["date", "time", "year", "month", "day"]), None)
                numeric_cols = [col for col in df.columns if df[col].dtype in ["int64", "float64"]]
                
                if time_col and numeric_cols:
                    fig = px.line(df, x=time_col, y=numeric_cols, title="Renewable Energy Trends")
            
            elif visualization_type == "scatter":
                # Identify numeric columns
                numeric_cols = [col for col in df.columns if df[col].dtype in ["int64", "float64"]]
                
                if len(numeric_cols) >= 2:
                    fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], title="Renewable Energy Correlation")
            
            elif visualization_type == "pie":
                # Identify categorical and numeric columns
                categorical_cols = [col for col in df.columns if df[col].dtype not in ["int64", "float64"]]
                numeric_cols = [col for col in df.columns if df[col].dtype in ["int64", "float64"]]
                
                if categorical_cols and numeric_cols:
                    fig = px.pie(df, names=categorical_cols[0], values=numeric_cols[0], title="Renewable Energy Distribution")
            
            elif visualization_type == "table":
                fig = go.Figure(data=[go.Table(
                    header=dict(values=list(df.columns),
                                fill_color='paleturquoise',
                                align='left'),
                    cells=dict(values=[df[col] for col in df.columns],
                               fill_color='lavender',
                               align='left'))
                ])
                fig.update_layout(title="Renewable Energy Data Table")
            
            # Save the visualization
            if fig:
                # Create a unique filename
                filename = f"data/visualizations/{viz_id}.html"
                
                # Save the figure as an HTML file
                fig.write_html(filename)
                
                # Return the URL of the visualization
                return f"/visualizations/{viz_id}.html"
            else:
                raise ValueError(f"Failed to generate visualization of type {visualization_type}")
        
        except Exception as e:
            logging.error(f"Error generating visualization: {str(e)}")
            raise Exception(f"Failed to generate visualization: {str(e)}") 