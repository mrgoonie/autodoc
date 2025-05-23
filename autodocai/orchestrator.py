"""
Orchestrator for AutoDoc AI.

This module orchestrates the workflow of the AutoDoc AI system using LangGraph.
"""

import os
import logging
from typing import Dict, Any, List, Tuple, Callable, Optional

from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from autodocai.config import AppConfig
from autodocai.agents.base import BaseAgent
from autodocai.agents.repo_cloner_agent import RepoClonerAgent
from autodocai.agents.code_parser_agent import CodeParserAgent
from autodocai.agents.summarizer_agent import SummarizerAgent
from autodocai.agents.docstring_enhancer_agent import DocstringEnhancerAgent
from autodocai.agents.rag_query_agent import RAGQueryAgent
from autodocai.agents.mermaid_diagram_agent import MermaidDiagramAgent
from autodocai.agents.translation_agent import TranslationAgent
from autodocai.agents.docusaurus_formatter_agent import DocusaurusFormatterAgent
from autodocai.agents.documentation_builder_agent import DocumentationBuilderAgent
from autodocai.notifications import NotificationService

logger = logging.getLogger("autodocai.orchestrator")

class WorkflowState(BaseModel):
    """State of the AutoDoc AI workflow."""
    
    # Initial inputs
    repo_url: str = Field(description="URL of the GitHub repository")
    output_dir: str = Field(description="Output directory for documentation")
    
    def dict(self, *args, **kwargs):
        """Convert state to dictionary for callbacks and serialization.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the state
        """
        # Use Pydantic's model_dump instead of dict for newer Pydantic versions
        if hasattr(super(), "model_dump"):
            return super().model_dump(*args, **kwargs)
        return super().dict(*args, **kwargs)
    
    # State from repo cloner
    repo_info: Optional[Any] = Field(default=None, description="Repository information")
    
    # State from code parser
    snippets: Optional[List[Dict[str, Any]]] = Field(default=None, description="Code snippets")
    
    # State from summarizer
    summaries: Optional[Dict[str, Dict[str, str]]] = Field(default=None, description="Summaries of code snippets")
    
    # State from docstring enhancer
    enhanced_snippets: Optional[List[Dict[str, Any]]] = Field(default=None, description="Snippets with enhanced docstrings")
    
    # State from diagram generator
    diagrams: Optional[Dict[str, str]] = Field(default=None, description="Generated diagrams")
    
    # State from RAG query agent
    rag_results: Optional[Dict[str, Any]] = Field(default=None, description="Results from RAG queries")
    
    # State from documentation formatter
    docs_path: Optional[str] = Field(default=None, description="Path to generated documentation")
    
    # State from documentation builder
    build_result: Optional[Dict[str, Any]] = Field(default=None, description="Build result information")
    build_path: Optional[str] = Field(default=None, description="Path to built site")
    
    # Workflow control and messaging
    current_stage: str = Field(default="start", description="Current stage of the workflow")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Messages from agents")
    errors: List[Dict[str, str]] = Field(default_factory=list, description="Errors encountered during processing")

