import anthropic
import os
import logging

class ClaudeAPI:
    def __init__(self, api_key=None):
        """
        Initialize the Claude API client.
        
        Args:
            api_key (str, optional): The API key for Claude. Defaults to None.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Claude API key is required")
        
        try:
            # Initialize the client with minimal parameters
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.model = "claude-3-opus-20240229"  # Using the latest Claude model
            logging.info("Claude API client initialized")
        except Exception as e:
            logging.error(f"Error initializing Claude API: {str(e)}")
            raise
    
    def generate_response(self, system_prompt, conversation_history, max_tokens=1000):
        """
        Generate a response using the Claude API.
        
        Args:
            system_prompt (str): The system prompt to guide Claude's behavior
            conversation_history (list): List of conversation messages
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 1000.
            
        Returns:
            str: The generated response
        """
        try:
            # Format the conversation history for Claude
            messages = []
            
            # Add the system prompt
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
            # Add the conversation history
            for message in conversation_history:
                if message["role"] in ["user", "assistant"]:
                    messages.append({
                        "role": message["role"],
                        "content": message["content"]
                    })
            
            # Generate the response
            response = self.client.messages.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens
            )
            
            return response.content[0].text
        
        except Exception as e:
            logging.error(f"Error generating response from Claude: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    def analyze_data(self, data, query, max_tokens=2000):
        """
        Analyze data using Claude.
        
        Args:
            data (dict): The data to analyze
            query (str): The user's query about the data
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 2000.
            
        Returns:
            str: The analysis result
        """
        try:
            prompt = f"""
            You are a Renewable Energy Consultant analyzing data. Please analyze the following data 
            and answer the query.
            
            DATA:
            {data}
            
            QUERY:
            {query}
            
            Provide a detailed analysis with insights and recommendations based on the data.
            """
            
            response = self.client.messages.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analyst specializing in renewable energy."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens
            )
            
            return response.content[0].text
        
        except Exception as e:
            logging.error(f"Error analyzing data with Claude: {str(e)}")
            raise Exception(f"Failed to analyze data: {str(e)}") 