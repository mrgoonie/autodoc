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
- **Modular Architecture**: Extensible agent-based architecture for easy customization

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
- `SUMMARIZER_MODEL_NAME`: Model name for summary generation (default: `openai/gpt-4-turbo`)
- `RAG_MODEL_NAME`: Model name for RAG queries (default: `openai/gpt-4-turbo`)
- `OUTPUT_LANGUAGES`: Comma-separated list of language codes for output (default: `EN,VI`)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- See `.env.example` for a complete list of configuration options

## Architecture

AutoDoc AI uses a modular agent-based architecture powered by LangGraph to orchestrate the documentation generation process:

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│                │     │                │     │                │     │                │
│  RepoClonerAgent│────▶│CodeParserAgent │────▶│SummarizerAgent │────▶│DocstringEnhancer│
│                │     │                │     │                │     │                │
└────────────────┘     └────────────────┘     └────────────────┘     └────────────────┘
                                                                               │
┌────────────────┐     ┌────────────────┐     ┌────────────────┐     ┌─────────▼──────┐
│                │     │                │     │                │     │                │
│  DocBuilder    │◀────│  DocFormatter  │◀────│TranslationAgent│◀────│  RAGQueryAgent │
│                │     │                │     │                │     │                │
└────────────────┘     └────────────────┘     └────────────────┘     └────────────────┘
        │                                                                     ▲
        │                     ┌────────────────┐                              │
        └────────────────────▶│                │──────────────────────────────┘
                              │DiagramGenerator│
                              │                │
                              └────────────────┘
```

Each agent is responsible for a specific task in the documentation generation pipeline:

1. **RepoClonerAgent**: Clones the target repository and extracts basic repository information
2. **CodeParserAgent**: Parses the code to extract modules, classes, functions, and their relationships
3. **SummarizerAgent**: Generates summaries for each code snippet
4. **DocstringEnhancerAgent**: Enhances existing docstrings or generates new ones for code without documentation
5. **RAGQueryAgent**: Uses Retrieval Augmented Generation to create architectural overviews
6. **MermaidDiagramAgent**: Generates visual diagrams of code structure and relationships
7. **TranslationAgent**: Translates documentation to supported languages
8. **DocusaurusFormatterAgent**: Formats the documentation for Docusaurus
9. **DocumentationBuilderAgent**: Builds the final Docusaurus site

## Usage

```bash
# Basic usage with environment variables
python -m autodocai.cli generate

# Or specify parameters directly
python -m autodocai.cli generate --repo-url https://github.com/username/repo --output-dir ./docs

# For debugging
python -m autodocai.cli generate --debug
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific agent tests
pytest tests/agents/

# Run with verbose output
pytest -v
```

### Code Formatting and Linting

```bash
# Format code
black autodocai tests
isort autodocai tests

# Type checking
mypy autodocai
```

### Extending the Agent System

To add a new agent to the system:

1. Create a new agent class that inherits from `BaseAgent` in `autodocai/agents/`
2. Implement the required `_execute` method
3. Update the orchestrator in `autodocai/orchestrator.py` to include your agent
4. Add tests for your agent in `tests/agents/`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- This project uses [LangGraph](https://github.com/langchain-ai/langgraph) for AI agent orchestration
- [Qdrant](https://qdrant.tech/) for vector database functionality
- [OpenRouter](https://openrouter.ai/) for flexible access to various AI models
- [Docusaurus](https://docusaurus.io/) as the target documentation platform
