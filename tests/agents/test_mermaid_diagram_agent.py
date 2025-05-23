"""
Unit tests for MermaidDiagramAgent.

This module tests the functionality of the MermaidDiagramAgent, including:
- Generating module dependency diagrams
- Generating class diagrams
- Generating function flow diagrams
- Generating architectural diagrams
- Error handling and retry logic
"""

import pytest
import os
import re
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from autodocai.agents.mermaid_diagram_agent import MermaidDiagramAgent
from autodocai.schemas import MessageType, CodeSnippet, ParsedModule, ParsedClass, ParsedFunction


class TestMermaidDiagramAgent:
    """Tests for the MermaidDiagramAgent class."""

    @pytest.fixture
    def agent(self, mock_config):
        """Create a MermaidDiagramAgent instance for testing."""
        return MermaidDiagramAgent(mock_config)

    @pytest.mark.asyncio
    async def test_execute_no_data(self, agent):
        """Test execute method with no data."""
        # Arrange
        state = {"messages": []}

        # Act
        result = await agent._execute(state)

        # Assert
        assert "diagrams" not in result
        assert any(m.message_type == MessageType.WARNING for m in result["messages"])

    @pytest.mark.asyncio
    async def test_execute_with_data(self, agent, mock_snippet, mock_module, sample_workflow_state):
        """Test execute method with data."""
        # Arrange
        state = sample_workflow_state.copy()
        state["snippets"] = [mock_snippet]
        state["modules"] = [mock_module]

        # Mock the diagram generation methods
        with patch.object(agent, '_generate_module_dependency_diagram', return_value="```mermaid\ngraph TD\nA-->B\n```") as mock_module_diagram, \
             patch.object(agent, '_generate_class_diagrams', return_value={"class_test": "```mermaid\nclassDiagram\nClass1\n```"}) as mock_class_diagrams, \
             patch.object(agent, '_generate_function_flow_diagrams', return_value={"flow_test": "```mermaid\nflowchart TD\nA-->B\n```"}) as mock_flow_diagrams, \
             patch.object(agent, '_generate_architectural_diagram', return_value="```mermaid\ngraph TD\nX-->Y\n```") as mock_arch_diagram:

            # Act
            result = await agent._execute(state)

            # Assert
            assert "diagrams" in result
            assert len(result["diagrams"]) == 4
            assert "module_dependencies" in result["diagrams"]
            assert "architecture" in result["diagrams"]
            assert "class_test" in result["diagrams"]
            assert "flow_test" in result["diagrams"]
            
            # Verify all methods were called
            mock_module_diagram.assert_called_once()
            mock_class_diagrams.assert_called_once()
            mock_flow_diagrams.assert_called_once()
            mock_arch_diagram.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_module_dependency_diagram(self, agent, mock_module):
        """Test generation of module dependency diagram."""
        # Arrange
        modules = [mock_module]
        
        # Add another module with a dependency on the first one
        from autodocai.schemas import Import
        second_module = ParsedModule(
            file_path="second_module.py",
            imports=[
                Import(module="test_module", name="test_module", alias=None)
            ],
            classes=[],
            functions=[],
            docstring="",
            code="# Second module\nimport test_module\n\n# Module content"
        )
        modules.append(second_module)

        # Act
        diagram = await agent._generate_module_dependency_diagram(modules)

        # Assert
        assert diagram is not None
        assert "```mermaid" in diagram
        assert "graph TD" in diagram
        assert "second_module" in diagram
        assert "test_module" in diagram

    @pytest.mark.asyncio
    async def test_generate_class_diagrams(self, agent):
        """Test generation of class diagrams."""
        # Arrange
        # Create a module with classes
        module = ParsedModule(
            file_path="test_module.py",
            imports=[],
            classes=[
                ParsedClass(
                    name="TestClass",
                    methods=[
                        ParsedFunction(
                            name="test_method",
                            docstring="Test method docstring",
                            params=[],
                            code="def test_method(self, param):\n    return param",
                            start_line=1,
                            end_line=2
                        )
                    ],
                    docstring="Test class docstring",
                    base_classes=[],
                    code="class TestClass:\n    def test_method(self, param):\n        return param",
                    start_line=1,
                    end_line=3
                )
            ],
            functions=[],
            docstring="",
            code="# This is a test module\n\nclass TestClass:\n    def test_method(self, param):\n        return param"
        )
        modules = [module]

        # Act
        diagrams = await agent._generate_class_diagrams(modules)

        # Assert
        assert diagrams is not None
        assert len(diagrams) == 1
        assert "class_test_module" in diagrams
        assert "```mermaid" in diagrams["class_test_module"]
        assert "classDiagram" in diagrams["class_test_module"]
        assert "TestClass" in diagrams["class_test_module"]

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
        
        # Verify timeout is set correctly
        assert kwargs["timeout"].total == 60

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
            
            assert "API error" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_call_openrouter_api_rate_limit(self, agent):
        """Test the OpenRouter API rate limit handling."""
        # Arrange
        prompt = "Test prompt"
        system_message = "Test system message"
        
        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.post.return_value.__aenter__.return_value.status = 429
        mock_session.post.return_value.__aenter__.return_value.text = AsyncMock(return_value=json.dumps({
            "error": {
                "type": "rate_limit_exceeded",
                "message": "Rate limit exceeded"
            }
        }))
        
        # Act & Assert
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ValueError) as excinfo:
                await agent._call_openrouter_api(prompt, system_message)
            
            assert "Rate limit exceeded" in str(excinfo.value)
            
    @pytest.mark.asyncio
    async def test_should_retry_exception(self):
        """Test the retry exception function."""
        # Arrange & Act & Assert
        import aiohttp
        import asyncio
        
        # Should retry network errors
        assert MermaidDiagramAgent._should_retry_exception(aiohttp.ClientError())
        assert MermaidDiagramAgent._should_retry_exception(asyncio.TimeoutError())
        
        # Should retry rate limits and server errors
        assert MermaidDiagramAgent._should_retry_exception(ValueError("rate limit exceeded"))
        assert MermaidDiagramAgent._should_retry_exception(ValueError("status 429"))
        assert MermaidDiagramAgent._should_retry_exception(ValueError("status 500"))
        
        # Should not retry other errors
        assert not MermaidDiagramAgent._should_retry_exception(ValueError("Invalid input"))
        assert not MermaidDiagramAgent._should_retry_exception(KeyError())

    @pytest.mark.asyncio
    async def test_generate_function_flow_with_ai(self, agent, mock_snippet):
        """Test generating function flow diagram with AI."""
        # Arrange
        # Create a diagram with more content to pass the validation check (length > 30 and contains 'graph')
        diagram_content = "graph TD\nA[Start] --> B[Process Input]\nB --> C{Valid Input?}\nC -->|Yes| D[Process Data]\nC -->|No| E[Handle Error]\nD --> F[Return Result]\nE --> F\nF --> G[End]"
        expected_diagram = f"```mermaid\n{diagram_content}\n```"
        
        # Act
        # Create a response that matches the expected format exactly
        api_response = f"Here's the diagram for the function:\n\n{expected_diagram}"
        with patch.object(agent, '_call_openrouter_api', return_value=api_response) as mock_api:
            result = await agent._generate_function_flow_with_ai(mock_snippet)
        
        # Assert
        assert result is not None
        assert expected_diagram in result
        mock_api.assert_called_once()
        
        # Check if the prompt contains the function name and code
        args, kwargs = mock_api.call_args
        assert mock_snippet.symbol_name in args[0]
        assert mock_snippet.text_content in args[0]

    @pytest.mark.asyncio
    async def test_generate_architectural_diagram(self, agent, sample_workflow_state):
        """Test generating architectural diagram."""
        # Arrange
        expected_diagram = "```mermaid\ngraph TD\nA[Component A]-->B[Component B]\nB-->C[Component C]\n```"
        
        # Act
        with patch.object(agent, '_call_openrouter_api', return_value=f"Here's the architecture: {expected_diagram}") as mock_api:
            result = await agent._generate_architectural_diagram(sample_workflow_state)
        
        # Assert
        assert result is not None
        assert expected_diagram in result
        mock_api.assert_called_once()
        
        # Check if the prompt contains the architectural overview
        args, kwargs = mock_api.call_args
        assert "architectural_overview" in sample_workflow_state["rag_results"]
        assert sample_workflow_state["rag_results"]["architectural_overview"]["en"] in args[0]

    def test_sanitize_id(self, agent):
        """Test the ID sanitization function."""
        # Arrange
        test_cases = [
            ("Normal Name", "Normal_Name"),
            ("name-with-hyphens", "name_with_hyphens"),
            ("123starts_with_number", "n123starts_with_number"),
            ("special!@#chars", "special___chars"),
            ("", ""),
            ("a b c", "a_b_c")
        ]
        
        # Act & Assert
        for input_text, expected_output in test_cases:
            assert agent._sanitize_id(input_text) == expected_output

# Mock Import class for testing
class Import:
    def __init__(self, module, name, alias):
        self.module = module
        self.name = name
        self.alias = alias
