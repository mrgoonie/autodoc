"""
Pytest configuration for AutoDoc AI tests.

This module provides fixtures and common utilities for all tests.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from autodocai.config import AppConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = AppConfig(
        target_repo_url="https://github.com/test/repo",
        output_dir="/tmp/autodoc_test",
        qdrant_url="http://localhost:6333",
        github_pat="fake_token",
        output_languages=["EN", "VI"],
        openrouter_api_key="fake_api_key",
        sendgrid_api_key="fake_sendgrid_key",
        sendgrid_from_email="test@example.com",
        notification_email_to="user@example.com",
        summarizer_model_name="openai/gpt-4-turbo",
        rag_model_name="openai/gpt-4-turbo",
        log_level="INFO"
    )
    return config


@pytest.fixture
def mock_snippet():
    """Create a mock code snippet for testing."""
    from autodocai.schemas import CodeSnippet
    
    return CodeSnippet(
        id="test_snippet_1",
        file_path="test_module.py",
        symbol_type="function",
        symbol_name="test_function",
        language="python",
        start_line=1,
        end_line=10,
        text_content="""def test_function(param1, param2):
    \"\"\"This is a test function.
    
    Args:
        param1: First parameter
        param2: Second parameter
        
    Returns:
        bool: Result of the operation
    \"\"\"
    # Process the parameters
    result = param1 + param2
    return result > 0""",
        original_docstring="""This is a test function.
    
    Args:
        param1: First parameter
        param2: Second parameter
        
    Returns:
        bool: Result of the operation"""
    )


@pytest.fixture
def mock_module():
    """Create a mock module for testing."""
    from autodocai.schemas import ParsedModule, Import
    
    return ParsedModule(
        file_path="test_module.py",
        imports=[
            Import(module="os", name="os", alias=None),
            Import(module="sys", name="sys", alias=None),
            Import(module="mydep", name="mydep", alias="my_dependency"),
            Import(module="myproject.utils", name="utils", alias=None)
        ],
        classes=[],
        functions=[],
        docstring="This is a test module.",
        code="""
# This is test module code
import os
import sys
import mydep as my_dependency
from myproject.utils import utils

# Module content
"""
    )


@pytest.fixture
def sample_workflow_state():
    """Create a sample workflow state for testing."""
    return {
        "repo_info": {
            "name": "test-repo",
            "url": "https://github.com/test/repo",
            "description": "A test repository",
            "default_branch": "main",
            "languages": ["Python", "JavaScript"]
        },
        "snippets": [],
        "modules": [],
        "summaries": {},
        "diagrams": {},
        "rag_results": {
            "architectural_overview": {
                "en": "This is a test architecture with components A, B, and C. Component A calls B, which calls C.",
                "vi": "Đây là kiến trúc thử nghiệm với các thành phần A, B và C. Thành phần A gọi B, sau đó gọi C."
            }
        },
        "messages": []
    }
