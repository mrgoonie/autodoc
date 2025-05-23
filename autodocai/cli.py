"""
Command-line interface for AutoDoc AI.

This module provides the entry point for the AutoDoc AI tool, allowing users
to generate documentation from GitHub repositories through the command line.
"""

import asyncio
import os
import sys
from typing import Optional

import click
import nest_asyncio
from dotenv import load_dotenv

from autodocai.config import AppConfig
from autodocai.orchestrator import create_workflow

# Apply nest_asyncio to allow nested event loops (useful for Jupyter and certain environments)
nest_asyncio.apply()

# Load environment variables from .env file
load_dotenv()


@click.group()
@click.version_option()
def cli():
    """AutoDoc AI - Generate Docusaurus documentation from GitHub repositories using AI."""
    pass


# Define the underlying async function that will be called by sync_generate
async def generate(
    repo_url: Optional[str],
    output_dir: Optional[str],
    languages: Optional[str],
    github_pat: Optional[str],
    debug: bool,
):
    """Asynchronous implementation of the documentation generation process."""
    # Create configuration from CLI args and environment variables
    config = AppConfig.from_env_and_args(
        repo_url=repo_url,
        output_dir=output_dir,
        languages=languages,
        github_pat=github_pat,
        debug=debug,
    )

    # Validate configuration
    if not config.validate():
        sys.exit(1)

    # Create and run the workflow
    workflow_runner = create_workflow(config)
    result = await workflow_runner(repo_url=config.target_repo_url, output_dir=config.output_dir)

    # Extract path and handle completion
    if result.get("build_path"):
        click.echo(f"✅ Documentation generated successfully in {config.output_dir}")
        click.echo(f"   Documentation available at: {result.get('build_path')}")
        
        # Display statistics if available
        snippets = result.get("snippets", [])
        diagrams = result.get("diagrams", {})
        if snippets or diagrams:
            click.echo("\n📊 Statistics:")
            click.echo(f"   Files processed: {len(snippets)}")
            click.echo(f"   Functions documented: {sum(1 for s in snippets if s.get('symbol_type') == 'function')}")
            click.echo(f"   Classes documented: {sum(1 for s in snippets if s.get('symbol_type') == 'class')}")
            click.echo(f"   Diagrams generated: {len(diagrams)}")
    else:
        # Handle errors
        errors = result.get("errors", [])
        messages = result.get("messages", [])
        
        # Extract error messages from either the errors list or messages
        error_messages = []
        if errors:
            error_messages = [f"- {error.get('message', 'Unknown error')}" for error in errors]
        elif messages:
            # Try to extract error messages from agent messages
            error_messages = [f"- {msg.message}" for msg in messages if hasattr(msg, 'message_type') and msg.message_type == 'error']
        
        if not error_messages:
            error_messages = ["Unknown error occurred"]
            
        click.echo(f"❌ Error(s):\n{chr(10).join(error_messages)}")
        sys.exit(1)


@cli.command()
def configure():
    """Configure AutoDoc AI settings."""
    click.echo("Interactive configuration not yet implemented.")
    click.echo("Please edit your .env file directly or use command-line options.")


# Define a synchronous wrapper for the async generate command
@cli.command(name="generate")
@click.option(
    "--repo-url",
    help="GitHub repository URL to generate documentation for.",
    type=str,
    default=None,
)
@click.option(
    "--output-dir",
    help="Directory to save the generated documentation.",
    type=str,
    default=None,
)
@click.option(
    "--languages",
    help="Comma-separated list of languages to generate documentation for (e.g., 'EN,VI').",
    type=str,
    default=None,
)
@click.option(
    "--github-pat",
    help="GitHub Personal Access Token for private repositories.",
    type=str,
    default=None,
)
@click.option(
    "--debug",
    help="Enable debug mode with more verbose output.",
    is_flag=True,
    default=False,
)
def sync_generate(repo_url, output_dir, languages, github_pat, debug):
    """Generate documentation from a GitHub repository."""
    try:
        asyncio.run(generate(repo_url, output_dir, languages, github_pat, debug))
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        if debug:
            import traceback
            click.echo(traceback.format_exc())
        sys.exit(1)


def main():
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    main()
