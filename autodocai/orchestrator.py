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
    
    # State from repo cloner
    repo_info: Optional[Dict[str, Any]] = Field(default=None, description="Repository information")
    
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
    
    # Define edges
    workflow.add_edge("repo_cloner", "code_parser")
    workflow.add_edge("code_parser", "summarizer")
    workflow.add_edge("summarizer", "docstring_enhancer")
    workflow.add_edge("docstring_enhancer", "rag_query")
    workflow.add_edge("rag_query", "diagram_generator")
    workflow.add_edge("diagram_generator", "translator")
    workflow.add_edge("translator", "docusaurus_formatter")
    workflow.add_edge("docusaurus_formatter", "documentation_builder")
    workflow.add_edge("documentation_builder", END)
    
    # Compile the workflow
    app = workflow.compile()
    
    # Create the runner function
    async def run_workflow(repo_url: str, output_dir: str) -> Dict[str, Any]:
        """
        Run the AutoDoc AI workflow.
        
        Args:
            repo_url: URL of the GitHub repository
            output_dir: Output directory for documentation
            
        Returns:
            Dict[str, Any]: Result of the workflow
        """
        try:
            # Create initial state
            state = WorkflowState(
                repo_url=repo_url,
                output_dir=output_dir
            )
            
            # Run the workflow
            result = await app.ainvoke(state)
            
            # Send success notification
            if result.build_path:
                stats = {
                    "files_processed": len(result.snippets) if result.snippets else 0,
                    "functions_documented": sum(1 for s in result.snippets if s.get("symbol_type") == "function") if result.snippets else 0,
                    "classes_documented": sum(1 for s in result.snippets if s.get("symbol_type") == "class") if result.snippets else 0,
                    "diagrams_generated": len(result.diagrams) if result.diagrams else 0
                }
                
                await notification_service.send_success_notification(
                    repo_url=repo_url,
                    docs_path=result.build_path,
                    stats=stats
                )
            
            return result.dict()
            
        except Exception as e:
            logger.error(f"Error in workflow: {str(e)}")
            
            # Send error notification
            await notification_service.send_error_notification(
                repo_url=repo_url,
                error_message=str(e),
                stage=state.current_stage if 'state' in locals() else "initialization"
            )
            
            raise
    
    return run_workflow