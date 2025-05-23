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


@cli.command()
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
async def generate(
    repo_url: Optional[str],
    output_dir: Optional[str],
    languages: Optional[str],
    github_pat: Optional[str],
    debug: bool,
):
    """Generate documentation from a GitHub repository."""
    try:
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

        if result.get("build_path"):
            click.echo(f"✅ Documentation generated successfully in {config.output_dir}")
            click.echo(f"   Documentation available at: {result.get('build_path')}")
        else:
            errors = result.get("errors", [])
            error_message = "\n".join([f"- {error.get('message', 'Unknown error')}" for error in errors]) if errors else "Unknown error occurred"
            click.echo(f"❌ Error(s):\n{error_message}")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        if debug:
            import traceback
            click.echo(traceback.format_exc())
        sys.exit(1)


@cli.command()
def configure():
    """Configure AutoDoc AI settings."""
    click.echo("Interactive configuration not yet implemented.")
    click.echo("Please edit your .env file directly or use command-line options.")


def main():
    """Entry point for the application."""
    # Use asyncio.run for the async command
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        # Remove the 'generate' argument before passing to click
        sys.argv.pop(1)
        asyncio.run(generate())
    else:
        cli()


if __name__ == "__main__":
    main()
