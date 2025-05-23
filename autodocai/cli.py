"""
Command-line interface for AutoDoc AI.

This module provides the entry point for the AutoDoc AI tool, allowing users
to generate documentation from GitHub repositories through the command line.
"""

import asyncio
import os
import sys
import time
from typing import Optional, Dict, Any

import click
import nest_asyncio
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from autodocai.config import AppConfig
from autodocai.orchestrator import create_workflow, WorkflowState
from autodocai.schemas import MessageType

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
    no_progress: bool = False,
):
    """Asynchronous implementation of the documentation generation process."""
    # Create rich console for better output
    console = Console()
    
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

    console.print(f"[bold blue]🚀 Starting AutoDoc AI for[/] [bold green]{config.target_repo_url}[/]")
    console.print(f"[dim]Output directory: {config.output_dir}[/]")
    
    # Define agent names for progress display
    agent_steps = [
        "Repository Cloning",
        "Code Parsing",
        "Code Summarization",
        "Docstring Enhancement", 
        "Knowledge Base Queries",
        "Diagram Generation",
        "Translation",
        "Documentation Formatting",
        "Documentation Building"
    ]
    
    # Current step tracking
    current_step = 0
    
    # Create and run the workflow
    workflow_runner = create_workflow(config)
    
    start_time = time.time()
    
    if no_progress:
        # Run workflow without progress display
        result = await workflow_runner(repo_url=config.target_repo_url, output_dir=config.output_dir)
    else:
        # Set up progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/]"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # Create a task for overall progress
            task = progress.add_task(f"[yellow]Processing {os.path.basename(config.target_repo_url)}...[/]", total=len(agent_steps))
            
            # Custom callback to update progress based on workflow state
            async def progress_callback(state: Dict[str, Any]):
                nonlocal current_step
                messages = state.get("messages", [])
                
                # Update progress based on agent messages
                if messages:
                    # Get the most recent message
                    for msg in reversed(messages):
                        if hasattr(msg, "agent_name"):
                            agent_name = msg.agent_name
                            # Find the corresponding step
                            for i, step_name in enumerate(agent_steps):
                                if any(word in agent_name for word in step_name.split()):
                                    new_step = i
                                    if new_step > current_step:
                                        current_step = new_step
                                        progress.update(task, completed=current_step, description=f"[yellow]{agent_steps[current_step]}...[/]")
                                    break
                            break
                
                # Allow the UI to update
                await asyncio.sleep(0.1)
            
            # Run workflow with progress tracking
            try:
                result = await workflow_runner(
                    repo_url=config.target_repo_url, 
                    output_dir=config.output_dir,
                    progress_callback=progress_callback
                )
                progress.update(task, completed=len(agent_steps), description="[green]Documentation Complete![/]")
            except Exception as e:
                progress.update(task, description=f"[red]Error: {str(e)}[/]")
                raise
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Extract path and handle completion
    if result.get("build_path"):
        console.print(f"\n[bold green]✅ Documentation generated successfully in {elapsed_time:.1f} seconds[/]")
        console.print(f"[bold]📂 Documentation path:[/] {result.get('build_path')}")
        
        # Display statistics if available
        snippets = result.get("snippets", [])
        diagrams = result.get("diagrams", {})
        if snippets or diagrams:
            console.print("\n[bold]📊 Statistics:[/]")
            console.print(f"   [cyan]Files processed:[/] {len(snippets)}")
            console.print(f"   [cyan]Functions documented:[/] {sum(1 for s in snippets if s.get('symbol_type') == 'function')}")
            console.print(f"   [cyan]Classes documented:[/] {sum(1 for s in snippets if s.get('symbol_type') == 'class')}")
            console.print(f"   [cyan]Diagrams generated:[/] {len(diagrams)}")
            
            # Show languages if translations were done
            languages = config.output_languages
            if len(languages) > 1:
                console.print(f"   [cyan]Languages:[/] {', '.join(languages)}")
        
        # Show command to open docs
        console.print("\n[bold yellow]To view documentation:[/]")
        console.print(f"   cd {result.get('build_path')} && python -m http.server 8000")
        console.print("   Then open: [blue underline]http://localhost:8000[/]")
                
        return result
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
            error_messages = [f"- {msg.content}" for msg in messages if hasattr(msg, 'message_type') and msg.message_type == MessageType.ERROR]
        
        if not error_messages:
            error_messages = ["Unknown error occurred"]
        
        console.print(f"\n[bold red]❌ Error(s):[/]")
        for error in error_messages:
            console.print(f"[red]{error}[/]")
        
        sys.exit(1)


