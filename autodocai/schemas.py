"""
Schemas for AutoDoc AI.

This module defines the validation schemas for data structures used in the application,
ensuring data integrity and proper typing across the application.
"""

from enum import Enum
from typing import Dict, List, Optional, TypedDict, Union

from pydantic import BaseModel, Field, validator


# Define MessageType enum
class MessageType(str, Enum):
    """Type of agent message for logging and display."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


# Define CodeSnippet class
class CodeSnippet(BaseModel):
    """Code snippet extracted from the codebase."""
    id: str
    file_path: str
    start_line: int
    end_line: int
    text_content: str
    symbol_type: str  # Enum values: function, class, method, module, other
    language: str
    symbol_name: Optional[str] = None
    original_docstring: Optional[str] = None
    enhanced_docstring: Optional[Dict[str, str]] = None  # Language code -> docstring
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"


# Define ProcessingResult class
class ProcessingResult(BaseModel):
    """Result of the documentation generation process."""
    success: bool
    repo_url: str
    docs_url: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    files_processed: Optional[int] = None
    snippets_extracted: Optional[int] = None
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"


# Define RepositoryInfo class
class RepositoryInfo(BaseModel):
    """Information about a GitHub repository."""
    name: str
    url: str
    local_path: str
    default_branch: str
    languages: List[str]
    description: Optional[str] = None
    is_private: bool
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"


# Define AgentMessage class
class AgentMessage(BaseModel):
    """Message from an agent for logging and display."""
    agent_name: str
    message_type: MessageType
    content: str
    timestamp: str
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"

# Define FunctionParameter class
class FunctionParameter(BaseModel):
    """Parameter of a function or method."""
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"


# Define ParsedFunction class
class ParsedFunction(BaseModel):
    """Function parsed from code."""
    name: str
    docstring: Optional[str] = None
    params: List[FunctionParameter] = Field(default_factory=list)
    return_type: Optional[str] = None
    code: str
    start_line: int
    end_line: int
    is_async: bool = False
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"


# Define ClassProperty class
class ClassProperty(BaseModel):
    """Property of a class."""
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"


# Define ParsedClass class
class ParsedClass(BaseModel):
    """Class parsed from code."""
    name: str
    docstring: Optional[str] = None
    base_classes: List[str] = Field(default_factory=list)
    methods: List[ParsedFunction] = Field(default_factory=list)
    properties: List[ClassProperty] = Field(default_factory=list)
    code: str
    start_line: int
    end_line: int
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"


# Define Import class
class Import(BaseModel):
    """Import statement parsed from code."""
    module: str
    name: Optional[str] = None
    alias: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"


# Define ParsedModule class
class ParsedModule(BaseModel):
    """Module parsed from code."""
    file_path: str
    docstring: Optional[str] = None
    imports: List[Import] = Field(default_factory=list)
    functions: List[ParsedFunction] = Field(default_factory=list)
    classes: List[ParsedClass] = Field(default_factory=list)
    code: str
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"

# Define Pydantic models for easy integration with Python code

class CodeSnippet(BaseModel):
    """A code snippet extracted from a repository."""
    
    id: str
    file_path: str
    start_line: int
    end_line: int
    text_content: str
    symbol_name: Optional[str] = None
    symbol_type: str
    language: str
    original_docstring: Optional[str] = None
    ai_summary_en: Optional[str] = None
    ai_summary_vi: Optional[str] = None


class ProcessingResult(BaseModel):
    """Result of the documentation generation process."""
    
    success: bool
    repo_url: str
    docs_url: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    files_processed: Optional[int] = None
    snippets_extracted: Optional[int] = None


class RepositoryInfo(BaseModel):
    """Information about a cloned repository."""
    
    name: str
    url: str
    local_path: str
    default_branch: str
    languages: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    is_private: bool = False


class MessageType(str, Enum):
    """Types of messages from agents."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class AgentMessage(BaseModel):
    """Message from an agent in the system."""
    
    agent_name: str
    message_type: MessageType
    content: str
    timestamp: str


class FunctionParam(BaseModel):
    """Parameter of a function."""
    
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None


class ParsedFunction(BaseModel):
    """A function extracted from code analysis."""
    
    name: str
    docstring: Optional[str] = None
    params: List[FunctionParam] = Field(default_factory=list)
    return_type: Optional[str] = None
    code: str
    start_line: int
    end_line: int
    is_async: bool = False


class ClassAttribute(BaseModel):
    """Attribute of a class."""
    
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None


class ParsedClass(BaseModel):
    """A class extracted from code analysis."""
    
    name: str
    docstring: Optional[str] = None
    base_classes: List[str] = Field(default_factory=list)
    methods: List[ParsedFunction] = Field(default_factory=list)
    attributes: List[ClassAttribute] = Field(default_factory=list)
    code: str
    start_line: int
    end_line: int


class Import(BaseModel):
    """An import statement in a module."""
    
    module: str
    name: Optional[str] = None
    alias: Optional[str] = None


class ParsedModule(BaseModel):
    """A module extracted from code analysis."""
    
    file_path: str
    docstring: Optional[str] = None
    imports: List[Import] = Field(default_factory=list)
    functions: List[ParsedFunction] = Field(default_factory=list)
    classes: List[ParsedClass] = Field(default_factory=list)
    code: str
