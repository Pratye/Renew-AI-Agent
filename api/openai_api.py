import openai
import os
import logging

class OpenAIAPI:
    def __init__(self, api_key=None, base_url=None, model=None):
        """
        Initialize the OpenAI-compatible API client.
        
        Args:
            api_key (str, optional): The API key. Defaults to None.
            base_url (str, optional): Base URL for API (e.g., GroQ or Ollama endpoint). Defaults to None.
            model (str, optional): The model to use. Defaults to None.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required")
        
        # Get base URL from environment if not provided
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        
        # Initialize the client with minimal parameters
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        
        try:
            self.client = openai.OpenAI(**client_kwargs)
            
            # Set default model based on provider or use specified model
            self.model = model or os.getenv("OPENAI_MODEL")
            
            # If model is still not set, use defaults based on provider
            if not self.model:
                if self.base_url and "groq" in self.base_url.lower():
                    self.model = "mixtral-8x7b-32768"  # GroQ default model
                elif self.base_url and "ollama" in self.base_url.lower():
                    self.model = "llama2"  # Ollama default model
                else:
                    self.model = "gpt-4-turbo"  # OpenAI default model
            
            logging.info(f"API client initialized with model: {self.model}")
            if self.base_url:
                logging.info(f"Using custom API endpoint: {self.base_url}")
        except Exception as e:
            logging.error(f"Error initializing API client: {str(e)}")
            raise
    
    def generate_response(self, system_prompt, conversation_history, max_tokens=1000):
        """
        Generate a response using the API.
        
        Args:
            system_prompt (str): The system prompt to guide the model's behavior
            conversation_history (list): List of conversation messages
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 1000.
            
        Returns:
            str: The generated response
        """
        try:
            # Format the conversation history
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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logging.error(f"Error generating response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    def analyze_data(self, data, query, max_tokens=2000):
        """
        Analyze data using the API.
        
        Args:
            data (dict): The data to analyze
            query (str): The user's query about the data
            max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 2000.
            
        Returns:
            str: The analysis result
        """
        try:
            # Convert data to string if it's not already
            data_str = data
            if isinstance(data, (dict, list)):
                import json
                data_str = json.dumps(data, indent=2)
            
            prompt = f"""
            You are a Renewable Energy Consultant analyzing data. Please analyze the following data 
            and answer the query.
            
            DATA:
            {data_str}
            
            QUERY:
            {query}
            
            Provide a detailed analysis with insights and recommendations based on the data.
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
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analyst specializing in renewable energy."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logging.error(f"Error analyzing data: {str(e)}")
            raise Exception(f"Failed to analyze data: {str(e)}")
            
    def generate_embeddings(self, text):
        """
        Generate embeddings for text.
        
        Args:
            text (str): The text to generate embeddings for
            
        Returns:
            list: The embeddings
        """
        try:
            # Use appropriate embedding model based on provider
            embedding_model = "text-embedding-3-small"
            
            # Adjust embedding model based on provider
            if self.base_url:
                if "groq" in self.base_url.lower():
                    embedding_model = "text-embedding-ada-002"  # GroQ compatible model
                elif "ollama" in self.base_url.lower():
                    embedding_model = "llama2"  # Ollama compatible model
            
            try:
                response = self.client.embeddings.create(
                    model=embedding_model,
                    input=text
                )
                
                return response.data[0].embedding
            except Exception as embedding_error:
                # If the specific embedding model fails, try a fallback
                logging.warning(f"Error with embedding model {embedding_model}: {str(embedding_error)}. Trying fallback.")
                fallback_model = "text-embedding-ada-002"  # Most widely supported
                
                response = self.client.embeddings.create(
                    model=fallback_model,
                    input=text
                )
                
                return response.data[0].embedding
        
        except Exception as e:
            logging.error(f"Error generating embeddings: {str(e)}")
            # Return a mock embedding instead of failing
            import random
            logging.warning("Returning mock embedding due to API error")
            return [random.random() for _ in range(1536)]  # Standard embedding size 