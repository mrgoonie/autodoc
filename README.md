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

AutoDoc AI uses a modular agent-based architecture powered by LangGraph to orchestrate the documentation generation process. LangGraph provides a flexible framework for connecting AI agents together into a workflow that can handle complex document generation tasks.

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

### LangGraph Orchestration

The orchestrator uses LangGraph's `StateGraph` to connect agents into a directed graph with predefined execution order. This provides several key benefits:

1. **Declarative Workflow Definition**: The workflow is defined as a directed graph where nodes are agents and edges represent the flow of data.

2. **Robust State Management**: The system maintains a `WorkflowState` Pydantic model that captures all intermediate data and progress information.

3. **Parallel and Sequential Processing**: LangGraph supports both parallel and sequential execution patterns, allowing for optimal processing of different tasks.

4. **Persistent Progress Tracking**: The workflow state can be monitored and tracked throughout the execution process.

5. **Resilient Error Handling**: Each agent independently handles exceptions, allowing the workflow to continue even if individual steps encounter issues.

Each agent in the workflow:

1. Receives a state object with data from previous agents
2. Performs its specific task asynchronously
3. Updates the state with new information
4. Passes the state to the next agent in the workflow

The architecture also supports progress callbacks for real-time monitoring and UI updates during execution.

### Agent Responsibilities

Each agent is responsible for a specific task in the documentation generation pipeline:

1. **RepoClonerAgent**: Clones the target repository and extracts basic repository information including language statistics, repository structure, and metadata.

2. **CodeParserAgent**: Parses the code to extract modules, classes, functions, and their relationships. This agent identifies important code elements and prepares them for documentation.

3. **SummarizerAgent**: Generates concise, accurate summaries for each code snippet by analyzing code structure, purpose, and functionality.

4. **DocstringEnhancerAgent**: Enhances existing docstrings or generates new ones for code without documentation, ensuring complete and consistent API documentation.

5. **RAGQueryAgent**: Uses Retrieval Augmented Generation to create architectural overviews by querying a vector database of code knowledge to provide context-aware documentation.

6. **MermaidDiagramAgent**: Generates visual diagrams of code structure and relationships using Mermaid.js syntax for visual representation of code architecture.

7. **TranslationAgent**: Translates documentation to all supported languages while maintaining technical accuracy and consistency.

8. **DocusaurusFormatterAgent**: Formats the documentation for Docusaurus, creating a well-structured site with proper navigation, search functionality, and theme support.

9. **DocumentationBuilderAgent**: Builds the final Docusaurus site by installing dependencies and running the build process to generate a production-ready documentation site.

## Usage

AutoDoc AI provides a comprehensive command-line interface (CLI) for generating documentation and managing the tool.

### Configuration

```bash
# Show current configuration
python -m autodocai.cli configure --show

# Run interactive configuration to set up .env file
python -m autodocai.cli configure
```

### Repository Information

```bash
# Get information about a repository before generating documentation
python -m autodocai.cli info https://github.com/username/repo

# For private repositories
python -m autodocai.cli info https://github.com/username/private-repo --github-pat YOUR_PAT
```

### Generating Documentation

```bash
# Basic usage with environment variables
python -m autodocai.cli generate

# Specify parameters directly
python -m autodocai.cli generate --repo-url https://github.com/username/repo --output-dir ./docs

# Generate documentation with multiple languages
python -m autodocai.cli generate --repo-url https://github.com/username/repo --languages EN,VI,ES

# For private repositories
python -m autodocai.cli generate --repo-url https://github.com/username/private-repo --github-pat YOUR_PAT

# Disable progress display
python -m autodocai.cli generate --no-progress

# For debugging
python -m autodocai.cli generate --debug
```

#### Advanced CLI Options

The CLI offers several advanced options for customizing the documentation generation process:

| Option | Description |
| ------ | ----------- |
| `--repo-url` | GitHub repository URL to generate documentation for |
| `--output-dir` | Directory to save the generated documentation |
| `--languages` | Comma-separated list of language codes for output (e.g., 'EN,VI,ES') |
| `--github-pat` | GitHub Personal Access Token for accessing private repositories |
| `--debug` | Enable debug mode with more verbose output and error tracing |
| `--no-progress` | Disable interactive progress display (useful for CI/CD pipelines) |

#### Real-time Progress Monitoring

When running the generate command, the CLI provides real-time feedback on the documentation generation process:

- Current stage of the workflow
- Time elapsed
- Status messages from each agent
- Error reporting with detailed diagnostics

This makes it easy to monitor long-running documentation generation tasks and identify any issues that might arise during processing.

### Using as Package

You can also use AutoDoc AI programmatically in your Python code:

```python
import asyncio
from autodocai.config import AppConfig
from autodocai.orchestrator import create_workflow

async def generate_docs():
    # Create config
    config = AppConfig.from_env_and_args(repo_url="https://github.com/username/repo")
    
    # Create and run workflow
    workflow_runner = create_workflow(config)
    result = await workflow_runner(config.target_repo_url, config.output_dir)
    
    print(f"Documentation built at: {result.get('build_path')}")

# Run the async function
asyncio.run(generate_docs())
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
