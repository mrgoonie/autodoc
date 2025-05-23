# AutoDoc AI

AutoDoc AI is an advanced tool designed to automatically generate Docusaurus documentation from GitHub repositories using AI techniques. By combining traditional code analysis with a multi-agent AI system, it creates comprehensive, well-structured, and multilingual documentation with minimal human effort.

## Features

- **GitHub Repository Access**: Clone and analyze public and private GitHub repositories (using PAT for private repos)
- **Code Analysis**: Parse and extract code structures (initially focusing on Python)
- **AI-Powered Documentation**: Use a multi-agent AI system (LangGraph) to coordinate specialized AI agents
- **RAG Integration**: Utilize Retrieval Augmented Generation with Qdrant vector database for improved content
- **Mermaid.js Diagrams**: Generate visual diagrams of code dependencies and flows
- **Multilingual Support**: Create documentation in both English and Vietnamese
- **Docusaurus Format**: Output documentation in Markdown/MDX format compatible with Docusaurus
- **Notification System**: Receive email notifications about processing status via SendGrid

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/autodocai.git
cd autodocai

# Install the package and dependencies
pip install -e .

# For development, install additional dependencies
pip install -e ".[dev]"
```

## Configuration

AutoDoc AI is configured through environment variables. Copy the `.env.example` file to `.env` and edit it with your settings:

```bash
cp .env.example .env
# Edit .env with your configuration
```

### Required Environment Variables

- `OPENROUTER_API_KEY`: Your OpenRouter API key (BYOK model)
- `QDRANT_URL`: URL for your Qdrant vector database instance
- `TARGET_REPO_URL`: GitHub repository URL to generate documentation for
- `OUTPUT_DIR`: Directory where the generated Docusaurus documentation will be saved

### Optional Environment Variables

- `GITHUB_PAT`: Personal Access Token for accessing private GitHub repositories
- `SENDGRID_API_KEY`: SendGrid API key for email notifications
- `SENDGRID_FROM_EMAIL`: Sender email address for notifications
- `NOTIFICATION_EMAIL_TO`: Recipient email address for notifications
- See `.env.example` for a complete list of configuration options

## Usage

```bash
# Basic usage with environment variables
autodocai generate

# Or specify parameters directly
autodocai generate --repo-url https://github.com/username/repo --output-dir ./docs
```

## Development

```bash
# Run tests
pytest

# Format code
black autodocai tests
isort autodocai tests

# Type checking
mypy autodocai
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- This project uses [LangGraph](https://github.com/langchain-ai/langgraph) for AI agent orchestration
- [Qdrant](https://qdrant.tech/) for vector database functionality
- [OpenRouter](https://openrouter.ai/) for flexible access to various AI models
- [Docusaurus](https://docusaurus.io/) as the target documentation platform
