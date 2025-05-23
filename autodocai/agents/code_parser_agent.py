"""
Code parser agent for AutoDoc AI.

This agent is responsible for parsing and analyzing code from a repository,
extracting functions, classes, and other relevant information for documentation.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from autodocai.agents.base import BaseAgent
from autodocai.code_parser import PythonCodeParser, find_python_files, is_python_file
from autodocai.schemas import CodeSnippet, MessageType, ParsedModule


class CodeParserAgent(BaseAgent):
    """Agent for parsing and analyzing code.
    
    This agent analyzes code files in the repository, extracting structured
    information about functions, classes, methods, and other code elements.
    Currently focuses on Python code with plans to expand to other languages.
    """
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the code parsing process.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict[str, Any]: Updated workflow state with parsed code information
        """
        # Get repository information from state
        repo_info = state.get("repo_info")
        if not repo_info:
            raise ValueError("Repository information is missing")
        
        repo_path = repo_info.local_path
        self.logger.info(f"Starting code analysis for repository: {repo_path}")
        
        # Initialize results
        modules = []
        snippets = []
        files_processed = 0
        
        # Check if the repository contains Python code
        if "Python" in repo_info.languages:
            # Find Python files
            python_files = find_python_files(repo_path)
            self.logger.info(f"Found {len(python_files)} Python files")
            self._add_message(state, MessageType.INFO, f"Found {len(python_files)} Python files")
            
            # Process each Python file
            for file_path in python_files:
                try:
                    # Parse the file
                    self.logger.debug(f"Parsing file: {file_path}")
                    parser = PythonCodeParser(file_path)
                    module = parser.parse()
                    
                    # Add module to results
                    modules.append(module)
                    
                    # Extract code snippets from the module
                    file_snippets = self._extract_snippets(module, repo_path)
                    snippets.extend(file_snippets)
                    
                    files_processed += 1
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing file {file_path}: {str(e)}")
                    self._add_message(
                        state, 
                        MessageType.WARNING, 
                        f"Error parsing file {os.path.relpath(file_path, repo_path)}: {str(e)}"
                    )
        
        # Add parsed information to state
        state["modules"] = modules
        state["snippets"] = snippets
        state["files_processed"] = files_processed
        state["snippets_extracted"] = len(snippets)
        
        self.logger.info(
            f"Completed code analysis: {files_processed} files processed, {len(snippets)} snippets extracted"
        )
        self._add_message(
            state, 
            MessageType.SUCCESS, 
            f"Completed code analysis: {files_processed} files processed, {len(snippets)} snippets extracted"
        )
        
        return state
    
    def _extract_snippets(self, module: ParsedModule, repo_path: str) -> List[CodeSnippet]:
        """Extract code snippets from a parsed module.
        
        Args:
            module: Parsed module information
            repo_path: Root path of the repository
            
        Returns:
            List[CodeSnippet]: List of code snippets
        """
        snippets = []
        relative_path = os.path.relpath(module.file_path, repo_path)
        
        # Add module-level snippet
        if module.docstring:
            module_snippet = CodeSnippet(
                id=f"module:{relative_path}",
                file_path=relative_path,
                start_line=1,
                end_line=len(module.code.split("\n")),
                text_content=module.code,
                symbol_name=os.path.basename(module.file_path).replace(".py", ""),
                symbol_type="module",
                language="python",
                original_docstring=module.docstring
            )
            snippets.append(module_snippet)
        
        # Add function snippets
        for func in module.functions:
            func_snippet = CodeSnippet(
                id=f"function:{relative_path}:{func.name}",
                file_path=relative_path,
                start_line=func.start_line,
                end_line=func.end_line,
                text_content=func.code,
                symbol_name=func.name,
                symbol_type="function",
                language="python",
                original_docstring=func.docstring
            )
            snippets.append(func_snippet)
        
        # Add class snippets
        for cls in module.classes:
            # Add class snippet
            class_snippet = CodeSnippet(
                id=f"class:{relative_path}:{cls.name}",
                file_path=relative_path,
                start_line=cls.start_line,
                end_line=cls.end_line,
                text_content=cls.code,
                symbol_name=cls.name,
                symbol_type="class",
                language="python",
                original_docstring=cls.docstring
            )
            snippets.append(class_snippet)
            
            # Add method snippets
            for method in cls.methods:
                method_snippet = CodeSnippet(
                    id=f"method:{relative_path}:{cls.name}.{method.name}",
                    file_path=relative_path,
                    start_line=method.start_line,
                    end_line=method.end_line,
                    text_content=method.code,
                    symbol_name=f"{cls.name}.{method.name}",
                    symbol_type="method",
                    language="python",
                    original_docstring=method.docstring
                )
                snippets.append(method_snippet)
        
        return snippets
