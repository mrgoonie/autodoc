"""
Unit tests for DocusaurusFormatterAgent.

This module tests the functionality of the DocusaurusFormatterAgent, including:
- Creating Docusaurus configuration files
- Generating documentation pages from code snippets
- Creating sidebar configuration
- Handling internationalization
"""

import pytest
import os
import shutil
import json
from unittest.mock import patch, MagicMock, AsyncMock, mock_open

from autodocai.agents.docusaurus_formatter_agent import DocusaurusFormatterAgent
from autodocai.schemas import MessageType, CodeSnippet


class TestDocusaurusFormatterAgent:
    """Tests for the DocusaurusFormatterAgent class."""

    @pytest.fixture
    def agent(self, mock_config):
        """Create a DocusaurusFormatterAgent instance for testing."""
        # Ensure output directory is a temp directory for testing
        config = mock_config
        config.output_dir = "/tmp/autodoc_test_output"
        return DocusaurusFormatterAgent(config)
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup before and teardown after tests."""
        # Setup - create test output directory if it doesn't exist
        os.makedirs("/tmp/autodoc_test_output", exist_ok=True)
        
        yield
        
        # Teardown - remove test output directory
        if os.path.exists("/tmp/autodoc_test_output"):
            shutil.rmtree("/tmp/autodoc_test_output")
    
    @pytest.mark.asyncio
    async def test_execute_missing_repo_info(self, agent):
        """Test execute method with missing repository information."""
        # Arrange
        state = {"messages": []}
        
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            await agent._execute(state)
        
        assert "Repository information is missing" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_execute_with_valid_data(self, agent, sample_workflow_state, mock_snippet):
        """Test execute method with valid data."""
        # Arrange
        state = sample_workflow_state.copy()
        state["snippets"] = [mock_snippet]
        
        # Mock all the internal methods that would normally create files
        with patch.object(agent, '_create_docusaurus_config', AsyncMock(return_value=None)) as mock_create_config, \
             patch.object(agent, '_create_homepage', AsyncMock(return_value=None)) as mock_create_homepage, \
             patch.object(agent, '_create_introduction', AsyncMock(return_value="/tmp/intro.md")) as mock_create_intro, \
             patch.object(agent, '_create_architecture_page', AsyncMock(return_value="/tmp/arch.md")) as mock_create_arch, \
             patch.object(agent, '_group_snippets_by_module', return_value={"test_module.py": {"snippets": [mock_snippet]}}) as mock_group, \
             patch.object(agent, '_create_module_page', AsyncMock(return_value="/tmp/module.md")) as mock_create_module, \
             patch.object(agent, '_create_sidebar_config', AsyncMock(return_value=None)) as mock_create_sidebar:
            
            # Act
            result = await agent._execute(state)
            
            # Assert
            assert "docs_path" in result
            assert result["docs_path"] == agent.config.output_dir
            assert any(m["type"] == MessageType.SUCCESS for m in result["messages"])
            
            # Verify all methods were called
            mock_create_config.assert_called_once()
            mock_create_homepage.assert_called_once()
            mock_create_intro.assert_called_once()
            mock_create_arch.assert_called_once()
            mock_group.assert_called_once()
            mock_create_module.assert_called()
            mock_create_sidebar.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_docusaurus_config(self, agent):
        """Test creating Docusaurus configuration files."""
        # Arrange
        output_dir = "/tmp/autodoc_test_output"
        project_name = "test-project"
        
        # Use mock_open to avoid actual file writes
        m = mock_open()
        
        # Act
        with patch("builtins.open", m):
            await agent._create_docusaurus_config(output_dir, project_name)
        
        # Assert
        # Check that files were "opened" for writing
        assert any("docusaurus.config.js" in call[0][0] for call in m.call_args_list)
        assert any("sidebars.js" in call[0][0] for call in m.call_args_list)
        assert any("custom.css" in call[0][0] for call in m.call_args_list)
        
        # Check that content was written
        write_calls = [call[0][0] for call in m().write.call_args_list]
        config_content = "".join(write_calls)
        
        # Verify key elements in the config
        assert project_name in config_content
        assert "title:" in config_content
        assert "theme:" in config_content
        assert "navbar:" in config_content
    
    @pytest.mark.asyncio
    async def test_create_introduction(self, agent, sample_workflow_state):
        """Test creating introduction page."""
        # Arrange
        docs_dir = "/tmp/autodoc_test_output/docs"
        os.makedirs(docs_dir, exist_ok=True)
        
        repo_info = sample_workflow_state["repo_info"]
        rag_results = sample_workflow_state["rag_results"]
        
        # Act
        with patch("builtins.open", mock_open()) as m:
            result = await agent._create_introduction(docs_dir, repo_info, rag_results)
        
        # Assert
        assert result is not None
        assert os.path.join(docs_dir, "intro.md") in result
        
        # Verify file was opened for writing
        m.assert_called_with(os.path.join(docs_dir, "intro.md"), 'w', encoding='utf-8')
        
        # Check that content was written
        write_calls = [call[0][0] for call in m().write.call_args_list]
        content = "".join(write_calls)
        
        # Verify key elements in the content
        assert "---" in content  # YAML frontmatter
        assert "sidebar_position: 1" in content
        assert "# Introduction" in content
        assert repo_info["name"] in content
        assert "Repository Information" in content
    
    @pytest.mark.asyncio
    async def test_group_snippets_by_module(self, agent, mock_snippet):
        """Test grouping snippets by module."""
        # Arrange
        snippets = [
            mock_snippet,
            CodeSnippet(
                id="test_snippet_2",
                file_path="test_module.py",
                symbol_type="class",
                symbol_name="TestClass",
                language="python",
                start_line=12,
                end_line=20,
                text_content="class TestClass:\n    pass",
                original_docstring=""
            ),
            CodeSnippet(
                id="test_snippet_3",
                file_path="another_module.py",
                symbol_type="function",
                symbol_name="another_function",
                language="python",
                start_line=1,
                end_line=5,
                text_content="def another_function():\n    pass",
                original_docstring=""
            )
        ]
        
        # Act
        result = agent._group_snippets_by_module(snippets)
        
        # Assert
        assert len(result) == 2
        assert "test_module.py" in result
        assert "another_module.py" in result
        
        # Check snippet counts
        assert len(result["test_module.py"]["snippets"]) == 2
        assert len(result["another_module.py"]["snippets"]) == 1
        
        # Check categorization
        test_module = result["test_module.py"]
        assert len(test_module["functions"]) == 1
        assert len(test_module["classes"]) == 1
        assert test_module["functions"][0].symbol_name == "test_function"
        assert test_module["classes"][0].symbol_name == "TestClass"
    
    @pytest.mark.asyncio
    async def test_create_module_page(self, agent, mock_snippet, sample_workflow_state):
        """Test creating a module page."""
        # Arrange
        docs_dir = "/tmp/autodoc_test_output/docs/modules"
        os.makedirs(docs_dir, exist_ok=True)
        
        module_path = "test_module.py"
        snippets = [mock_snippet]
        summaries = {mock_snippet.id: {"en": "This is a summary", "vi": "Đây là tóm tắt"}}
        diagrams = {"class_test_module": "```mermaid\nclassDiagram\nClass1\n```"}
        
        # Mock json.dump to avoid actual file writes
        mock_json_dump = MagicMock()
        
        # Act
        with patch("builtins.open", mock_open()) as m, \
             patch("json.dump", mock_json_dump):
            result = await agent._create_module_page(
                docs_dir, module_path, snippets, summaries, diagrams, 
                sample_workflow_state["rag_results"]
            )
        
        # Assert
        assert result is not None
        
        # Verify files were opened for writing
        assert any("test_module.md" in call[0][0] for call in m.call_args_list)
        assert any("_category_.json" in call[0][0] for call in m.call_args_list)
        
        # Check that content was written
        write_calls = [call[0][0] for call in m().write.call_args_list]
        content = "".join(write_calls)
        
        # Verify key elements in the content
        assert "---" in content  # YAML frontmatter
        assert "# test_module.py" in content
        assert "This is a summary" in content
        assert mock_snippet.symbol_name in content
        assert "```python" in content
        
        # Verify category JSON was written
        mock_json_dump.assert_called()
        args, _ = mock_json_dump.call_args
        assert "label" in args[0]
        assert args[0]["label"] == "test_module"
