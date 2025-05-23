"""
Unit tests for DocumentationBuilderAgent.

This module tests the functionality of the DocumentationBuilderAgent, including:
- Building Docusaurus documentation
- Installing dependencies
- Handling error cases
"""

import os
import pytest
import shutil
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock, call

from autodocai.agents.documentation_builder_agent import DocumentationBuilderAgent
from autodocai.schemas import MessageType


class TestDocumentationBuilderAgent:
    """Tests for the DocumentationBuilderAgent class."""

    @pytest.fixture
    def agent(self, mock_config):
        """Create a DocumentationBuilderAgent instance for testing."""
        return DocumentationBuilderAgent(mock_config)
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up after test
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_docs_path(self, temp_output_dir):
        """Create a test docs path with basic Docusaurus structure."""
        docs_path = os.path.join(temp_output_dir, "docs")
        os.makedirs(docs_path, exist_ok=True)
        
        # Create basic docusaurus files
        with open(os.path.join(temp_output_dir, "docusaurus.config.js"), "w") as f:
            f.write("module.exports = { title: 'Test Site' };")
        
        with open(os.path.join(docs_path, "intro.md"), "w") as f:
            f.write("# Introduction\nThis is a test document.")
        
        return temp_output_dir

    @pytest.mark.asyncio
    async def test_execute_no_docs_path(self, agent):
        """Test execute method with no docs path."""
        # Arrange
        state = {"messages": []}

        # Act
        result = await agent._execute(state)

        # Assert
        assert "build_path" not in result
        assert any(m["type"] == MessageType.ERROR for m in result["messages"])

    @pytest.mark.asyncio
    async def test_execute_with_docs_path(self, agent, test_docs_path):
        """Test execute method with docs path."""
        # Arrange
        state = {
            "messages": [],
            "docs_path": test_docs_path
        }
        
        # Mock the build methods
        with patch.object(agent, '_install_dependencies', return_value=True) as mock_install, \
             patch.object(agent, '_build_documentation', return_value=os.path.join(test_docs_path, "build")) as mock_build:
            
            # Act
            result = await agent._execute(state)
            
            # Assert
            assert "build_path" in result
            assert result["build_path"] == os.path.join(test_docs_path, "build")
            assert any(m["type"] == MessageType.SUCCESS for m in result["messages"])
            
            # Verify methods were called
            mock_install.assert_called_once_with(test_docs_path)
            mock_build.assert_called_once_with(test_docs_path)

    @pytest.mark.asyncio
    async def test_install_dependencies_success(self, agent, test_docs_path):
        """Test successful dependency installation."""
        # Arrange
        mock_subprocess = AsyncMock()
        mock_subprocess.communicate.return_value = (b"success", b"")
        mock_subprocess.returncode = 0
        
        # Act
        with patch('asyncio.create_subprocess_exec', return_value=mock_subprocess) as mock_exec:
            result = await agent._install_dependencies(test_docs_path)
        
        # Assert
        assert result is True
        assert mock_exec.call_count >= 1  # Should call npm/yarn at least once
        
        # Verify proper commands were called
        calls = mock_exec.call_args_list
        assert any('npm' in str(call_args) and 'install' in str(call_args) for call_args in calls)

    @pytest.mark.asyncio
    async def test_install_dependencies_failure(self, agent, test_docs_path):
        """Test dependency installation failure."""
        # Arrange
        mock_subprocess = AsyncMock()
        mock_subprocess.communicate.return_value = (b"", b"error")
        mock_subprocess.returncode = 1
        
        # Act
        with patch('asyncio.create_subprocess_exec', return_value=mock_subprocess) as mock_exec:
            result = await agent._install_dependencies(test_docs_path)
        
        # Assert
        assert result is False
        assert mock_exec.call_count >= 1

    @pytest.mark.asyncio
    async def test_build_documentation_success(self, agent, test_docs_path):
        """Test successful documentation build."""
        # Arrange
        build_path = os.path.join(test_docs_path, "build")
        os.makedirs(build_path, exist_ok=True)
        
        mock_subprocess = AsyncMock()
        mock_subprocess.communicate.return_value = (b"success", b"")
        mock_subprocess.returncode = 0
        
        # Act
        with patch('asyncio.create_subprocess_exec', return_value=mock_subprocess) as mock_exec:
            result = await agent._build_documentation(test_docs_path)
        
        # Assert
        assert result == build_path
        assert mock_exec.call_count >= 1  # Should call npm/yarn build
        
        # Verify proper commands were called
        calls = mock_exec.call_args_list
        assert any('npm' in str(call_args) and 'build' in str(call_args) for call_args in calls)

    @pytest.mark.asyncio
    async def test_build_documentation_failure(self, agent, test_docs_path):
        """Test documentation build failure."""
        # Arrange
        mock_subprocess = AsyncMock()
        mock_subprocess.communicate.return_value = (b"", b"error")
        mock_subprocess.returncode = 1
        
        # Act
        with patch('asyncio.create_subprocess_exec', return_value=mock_subprocess) as mock_exec:
            result = await agent._build_documentation(test_docs_path)
        
        # Assert
        assert result is None
        assert mock_exec.call_count >= 1

    @pytest.mark.asyncio
    async def test_execute_full_workflow(self, agent, test_docs_path):
        """Test the full workflow from start to finish."""
        # Arrange
        state = {
            "messages": [],
            "docs_path": test_docs_path
        }
        
        build_path = os.path.join(test_docs_path, "build")
        os.makedirs(build_path, exist_ok=True)
        
        # Create mock for subprocess that returns success
        mock_subprocess = AsyncMock()
        mock_subprocess.communicate.return_value = (b"success", b"")
        mock_subprocess.returncode = 0
        
        # Act
        with patch('asyncio.create_subprocess_exec', return_value=mock_subprocess) as mock_exec:
            result = await agent._execute(state)
        
        # Assert
        assert "build_path" in result
        assert result["build_path"] == build_path
        assert any(m["type"] == MessageType.SUCCESS for m in result["messages"])
        assert mock_exec.call_count >= 2  # Should call for both install and build
