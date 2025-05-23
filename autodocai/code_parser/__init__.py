"""
Code parser module for AutoDoc AI.

This package handles code parsing and analysis for different programming languages.
Initially focused on Python with plans to expand to other languages.
"""

from autodocai.code_parser.python_parser import (
    PythonCodeParser, 
    parse_module, 
    find_python_files, 
    is_python_file,
    extract_all_docstrings
)

__all__ = [
    "PythonCodeParser", 
    "parse_module", 
    "find_python_files", 
    "is_python_file",
    "extract_all_docstrings"
]