@cli.command()
@click.option(
    "--show",
    help="Show current configuration.",
    is_flag=True,
    default=False,
)
def configure(show):
    """Configure AutoDoc AI settings or show current configuration."""
    console = Console()
    
    # Show current configuration if requested
    if show:
        config = AppConfig.from_env_and_args()
        console.print("[bold blue]Current AutoDoc AI Configuration:[/]")
        console.print(f"[cyan]Target Repository URL:[/] {config.target_repo_url or 'Not set'}")
        console.print(f"[cyan]Output Directory:[/] {config.output_dir or 'Not set'}")
        console.print(f"[cyan]Output Languages:[/] {', '.join(config.output_languages)}")
        console.print(f"[cyan]Qdrant URL:[/] {config.qdrant_url}")
        console.print(f"[cyan]Log Level:[/] {config.log_level}")
        console.print(f"[cyan]GitHub PAT:[/] {'✅ Configured' if config.github_pat else '❌ Not configured'}")
        console.print(f"[cyan]OpenRouter API Key:[/] {'✅ Configured' if config.openrouter_api_key else '❌ Not configured'}")
        console.print(f"[cyan]SendGrid API Key:[/] {'✅ Configured' if config.sendgrid_api_key else '❌ Not configured'}")
        console.print(f"[cyan]Notification Email:[/] {config.notification_email_to or 'Not configured'}")
        return
    
    # Interactive configuration
    console.print("[bold blue]AutoDoc AI Configuration[/]")
    console.print("This will create or update your .env file with new settings.")
    
    # Get current config
    config = AppConfig.from_env_and_args()
    
    # Get new values
    repo_url = click.prompt("Target Repository URL", default=config.target_repo_url or "", show_default=True)
    output_dir = click.prompt("Output Directory", default=config.output_dir or "./docs", show_default=True)
    languages = click.prompt("Output Languages (comma-separated)", default=",".join(config.output_languages), show_default=True)
    github_pat = click.prompt("GitHub Personal Access Token (for private repos)", default=config.github_pat or "", show_default=False, hide_input=True)
    openrouter_key = click.prompt("OpenRouter API Key", default=config.openrouter_api_key or "", show_default=False, hide_input=True)
    
    # Write to .env file
    env_path = os.path.join(os.getcwd(), ".env")
    with open(env_path, "w") as f:
        f.write(f"TARGET_REPO_URL={repo_url}\n")
        f.write(f"OUTPUT_DIR={output_dir}\n")
        f.write(f"OUTPUT_LANGUAGES={languages}\n")
        if github_pat:
            f.write(f"GITHUB_PAT={github_pat}\n")
        if openrouter_key:
            f.write(f"OPENROUTER_API_KEY={openrouter_key}\n")
    
    console.print("[bold green]✅ Configuration saved successfully![/]")
    console.print(f"[dim]Configuration file: {env_path}[/]")


@cli.command()
@click.argument("repo_url", required=True)
@click.option(
    "--github-pat",
    help="GitHub Personal Access Token for private repositories.",
    type=str,
    default=None,
)
def info(repo_url, github_pat):
    """Display information about a GitHub repository."""
    console = Console()
    console.print(f"[bold blue]Fetching information for[/] [bold green]{repo_url}[/]")
    
    # Create config with a default output directory
    temp_output_dir = os.path.join(os.getcwd(), "temp_docs")
    config = AppConfig.from_env_and_args(
        repo_url=repo_url, 
        github_pat=github_pat,
        output_dir=temp_output_dir
    )
    
    try:
        # Create repo cloner agent
        from autodocai.agents.repo_cloner_agent import RepoClonerAgent
        repo_cloner = RepoClonerAgent(config)
        
        # Show progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/]"),
            console=console
        ) as progress:
            task = progress.add_task("Cloning repository...", total=1)
            
            # Run async in a sync context
            async def get_repo_info():
                # Initialize state with config and required keys
                state = {
                    "repo_url": repo_url, 
                    "messages": [],
                    "config": config,  # Add config to state
                    "output_dir": os.path.join(os.getcwd(), "temp_docs"),  # Temporary output dir
                    "current_stage": "repo_cloning"
                }
                result = await repo_cloner.execute(state)
                progress.update(task, completed=1, description="Repository cloned")
                return result
            
            result = asyncio.run(get_repo_info())
        
        # Show repository information
        repo_info = result.get("repo_info")
        if repo_info:
            console.print("\n[bold]Repository Information:[/]")
            console.print(f"[cyan]Name:[/] {repo_info.name}")
            console.print(f"[cyan]Description:[/] {repo_info.description or 'No description available'}")
            console.print(f"[cyan]Default Branch:[/] {repo_info.default_branch}")
            console.print(f"[cyan]Languages:[/] {', '.join(repo_info.languages)}")
            console.print(f"[cyan]Private:[/] {'Yes' if repo_info.is_private else 'No'}")
            console.print(f"[cyan]Local Path:[/] {repo_info.local_path}")
            
            # Count files by type
            if os.path.exists(repo_info.local_path):
                file_types = {}
                total_files = 0
                for root, _, files in os.walk(repo_info.local_path):
                    for file in files:
                        if file.startswith('.'):
                            continue
                        ext = os.path.splitext(file)[1]
                        if ext:
                            file_types[ext] = file_types.get(ext, 0) + 1
                        total_files += 1
                
                # Display file type counts
                console.print(f"\n[bold]File Statistics ([cyan]{total_files}[/] total files):[/]")
                for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]:  # Top 10
                    console.print(f"  [cyan]{ext}:[/] {count} files")
                
                # Suggest command to generate docs
                console.print("\n[bold yellow]Generate Documentation:[/]")
                console.print(f"  autodocai generate --repo-url {repo_url} --output-dir ./docs/{repo_info.name}")
        else:
            console.print("[bold red]❌ Failed to retrieve repository information[/]")
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/] {str(e)}")
        sys.exit(1)


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
@click.option(
    "--no-progress",
    help="Disable progress display.",
    is_flag=True,
    default=False,
)
def sync_generate(repo_url, output_dir, languages, github_pat, debug, no_progress):
    """Generate documentation from a GitHub repository."""
    try:
        # Create console for rich output
        console = Console()
        
        # Get absolute path for output directory if provided
        if output_dir and not os.path.isabs(output_dir):
            output_dir = os.path.abspath(output_dir)
            
        # Run the async generate function
        asyncio.run(generate(repo_url, output_dir, languages, github_pat, debug, no_progress))
    except Exception as e:
        console = Console()
        console.print(f"[bold red]❌ Error:[/] {str(e)}")
        if debug:
            import traceback
            console.print("[bold yellow]Traceback:[/]")
            console.print(traceback.format_exc())
        sys.exit(1)


def main():
    """Entry point for the application."""
    cli()


if __name__ == "__main__":
    main()
