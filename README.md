# Renewable Energy Consultant

A comprehensive application for renewable energy analysis and monitoring, featuring real-time data integration, interactive dashboards, and AI-powered insights.

## Features

- Real-time renewable energy data monitoring
- Interactive dashboards with multiple visualization types
- AI-powered analysis and recommendations
- Public dashboard sharing
- User authentication and management
- Auto-refresh capabilities
- Support for multiple data sources (EIA, SolarGIS, WindEurope)

## Docker Deployment

### Prerequisites

- Docker
- Docker Compose
- API keys for the following services:
  - OpenAI/GroQ/Claude (at least one)
  - EIA
  - SolarGIS
  - WindEurope

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/Pratye/Renew-AI-Agent.git
   cd Renew-AI-Agent
   ```

2. Create your environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file with your API keys and configuration:
   ```bash
   nano .env
   ```

4. Build and start the services:
   ```bash
   docker-compose up -d
   ```

The application will be available at `http://localhost:5001`

### Docker Commands

- Start the services:
  ```bash
  docker-compose up -d
  ```

- View logs:
  ```bash
  docker-compose logs -f
  ```

- Stop the services:
  ```bash
  docker-compose down
  ```

- Rebuild and restart services:
  ```bash
  docker-compose up -d --build
  ```

- Remove all containers and volumes:
  ```bash
  docker-compose down -v
  ```

### Environment Variables

Required environment variables in `.env`:

- `JWT_SECRET_KEY`: Secret key for JWT token generation
- `OPENAI_API_KEY`: OpenAI API key (optional if using GroQ or Claude)
- `GROQ_API_KEY`: GroQ API key (optional if using OpenAI or Claude)
- `CLAUDE_API_KEY`: Claude API key (optional if using OpenAI or GroQ)
- `EIA_API_KEY`: EIA API key for energy data
- `SOLARGIS_API_KEY`: SolarGIS API key for solar data
- `WINDEUROPE_API_KEY`: WindEurope API key for wind data

### Persistence

- MongoDB data is persisted in a Docker volume named `mongodb_data`
- Application code is mounted as a volume for development purposes

### Security Notes

- Never commit your `.env` file
- Use strong passwords for MongoDB in production
- Consider using Docker secrets for sensitive data in production
- Restrict MongoDB access in production environments

## Development

To run the application in development mode:

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r mcp_server/requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run the application:
   ```bash
   python -m flask run --host=0.0.0.0 --port=5001
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[MIT License](LICENSE) 