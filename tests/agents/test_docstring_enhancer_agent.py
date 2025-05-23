"""
Unit tests for DocstringEnhancerAgent.

This module tests the functionality of the DocstringEnhancerAgent, including:
- Processing code snippets without docstrings
- Generating enhanced docstrings using AI
- Error handling and edge cases
"""

import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from autodocai.agents.docstring_enhancer_agent import DocstringEnhancerAgent
from autodocai.schemas import MessageType, CodeSnippet


class TestDocstringEnhancerAgent:
    """Tests for the DocstringEnhancerAgent class."""

    @pytest.fixture
    def agent(self, mock_config):
        """Create a DocstringEnhancerAgent instance for testing."""
        return DocstringEnhancerAgent(mock_config)
    
    @pytest.fixture
    def mock_snippet(self):
        """Create a mock code snippet for testing."""
        return CodeSnippet(
            id="test_snippet_1",
            file_path="test_file.py",
            symbol_type="function",
            symbol_name="test_function",
            language="python",
            start_line=1,
            end_line=10,
            text_content="def test_function(arg1, arg2):\n    # This is a test function\n    return arg1 + arg2",
            original_docstring=""
        )
    
    @pytest.fixture
    def mock_snippet_with_docstring(self):
        """Create a mock code snippet with docstring for testing."""
        return CodeSnippet(
            id="test_snippet_2",
            file_path="test_file.py",
            symbol_type="function",
            symbol_name="test_function_with_docs",
            language="python",
            start_line=15,
            end_line=30,
            text_content="def test_function_with_docs(arg1, arg2):\n    \"\"\"This is a basic docstring.\"\"\"\n    return arg1 + arg2",
            original_docstring="This is a basic docstring."
        )

    @pytest.mark.asyncio
    async def test_execute_no_data(self, agent):
        """Test execute method with no data."""
        # Arrange
        state = {"messages": []}

        # Act
        result = await agent._execute(state)

        # Assert
        assert "enhanced_snippets" not in result
        assert any(m["type"] == MessageType.WARNING for m in result["messages"])

    @pytest.mark.asyncio
    async def test_execute_with_snippets(self, agent, mock_snippet, mock_snippet_with_docstring):
        """Test execute method with code snippets."""
        # Arrange
        state = {
            "messages": [],
            "snippets": [mock_snippet, mock_snippet_with_docstring]
        }
        
        # Mock the docstring generation method
        with patch.object(agent, '_generate_docstring', return_value={
            "en": "Enhanced docstring for test_function",
            "vi": "Docstring nâng cao cho test_function"
        }) as mock_generate:
            
            # Act
            result = await agent._execute(state)
            
            # Assert
            assert "enhanced_snippets" in result
            assert len(result["enhanced_snippets"]) == 1  # Only the snippet without docstring should be enhanced
            assert result["enhanced_snippets"][0].symbol_name == "test_function"
            assert result["enhanced_snippets"][0].enhanced_docstring["en"] == "Enhanced docstring for test_function"
            assert any(m["type"] == MessageType.SUCCESS for m in result["messages"])
            
            # Verify docstring generation was called once for the snippet without docstring
            mock_generate.assert_called_once_with(
                mock_snippet.text_content,
                mock_snippet.symbol_type,
                mock_snippet.symbol_name
            )

    @pytest.mark.asyncio
    async def test_generate_docstring(self, agent, mock_snippet):
        """Test generating docstring for a code snippet."""
        # Arrange
        expected_en_docstring = "This function adds two numbers together."
        expected_vi_docstring = "Hàm này cộng hai số lại với nhau."
        
        # Mock the API call method
        with patch.object(agent, '_call_openrouter_api') as mock_api:
            mock_api.side_effect = [
                expected_en_docstring,  # First call returns English docstring
                expected_vi_docstring   # Second call returns Vietnamese translation
            ]
            
            # Act
            result = await agent._generate_docstring(
                mock_snippet.text_content,
                mock_snippet.symbol_type,
                mock_snippet.symbol_name
            )
            
            # Assert
            assert result is not None
            assert result["en"] == expected_en_docstring
            assert result["vi"] == expected_vi_docstring
            assert mock_api.call_count == 2  # Called twice: once for English, once for Vietnamese

    @pytest.mark.asyncio
    async def test_generate_docstring_error(self, agent, mock_snippet):
        """Test error handling in docstring generation."""
        # Arrange
        with patch.object(agent, '_call_openrouter_api', side_effect=ValueError("API Error")) as mock_api:
            
            # Act
            result = await agent._generate_docstring(
                mock_snippet.text_content,
                mock_snippet.symbol_type,
                mock_snippet.symbol_name
            )
            
            # Assert
            assert result is not None
            assert "Docstring for test_function" in result["en"]
            assert "Docstring cho test_function" in result["vi"]
            mock_api.assert_called_once()  # Should have attempted to call the API

    @pytest.mark.asyncio
    async def test_call_openrouter_api(self, agent):
        """Test the OpenRouter API call with mocks."""
        # Arrange
        prompt = "Test prompt"
        system_message = "Test system message"
        expected_response = "Test API response"
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps({
            "choices": [{
                "message": {
                    "content": expected_response
                }
            }]
        }))
        
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        # Act
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await agent._call_openrouter_api(prompt, system_message)
        
        # Assert
        assert result == expected_response
        
        # Verify API call parameters
        args, kwargs = mock_session.post.call_args
        assert args[0] == "https://openrouter.ai/api/v1/chat/completions"
        assert kwargs["json"]["model"] == agent.config.summarizer_model_name
        assert kwargs["json"]["messages"][0]["role"] == "system"
        assert kwargs["json"]["messages"][0]["content"] == system_message
        assert kwargs["json"]["messages"][1]["role"] == "user"
        assert kwargs["json"]["messages"][1]["content"] == prompt

    @pytest.mark.asyncio
    async def test_call_openrouter_api_error(self, agent):
        """Test the OpenRouter API call error handling."""
        # Arrange
        prompt = "Test prompt"
        system_message = "Test system message"
        
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.post.return_value.__aenter__.return_value.status = 400
        mock_session.post.return_value.__aenter__.return_value.text = AsyncMock(return_value=json.dumps({
            "error": {
                "type": "invalid_request_error",
                "message": "API Error"
            }
        }))
        
        # Act & Assert
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ValueError) as excinfo:
                await agent._call_openrouter_api(prompt, system_message)
            
            assert "API" in str(excinfo.value)
