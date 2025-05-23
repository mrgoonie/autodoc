"""
Integration tests for AutoDoc AI.

This module tests the full workflow integration, from repository cloning to
documentation generation, using a sample GitHub repository.
"""

import os
import pytest
import shutil
from unittest.mock import patch, MagicMock, AsyncMock

from autodocai.config import AppConfig
from autodocai.orchestrator import create_workflow, WorkflowState


class TestIntegration:
    """Integration tests for the full AutoDoc AI workflow."""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing."""
        config = AppConfig(
            target_repo_url="https://github.com/mrgoonie/searchapi",
            output_dir="/tmp/autodoc_test_integration",
            github_pat=None,  # Not needed for public repos
            output_languages=["EN"],
            openrouter_api_key="fake_api_key",
            sendgrid_api_key=None,
            sendgrid_from_email=None,
            notification_email_to=None,
            summarizer_model_name="openai/gpt-4-turbo",
            rag_model_name="openai/gpt-4-turbo",
            qdrant_url="http://localhost:6333",  # Added for testing
            log_level="INFO"
        )
        return config
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup before and teardown after tests."""
        # Setup - create test output directory if it doesn't exist
        os.makedirs("/tmp/autodoc_test_integration", exist_ok=True)
        
        yield
        
        # Teardown - remove test output directory
        if os.path.exists("/tmp/autodoc_test_integration"):
            shutil.rmtree("/tmp/autodoc_test_integration")
    
    @pytest.mark.asyncio
    @pytest.mark.slow  # Mark as slow test since it's integration
    @pytest.mark.integration  # Mark as integration test
    async def test_full_workflow_with_mocks(self, sample_config):
        """Test the full workflow with mocked agents."""
        # Create mock states for each stage of processing
        mock_repo_info = {
            "name": "searchapi",
            "url": "https://github.com/mrgoonie/searchapi",
            "description": "A search API implementation",
            "default_branch": "main",
            "languages": ["Python", "JavaScript"]
        }
        
        mock_snippets = [
            {
                "id": "snippet1",
                "file_path": "app.py",
                "symbol_type": "function",
                "symbol_name": "search",
                "language": "python",
                "start_line": 1,
                "end_line": 10,
                "text_content": "def search():\n    pass",
                "original_docstring": ""
            }
        ]
        
        mock_summaries = {
            "snippet1": {
                "en": "This function performs a search operation",
                "vi": "Hàm này thực hiện tìm kiếm"
            }
        }
        
        mock_diagrams = {
            "architecture": "```mermaid\ngraph TD\nA-->B\n```",
            "module_dependencies": "```mermaid\ngraph TD\nC-->D\n```"
        }
        
        # Create mock agents
        mock_repo_cloner = AsyncMock(return_value={"repo_info": mock_repo_info})
        mock_code_parser = AsyncMock(return_value={"snippets": mock_snippets})
        mock_summarizer = AsyncMock(return_value={"summaries": mock_summaries})
        mock_docstring_enhancer = AsyncMock(return_value={"enhanced_snippets": mock_snippets})
        mock_rag_query = AsyncMock(return_value={"rag_results": {"architectural_overview": {"en": "Architecture overview"}}})
        mock_diagram_generator = AsyncMock(return_value={"diagrams": mock_diagrams})
        mock_translator = AsyncMock(return_value={"translations": {"en": "English", "vi": "Vietnamese"}})
        mock_docusaurus_formatter = AsyncMock(return_value={"docs_path": "/tmp/autodoc_test_integration/docs"})
        mock_documentation_builder = AsyncMock(return_value={"build_path": "/tmp/autodoc_test_integration/build"})
        
        # Create workflow with patched agents
        with patch('autodocai.agents.repo_cloner_agent.RepoClonerAgent.execute', mock_repo_cloner), \
             patch('autodocai.agents.code_parser_agent.CodeParserAgent.execute', mock_code_parser), \
             patch('autodocai.agents.summarizer_agent.SummarizerAgent.execute', mock_summarizer), \
             patch('autodocai.agents.docstring_enhancer_agent.DocstringEnhancerAgent.execute', mock_docstring_enhancer), \
             patch('autodocai.agents.rag_query_agent.RAGQueryAgent.execute', mock_rag_query), \
             patch('autodocai.agents.mermaid_diagram_agent.MermaidDiagramAgent.execute', mock_diagram_generator), \
             patch('autodocai.agents.translation_agent.TranslationAgent.execute', mock_translator), \
             patch('autodocai.agents.docusaurus_formatter_agent.DocusaurusFormatterAgent.execute', mock_docusaurus_formatter), \
             patch('autodocai.agents.documentation_builder_agent.DocumentationBuilderAgent.execute', mock_documentation_builder), \
             patch('autodocai.notifications.NotificationService.send_success_notification', AsyncMock(return_value=True)):
            
            # Create the workflow runner
            workflow_runner = create_workflow(sample_config)
            
            # Run the workflow
            result = await workflow_runner(
                repo_url=sample_config.target_repo_url,
                output_dir=sample_config.output_dir
            )
            
            # Verify the result
            assert result is not None
            assert "build_path" in result
            assert result["build_path"] == "/tmp/autodoc_test_integration/build"
            
            # Verify each agent was called
            mock_repo_cloner.assert_called_once()
            mock_code_parser.assert_called_once()
            mock_summarizer.assert_called_once()
            mock_docstring_enhancer.assert_called_once()
            mock_rag_query.assert_called_once()
            mock_diagram_generator.assert_called_once()
            mock_translator.assert_called_once()
            mock_docusaurus_formatter.assert_called_once()
            mock_documentation_builder.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.e2e  # Mark as end-to-end test
@pytest.mark.skipif(os.environ.get("OPENROUTER_API_KEY") is None, reason="OPENROUTER_API_KEY not set")
async def test_real_workflow_with_searchapi():
    """
    Test the complete workflow with the real searchapi repository.
    
    This test requires:
    - OPENROUTER_API_KEY environment variable to be set
    - Internet connection to clone the repository
    - Sufficient time to process the entire repo
    
    It's skipped by default and should be run manually when needed.
    """
    # Create configuration with real API key
    config = AppConfig(
        target_repo_url="https://github.com/mrgoonie/searchapi",
        output_dir="/tmp/autodoc_searchapi_test",
        github_pat=None,  # Not needed for public repos
        output_languages=["EN"],
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY"),
        sendgrid_api_key=None,
        sendgrid_from_email=None,
        notification_email_to=None,
        summarizer_model_name="openai/gpt-4-turbo",
        rag_model_name="openai/gpt-4-turbo",
        log_level="INFO"
    )
    
    # Clean output directory if it exists
    if os.path.exists(config.output_dir):
        shutil.rmtree(config.output_dir)
    
    # Create the workflow runner
    workflow_runner = create_workflow(config)
    
    # Run the workflow
    result = await workflow_runner(
        repo_url=config.target_repo_url,
        output_dir=config.output_dir
    )
    
    # Verify the result
    assert result is not None
    assert "build_path" in result
    assert os.path.exists(result["build_path"])
    
    # Check for key documentation files
    assert os.path.exists(os.path.join(config.output_dir, "docs", "intro.md"))
    assert os.path.exists(os.path.join(config.output_dir, "docusaurus.config.js"))
    
    # Clean up after test
    shutil.rmtree(config.output_dir)
