# Renewable Energy Consultant

An AI-powered renewable energy consultant with dashboard creation capabilities.

## Features

- Interactive chat interface for renewable energy consulting
- Automatic dashboard creation based on user queries
- Support for various renewable energy types (solar, wind, biogas, etc.)
- ROI calculations for renewable energy projects
- Data visualization and analysis
- Vector database for enhanced question answering

## Architecture

The application consists of two main components:

1. **Flask Web Application**: Provides the user interface and handles user interactions
2. **MCP Server**: Handles AI processing and tool execution

## Prerequisites

- Docker and Docker Compose
- GroQ API key (or other OpenAI-compatible API)

## Running with Docker

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/renewable-energy-consultant.git
cd renewable-energy-consultant
```

### 2. Set up environment variables

Create a `.env` file in the root directory with your API keys:

```
OPENAI_API_KEY=your_groq_api_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=mixtral-8x7b-32768
```

### 3. Build and run with Docker Compose

```bash
docker-compose up --build
```

This will start both the Flask web application and the MCP server.

### 4. Access the application

Open your browser and navigate to:

```
http://localhost:5000
```

## Development Setup

If you want to run the application locally for development:

### 1. Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install dependencies

```bash
poetry install
```

### 3. Update the `.env` file

Make sure your `.env` file has the correct configuration:

```
# LLM Provider Configuration
OPENAI_API_KEY=your_groq_api_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=mixtral-8x7b-32768

# MCP Server Configuration
MCP_SERVER_URL=http://localhost:5002
MCP_SERVER_SCRIPT_PATH=/path/to/mcp_server/server.py
MCP_CLIENT_ID=renewable_energy_app
MCP_CLIENT_SECRET=mcp_secret_2024_renewable_energy_consultant_secure

# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True
```

### 4. Run the MCP server

```bash
python mcp_server/server.py
```

### 5. Run the Flask application

```bash
python app.py
```

## Usage

1. Open the web interface
2. Ask questions about renewable energy
3. Request dashboards for specific energy types
4. Analyze ROI for renewable energy projects

## Examples

- "Create a dashboard for a solar farm in California"
- "What's the ROI for a wind farm with an initial investment of $2M?"
- "Compare efficiency between solar and wind energy"
- "Generate a report on biogas production from agricultural waste"

## License

MIT 