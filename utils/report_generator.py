import os
import json
import logging
from datetime import datetime
import uuid
import pandas as pd
from jinja2 import Template
import plotly.express as px
import plotly.graph_objects as go
from api.claude_api import ClaudeAPI
from api.openai_api import OpenAIAPI

class ReportGenerator:
    def __init__(self):
        """
        Initialize the report generator.
        """
        # Create the reports directory if it doesn't exist
        os.makedirs("data/reports", exist_ok=True)
        os.makedirs("data/visualizations", exist_ok=True)
        
        # Initialize API clients
        self.claude_api = None
        self.openai_api = None
        
        # Try to initialize Claude API
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_api_key and anthropic_api_key != "your-anthropic-api-key" and anthropic_api_key != "your-claude-api-key-here":
            try:
                self.claude_api = ClaudeAPI(api_key=anthropic_api_key)
                logging.info("Claude API initialized successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize Claude API: {str(e)}")
        
        # Try to initialize OpenAI API
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            try:
                self.openai_api = OpenAIAPI(api_key=openai_api_key)
                logging.info("OpenAI API initialized successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize OpenAI API: {str(e)}")
        
        if not self.claude_api and not self.openai_api:
            logging.warning("No LLM APIs available. Report generation will be limited.")
        
        logging.info("Report generator initialized")
    
    def generate_report(self, data, query, format="html"):
        """
        Generate a report based on the data and query.
        
        Args:
            data (dict): The data to include in the report
            query (str): The user's query that prompted the report
            format (str, optional): The format of the report. Defaults to "html".
            
        Returns:
            str: The URL of the generated report
        """
        try:
            # Generate a unique ID for the report
            report_id = str(uuid.uuid4())
            
            # Generate the report content using AI
            report_content = self._generate_report_content(data, query)
            
            # Generate visualizations for the report
            visualizations = self._generate_report_visualizations(data)
            
            # Create the report based on the format
            if format.lower() == "html":
                report_url = self._generate_html_report(report_id, report_content, visualizations, data, query)
            elif format.lower() == "pdf":
                report_url = self._generate_pdf_report(report_id, report_content, visualizations, data, query)
            elif format.lower() == "json":
                report_url = self._generate_json_report(report_id, report_content, visualizations, data, query)
            else:
                raise ValueError(f"Unsupported report format: {format}")
            
            return report_url
        
        except Exception as e:
            logging.error(f"Error generating report: {str(e)}")
            raise Exception(f"Failed to generate report: {str(e)}")
    
    def _generate_report_content(self, data, query):
        """
        Generate the content for the report using AI.
        
        Args:
            data (dict): The data to include in the report
            query (str): The user's query that prompted the report
            
        Returns:
            dict: The generated report content
        """
        try:
            # Prepare the prompt for the AI
            prompt = f"""
            You are a Renewable Energy Consultant generating a report. Please analyze the following data 
            and create a comprehensive report that addresses the query.
            
            DATA:
            {json.dumps(data, indent=2)}
            
            QUERY:
            {query}
            
            Generate a report with the following sections:
            1. Executive Summary
            2. Introduction
            3. Data Analysis
            4. Key Findings
            5. Recommendations
            6. Conclusion
            
            Format your response as a JSON object with the following structure:
            {{
                "title": "Report title",
                "sections": [
                    {{
                        "title": "Executive Summary",
                        "content": "Content of the executive summary"
                    }},
                    ...
                ]
            }}
            """
            
            response = None
            
            # Try to generate the report content using Claude if available
            if self.claude_api:
                try:
                    response = self.claude_api.analyze_data(data, prompt)
                except Exception as e:
                    logging.warning(f"Error generating report with Claude: {str(e)}. Falling back to OpenAI.")
            
            # Fall back to OpenAI if Claude is not available or failed
            if not response and self.openai_api:
                try:
                    response = self.openai_api.analyze_data(data, prompt)
                except Exception as e:
                    logging.warning(f"Error generating report with OpenAI: {str(e)}")
            
            # If both APIs failed or are not available, generate a simple report
            if not response:
                logging.warning("No LLM APIs available for report generation. Creating a simple report.")
                return self._generate_simple_report(data, query)
            
            # Parse the response as JSON
            try:
                report_content = json.loads(response)
            except json.JSONDecodeError:
                # If the response is not valid JSON, extract the JSON part
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    report_content = json.loads(json_str)
                else:
                    # If we can't extract JSON, create a simple structure
                    report_content = self._generate_simple_report(data, query, response)
            
            return report_content
        
        except Exception as e:
            logging.error(f"Error generating report content: {str(e)}")
            return self._generate_simple_report(data, query)
    
    def _generate_simple_report(self, data, query, content=None):
        """
        Generate a simple report without using AI.
        
        Args:
            data (dict): The data to include in the report
            query (str): The user's query that prompted the report
            content (str, optional): Additional content to include. Defaults to None.
            
        Returns:
            dict: The generated report content
        """
        # Extract energy type from data or query
        energy_type = "Renewable Energy"
        if isinstance(data, dict) and "energy_type" in data:
            energy_type = data["energy_type"].capitalize()
        elif "solar" in query.lower():
            energy_type = "Solar Energy"
        elif "wind" in query.lower():
            energy_type = "Wind Energy"
        elif "biogas" in query.lower() or "cbg" in query.lower():
            energy_type = "Biogas Energy"
        
        # Create a simple report structure
        report = {
            "title": f"{energy_type} Analysis Report",
            "sections": [
                {
                    "title": "Executive Summary",
                    "content": f"This report provides an analysis of {energy_type.lower()} data based on the query: '{query}'."
                },
                {
                    "title": "Introduction",
                    "content": f"This report was generated to address the following query: '{query}'. It contains an analysis of {energy_type.lower()} data and provides insights and recommendations."
                },
                {
                    "title": "Data Analysis",
                    "content": "The data has been analyzed to identify key patterns and trends."
                }
            ]
        }
        
        # Add the data summary section
        if isinstance(data, dict):
            summary = "Key data points:\n"
            for key, value in data.items():
                if not isinstance(value, (dict, list)):
                    summary += f"- {key}: {value}\n"
            
            report["sections"].append({
                "title": "Data Summary",
                "content": summary
            })
        
        # Add the provided content if available
        if content:
            report["sections"].append({
                "title": "Additional Information",
                "content": content
            })
        
        # Add conclusions
        report["sections"].append({
            "title": "Conclusion",
            "content": f"Based on the analysis of the {energy_type.lower()} data, we recommend further monitoring and analysis to optimize performance and efficiency."
        })
        
        return report
    
    def _generate_report_visualizations(self, data):
        """
        Generate visualizations for the report.
        
        Args:
            data (dict): The data to visualize
            
        Returns:
            list: The generated visualizations
        """
        try:
            visualizations = []
            
            # Convert the data to a DataFrame
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
            
            # Generate visualizations based on the data types
            
            # Check for numeric columns
            numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
            
            # Check for categorical columns
            categorical_cols = [col for col in df.columns if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col])]
            
            # Check for datetime columns
            datetime_cols = [col for col in df.columns if pd.api.types.is_datetime64_dtype(df[col])]
            
            # Generate a bar chart if we have categorical and numeric columns
            if categorical_cols and numeric_cols:
                viz_id = str(uuid.uuid4())
                filename = f"data/visualizations/{viz_id}.html"
                
                fig = px.bar(df, x=categorical_cols[0], y=numeric_cols[0], title=f"{numeric_cols[0]} by {categorical_cols[0]}")
                fig.write_html(filename)
                
                visualizations.append({
                    "title": f"{numeric_cols[0]} by {categorical_cols[0]}",
                    "type": "bar",
                    "url": f"/visualizations/{viz_id}.html"
                })
            
            # Generate a line chart if we have datetime and numeric columns
            if datetime_cols and numeric_cols:
                viz_id = str(uuid.uuid4())
                filename = f"data/visualizations/{viz_id}.html"
                
                fig = px.line(df, x=datetime_cols[0], y=numeric_cols, title=f"{', '.join(numeric_cols)} over Time")
                fig.write_html(filename)
                
                visualizations.append({
                    "title": f"{', '.join(numeric_cols)} over Time",
                    "type": "line",
                    "url": f"/visualizations/{viz_id}.html"
                })
            
            # Generate a pie chart for distribution of a categorical column
            if categorical_cols and len(df[categorical_cols[0]].unique()) <= 10:
                viz_id = str(uuid.uuid4())
                filename = f"data/visualizations/{viz_id}.html"
                
                value_counts = df[categorical_cols[0]].value_counts()
                fig = px.pie(names=value_counts.index, values=value_counts.values, title=f"Distribution of {categorical_cols[0]}")
                fig.write_html(filename)
                
                visualizations.append({
                    "title": f"Distribution of {categorical_cols[0]}",
                    "type": "pie",
                    "url": f"/visualizations/{viz_id}.html"
                })
            
            # Generate a scatter plot if we have at least 2 numeric columns
            if len(numeric_cols) >= 2:
                viz_id = str(uuid.uuid4())
                filename = f"data/visualizations/{viz_id}.html"
                
                fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], title=f"{numeric_cols[1]} vs {numeric_cols[0]}")
                fig.write_html(filename)
                
                visualizations.append({
                    "title": f"{numeric_cols[1]} vs {numeric_cols[0]}",
                    "type": "scatter",
                    "url": f"/visualizations/{viz_id}.html"
                })
            
            return visualizations
        
        except Exception as e:
            logging.error(f"Error generating report visualizations: {str(e)}")
            return []
    
    def _generate_html_report(self, report_id, report_content, visualizations, data, query):
        """
        Generate an HTML report.
        
        Args:
            report_id (str): The unique ID for the report
            report_content (dict): The content of the report
            visualizations (list): The visualizations to include in the report
            data (dict): The data used to generate the report
            query (str): The user's query that prompted the report
            
        Returns:
            str: The URL of the generated report
        """
        try:
            # Define the HTML template
            template_str = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{{ report_content.title }}</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    h1 {
                        color: #2c3e50;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                    }
                    h2 {
                        color: #2980b9;
                        margin-top: 30px;
                    }
                    .visualization {
                        margin: 30px 0;
                        text-align: center;
                    }
                    .visualization iframe {
                        width: 100%;
                        height: 500px;
                        border: none;
                    }
                    .metadata {
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 5px;
                        margin-top: 40px;
                        font-size: 0.9em;
                    }
                    .executive-summary {
                        background-color: #e8f4f8;
                        padding: 20px;
                        border-radius: 5px;
                        margin: 20px 0;
                    }
                </style>
            </head>
            <body>
                <h1>{{ report_content.title }}</h1>
                
                <div class="metadata">
                    <p><strong>Generated:</strong> {{ timestamp }}</p>
                    <p><strong>Query:</strong> {{ query }}</p>
                    <p><strong>Report ID:</strong> {{ report_id }}</p>
                </div>
                
                {% for section in report_content.sections %}
                    <h2>{{ section.title }}</h2>
                    {% if section.title == "Executive Summary" %}
                        <div class="executive-summary">
                            {{ section.content | safe }}
                        </div>
                    {% else %}
                        <div>
                            {{ section.content | safe }}
                        </div>
                    {% endif %}
                    
                    {% if section.title == "Data Analysis" or section.title == "Key Findings" %}
                        {% for viz in visualizations %}
                            <div class="visualization">
                                <h3>{{ viz.title }}</h3>
                                <iframe src="{{ viz.url }}"></iframe>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endfor %}
            </body>
            </html>
            """
            
            # Create a Jinja2 template
            template = Template(template_str)
            
            # Render the template
            html = template.render(
                report_content=report_content,
                visualizations=visualizations,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                query=query,
                report_id=report_id
            )
            
            # Save the HTML report
            filename = f"data/reports/{report_id}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            
            return f"/reports/{report_id}.html"
        
        except Exception as e:
            logging.error(f"Error generating HTML report: {str(e)}")
            raise Exception(f"Failed to generate HTML report: {str(e)}")
    
    def _generate_pdf_report(self, report_id, report_content, visualizations, data, query):
        """
        Generate a PDF report.
        
        Args:
            report_id (str): The unique ID for the report
            report_content (dict): The content of the report
            visualizations (list): The visualizations to include in the report
            data (dict): The data used to generate the report
            query (str): The user's query that prompted the report
            
        Returns:
            str: The URL of the generated report
        """
        # For simplicity, we'll generate an HTML report and note that it should be converted to PDF
        # In a real implementation, you would use a library like WeasyPrint or pdfkit to convert HTML to PDF
        
        html_url = self._generate_html_report(report_id, report_content, visualizations, data, query)
        logging.warning("PDF generation not implemented. Generated HTML report instead.")
        
        return html_url
    
    def _generate_json_report(self, report_id, report_content, visualizations, data, query):
        """
        Generate a JSON report.
        
        Args:
            report_id (str): The unique ID for the report
            report_content (dict): The content of the report
            visualizations (list): The visualizations to include in the report
            data (dict): The data used to generate the report
            query (str): The user's query that prompted the report
            
        Returns:
            str: The URL of the generated report
        """
        try:
            # Create the JSON report
            json_report = {
                "report_id": report_id,
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "content": report_content,
                "visualizations": visualizations,
                "data": data
            }
            
            # Save the JSON report
            filename = f"data/reports/{report_id}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(json_report, f, indent=2)
            
            return f"/reports/{report_id}.json"
        
        except Exception as e:
            logging.error(f"Error generating JSON report: {str(e)}")
            raise Exception(f"Failed to generate JSON report: {str(e)}")