def create_workflow(config: AppConfig) -> Callable:
    """
    Create the AutoDoc AI workflow.
    
    Args:
        config: Application configuration
        
    Returns:
        Callable: Function to run the workflow
    """
    # Initialize agents
    repo_cloner = RepoClonerAgent(config)
    code_parser = CodeParserAgent(config)
    summarizer = SummarizerAgent(config)
    docstring_enhancer = DocstringEnhancerAgent(config)
    rag_query = RAGQueryAgent(config)
    diagram_generator = MermaidDiagramAgent(config)
    translator = TranslationAgent(config)
    docusaurus_formatter = DocusaurusFormatterAgent(config)
    documentation_builder = DocumentationBuilderAgent(config)
    
    # Initialize notification service
    notification_service = NotificationService(config)
    
    # Define the workflow
    workflow = StateGraph(WorkflowState)
    
    # Define nodes
    workflow.add_node("repo_cloner", repo_cloner.execute)
    workflow.add_node("code_parser", code_parser.execute)
    workflow.add_node("summarizer", summarizer.execute)
    workflow.add_node("docstring_enhancer", docstring_enhancer.execute)
    workflow.add_node("rag_query", rag_query.execute)
    workflow.add_node("diagram_generator", diagram_generator.execute)
    workflow.add_node("translator", translator.execute)
    workflow.add_node("docusaurus_formatter", docusaurus_formatter.execute)
    workflow.add_node("documentation_builder", documentation_builder.execute)
    
    # Define edges for the workflow
    workflow.add_edge("repo_cloner", "code_parser")
    workflow.add_edge("code_parser", "summarizer")
    workflow.add_edge("summarizer", "docstring_enhancer")
    workflow.add_edge("docstring_enhancer", "rag_query")
    workflow.add_edge("rag_query", "diagram_generator")
    workflow.add_edge("diagram_generator", "translator")
    workflow.add_edge("translator", "docusaurus_formatter")
    workflow.add_edge("docusaurus_formatter", "documentation_builder")
    workflow.add_edge("documentation_builder", END)
    
    # Set the entrypoint for the workflow
    workflow.set_entry_point("repo_cloner")
    
    # Compile the workflow
    app = workflow.compile()
    
    # Create the runner function
    async def run_workflow(repo_url: str, output_dir: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Run the AutoDoc AI workflow.
        
        Args:
            repo_url: URL of the GitHub repository
            output_dir: Output directory for documentation
            progress_callback: Optional callback function to track progress
            
        Returns:
            Dict[str, Any]: Result of the workflow
        """
        try:
            # Create initial state
            state = WorkflowState(
                repo_url=repo_url,
                output_dir=output_dir
            )
            
            # If we have a progress callback, add event handlers to the app
            if progress_callback:
                try:
                    # Create a custom event handler for the progress tracking
                    async def on_node_complete(state, current_node, next_node):
                        try:
                            # Update the current stage
                            if hasattr(state, 'current_stage'):
                                # Map the node name to a human-readable stage name
                                node_to_stage = {
                                    "repo_cloner": "repository_cloning",
                                    "code_parser": "code_parsing",
                                    "summarizer": "summarizing_code",
                                    "docstring_enhancer": "enhancing_docstrings",
                                    "rag_query": "generating_architecture", 
                                    "diagram_generator": "creating_diagrams",
                                    "translator": "translating_documentation",
                                    "docusaurus_formatter": "formatting_documentation",
                                    "documentation_builder": "building_documentation"
                                }
                                
                                # Set the current stage based on the node that just completed
                                if current_node in node_to_stage:
                                    state.current_stage = node_to_stage[current_node]
                                    
                            # Call the progress callback with the state dictionary
                            if progress_callback:
                                state_dict = state.dict()
                                await progress_callback(state_dict)
                                
                            return state
                        except Exception as e:
                            logger.error(f"Error in progress callback handler: {str(e)}")
                            # Continue the workflow even if progress tracking fails
                            return state
                    
                    # Register the event handler with the app (if supported)
                    if hasattr(app, "register_node_complete_handler"):
                        app.register_node_complete_handler(on_node_complete)
                        
                    # Call the callback with the initial state
                    await progress_callback(state.dict())
                except Exception as e:
                    # Log but continue even if progress tracking setup fails
                    logger.error(f"Error setting up progress tracking: {str(e)}")
                
            # Run the workflow with proper error handling
            try:
                result = await app.ainvoke(state)
            except Exception as e:
                logger.error(f"Error during workflow execution: {str(e)}")
                # Ensure we have a state to work with even in case of failure
                if 'state' in locals():
                    if hasattr(state, "errors") and state.errors is None:
                        state.errors = []
                    if hasattr(state, "errors"):
                        state.errors.append({"agent": "orchestrator", "message": str(e)})
                    state.current_stage = "error"
                    return state.dict()
                raise
            
            # Send success notification if we have a build path
            try:
                if result.build_path:
                    # Calculate statistics from the result
                    stats = {
                        "files_processed": len(result.snippets) if result.snippets else 0,
                        "functions_documented": sum(1 for s in result.snippets if s.get("symbol_type") == "function" or getattr(s, "symbol_type", "") == "function") if result.snippets else 0,
                        "classes_documented": sum(1 for s in result.snippets if s.get("symbol_type") == "class" or getattr(s, "symbol_type", "") == "class") if result.snippets else 0,
                        "diagrams_generated": len(result.diagrams) if result.diagrams else 0
                    }
                    
                    # Try to send notification but don't block completion if it fails
                    try:
                        await notification_service.send_success_notification(
                            repo_url=repo_url,
                            docs_path=result.build_path,
                            stats=stats
                        )
                    except Exception as notify_error:
                        logger.warning(f"Failed to send success notification: {str(notify_error)}")
            except Exception as result_error:
                logger.error(f"Error processing result: {str(result_error)}")
            
            # Return the result as a dictionary for serialization
            return result.dict() if hasattr(result, "dict") else result
            
        except Exception as e:
            logger.error(f"Error in workflow: {str(e)}", exc_info=True)
            
            # Try to send error notification but don't block if it fails
            try:
                await notification_service.send_error_notification(
                    repo_url=repo_url,
                    error_message=str(e),
                    stage=state.current_stage if 'state' in locals() else "initialization"
                )
            except Exception as notify_error:
                logger.warning(f"Failed to send error notification: {str(notify_error)}")
            
            # Create a basic error state to return if everything else fails
            error_state = {
                "repo_url": repo_url,
                "output_dir": output_dir,
                "current_stage": "error",
                "errors": [{"agent": "orchestrator", "message": str(e)}]
            }
            
            # Return state dict if available, otherwise basic error state
            if 'state' in locals() and hasattr(state, "dict"):
                return state.dict()
            
            raise
    
    return run_workflow