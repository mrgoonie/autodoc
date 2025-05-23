"""
Python code parser for AutoDoc AI.

This module handles parsing and analysis of Python source code using the ast module.
It extracts code structure, docstrings, functions, classes, and other relevant information.
"""

import ast
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from autodocai.schemas import (
    ClassAttribute,
    FunctionParam,
    Import,
    ParsedClass,
    ParsedFunction,
    ParsedModule,
)


class DocstringExtractor(ast.NodeVisitor):
    """AST visitor to extract docstrings from Python modules, classes, and functions."""
    
    def __init__(self):
        """Initialize the docstring extractor."""
        self.docstrings = {}
    
    def visit_Module(self, node: ast.Module) -> None:
        """Extract module-level docstring."""
        if ast.get_docstring(node):
            self.docstrings["module"] = ast.get_docstring(node)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class docstring."""
        if ast.get_docstring(node):
            self.docstrings[f"class:{node.name}"] = ast.get_docstring(node)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract function docstring."""
        if ast.get_docstring(node):
            self.docstrings[f"function:{node.name}"] = ast.get_docstring(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Extract async function docstring."""
        if ast.get_docstring(node):
            self.docstrings[f"async_function:{node.name}"] = ast.get_docstring(node)
        self.generic_visit(node)


class PythonCodeParser:
    """Parser for Python code using the ast module.
    
    This class analyzes Python source code and extracts structured information about
    modules, classes, functions, and other code elements.
    """
    
    def __init__(self, file_path: str):
        """Initialize the Python code parser.
        
        Args:
            file_path: Path to the Python file to parse
        """
        self.file_path = file_path
        self.code = ""
        self.tree = None
        self.docstrings = {}
        self.line_mapping = {}
    
    def parse(self) -> ParsedModule:
        """Parse the Python file and extract its structure.
        
        Returns:
            ParsedModule: Structured information about the Python module
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            SyntaxError: If the Python code has syntax errors
            ValueError: For other parsing errors
        """
        try:
            # Read the file content
            with open(self.file_path, "r", encoding="utf-8") as file:
                self.code = file.read()
            
            # Create line mapping for accurate line numbers
            self._create_line_mapping()
            
            # Parse the code into an AST
            self.tree = ast.parse(self.code, filename=self.file_path)
            
            # Extract docstrings
            docstring_extractor = DocstringExtractor()
            docstring_extractor.visit(self.tree)
            self.docstrings = docstring_extractor.docstrings
            
            # Extract module-level components
            imports = self._extract_imports()
            functions = self._extract_functions()
            classes = self._extract_classes()
            
            # Create the parsed module
            module_docstring = self.docstrings.get("module")
            
            return ParsedModule(
                file_path=self.file_path,
                docstring=module_docstring,
                imports=imports,
                functions=functions,
                classes=classes,
                code=self.code,
            )
            
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.file_path}")
        except SyntaxError as e:
            raise SyntaxError(f"Syntax error in {self.file_path}: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing {self.file_path}: {str(e)}")
    
    def _create_line_mapping(self) -> None:
        """Create a mapping of line positions to line numbers."""
        lines = self.code.split("\n")
        position = 0
        
        for i, line in enumerate(lines):
            self.line_mapping[position] = i + 1
            position += len(line) + 1  # +1 for the newline character
    
    def _get_line_number(self, node: ast.AST) -> int:
        """Get the line number for a node.
        
        Args:
            node: AST node
            
        Returns:
            int: Line number
        """
        # Use lineno attribute if available
        if hasattr(node, "lineno"):
            return node.lineno
        
        # Fall back to line mapping for more accurate positioning
        if hasattr(node, "col_offset"):
            positions = sorted(self.line_mapping.keys())
            for pos in positions:
                if pos > node.col_offset:
                    return self.line_mapping[positions[positions.index(pos) - 1]]
        
        return 0
    
    def _extract_imports(self) -> List[Import]:
        """Extract import statements from the module.
        
        Returns:
            List[Import]: List of import statements
        """
        imports = []
        
        for node in ast.walk(self.tree):
            # Handle 'import module' statements
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(
                        Import(
                            module=name.name,
                            alias=name.asname,
                        )
                    )
            
            # Handle 'from module import name' statements
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module if node.module else ""
                for name in node.names:
                    imports.append(
                        Import(
                            module=module_name,
                            name=name.name,
                            alias=name.asname,
                        )
                    )
        
        return imports
    
    def _extract_param_type_and_default(
        self, param: ast.arg, defaults: List[ast.expr], i: int, num_args: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract parameter type hint and default value.
        
        Args:
            param: AST parameter node
            defaults: List of default values
            i: Parameter index
            num_args: Total number of parameters
            
        Returns:
            Tuple[Optional[str], Optional[str]]: Type hint and default value
        """
        # Extract type annotation if available
        type_hint = None
        if param.annotation:
            type_hint = ast.unparse(param.annotation)
        
        # Extract default value if available
        default_value = None
        default_offset = num_args - len(defaults)
        if i >= default_offset and defaults:
            default_index = i - default_offset
            if default_index < len(defaults):
                default_value = ast.unparse(defaults[default_index])
        
        return type_hint, default_value
    
    def _extract_function_params(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> List[FunctionParam]:
        """Extract function parameters.
        
        Args:
            node: Function definition node
            
        Returns:
            List[FunctionParam]: List of function parameters
        """
        params = []
        args = node.args
        
        # Process positional arguments
        defaults = args.defaults if hasattr(args, "defaults") else []
        num_args = len(args.args)
        
        for i, arg in enumerate(args.args):
            # Skip 'self' and 'cls' parameters in methods
            if i == 0 and arg.arg in ("self", "cls") and isinstance(node.parent, ast.ClassDef):
                continue
                
            type_hint, default_value = self._extract_param_type_and_default(
                arg, defaults, i, num_args
            )
            
            params.append(
                FunctionParam(
                    name=arg.arg,
                    type_hint=type_hint,
                    default_value=default_value,
                )
            )
        
        # Process keyword-only arguments
        kw_defaults = args.kw_defaults if hasattr(args, "kw_defaults") else []
        num_kw_args = len(args.kwonlyargs)
        
        for i, arg in enumerate(args.kwonlyargs):
            type_hint, default_value = self._extract_param_type_and_default(
                arg, kw_defaults, i, num_kw_args
            )
            
            params.append(
                FunctionParam(
                    name=arg.arg,
                    type_hint=type_hint,
                    default_value=default_value,
                )
            )
        
        # Handle *args
        if args.vararg:
            params.append(
                FunctionParam(
                    name=f"*{args.vararg.arg}",
                    type_hint=ast.unparse(args.vararg.annotation) if args.vararg.annotation else None,
                )
            )
        
        # Handle **kwargs
        if args.kwarg:
            params.append(
                FunctionParam(
                    name=f"**{args.kwarg.arg}",
                    type_hint=ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None,
                )
            )
        
        return params
    
    def _extract_functions(self) -> List[ParsedFunction]:
        """Extract functions from the module.
        
        Returns:
            List[ParsedFunction]: List of functions
        """
        functions = []
        
        # Find all function definitions at the module level
        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip methods (handled in class extraction)
                if isinstance(node.parent, ast.ClassDef):
                    continue
                
                # Add parent reference for parameter extraction
                node.parent = self.tree
                
                # Extract function information
                function = self._process_function_node(node)
                functions.append(function)
        
        return functions
    
    def _process_function_node(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> ParsedFunction:
        """Process a function definition node.
        
        Args:
            node: Function definition node
            
        Returns:
            ParsedFunction: Parsed function information
        """
        # Get function name
        name = node.name
        
        # Get docstring
        docstring = None
        if isinstance(node, ast.FunctionDef):
            docstring_key = f"function:{name}"
        else:
            docstring_key = f"async_function:{name}"
            
        docstring = self.docstrings.get(docstring_key)
        
        # Get return type hint
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)
        
        # Get function parameters
        params = self._extract_function_params(node)
        
        # Get function code
        start_line = node.lineno
        end_line = 0
        
        # Find the last line of the function
        for child in ast.walk(node):
            if hasattr(child, "lineno"):
                end_line = max(end_line, child.lineno)
        
        # Ensure we include the final line with potential decorations
        end_line = max(end_line + 1, start_line + 1)
        
        # Extract the function code
        lines = self.code.split("\n")
        code_lines = lines[start_line - 1:end_line]
        code = "\n".join(code_lines)
        
        # Check if function is async
        is_async = isinstance(node, ast.AsyncFunctionDef)
        
        return ParsedFunction(
            name=name,
            docstring=docstring,
            params=params,
            return_type=return_type,
            code=code,
            start_line=start_line,
            end_line=end_line,
            is_async=is_async,
        )
    
    def _extract_classes(self) -> List[ParsedClass]:
        """Extract classes from the module.
        
        Returns:
            List[ParsedClass]: List of classes
        """
        classes = []
        
        # Find all class definitions at the module level
        for node in ast.iter_child_nodes(self.tree):
            if isinstance(node, ast.ClassDef):
                # Extract class information
                class_info = self._process_class_node(node)
                classes.append(class_info)
        
        return classes
    
    def _process_class_node(self, node: ast.ClassDef) -> ParsedClass:
        """Process a class definition node.
        
        Args:
            node: Class definition node
            
        Returns:
            ParsedClass: Parsed class information
        """
        # Get class name
        name = node.name
        
        # Get docstring
        docstring = self.docstrings.get(f"class:{name}")
        
        # Get base classes
        base_classes = []
        for base in node.bases:
            base_classes.append(ast.unparse(base))
        
        # Get class methods
        methods = []
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Add parent reference for parameter extraction
                child.parent = node
                method = self._process_function_node(child)
                methods.append(method)
        
        # Get class attributes
        attributes = self._extract_class_attributes(node)
        
        # Get class code
        start_line = node.lineno
        end_line = 0
        
        # Find the last line of the class
        for child in ast.walk(node):
            if hasattr(child, "lineno"):
                end_line = max(end_line, child.lineno)
        
        # Ensure we include the final line
        end_line = max(end_line + 1, start_line + 1)
        
        # Extract the class code
        lines = self.code.split("\n")
        code_lines = lines[start_line - 1:end_line]
        code = "\n".join(code_lines)
        
        return ParsedClass(
            name=name,
            docstring=docstring,
            base_classes=base_classes,
            methods=methods,
            attributes=attributes,
            code=code,
            start_line=start_line,
            end_line=end_line,
        )
    
    def _extract_class_attributes(self, node: ast.ClassDef) -> List[ClassAttribute]:
        """Extract class attributes.
        
        Args:
            node: Class definition node
            
        Returns:
            List[ClassAttribute]: List of class attributes
        """
        attributes = []
        
        # Find attribute assignments in the class body
        for child in node.body:
            # Class variable assignment
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        # Skip private attributes (starting with _)
                        if target.id.startswith("_") and not target.id.startswith("__"):
                            continue
                            
                        attributes.append(
                            ClassAttribute(
                                name=target.id,
                                default_value=ast.unparse(child.value),
                            )
                        )
            
            # Annotated assignment
            elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                # Skip private attributes
                if child.target.id.startswith("_") and not child.target.id.startswith("__"):
                    continue
                    
                attributes.append(
                    ClassAttribute(
                        name=child.target.id,
                        type_hint=ast.unparse(child.annotation),
                        default_value=ast.unparse(child.value) if child.value else None,
                    )
                )
        
        # Find attributes defined in __init__ method
        init_method = None
        for child in node.body:
            if isinstance(child, ast.FunctionDef) and child.name == "__init__":
                init_method = child
                break
        
        if init_method:
            self_assigns = set()
            
            # Find self.attribute = value assignments in __init__
            for child in ast.walk(init_method):
                if (
                    isinstance(child, ast.Assign)
                    and len(child.targets) == 1
                    and isinstance(child.targets[0], ast.Attribute)
                    and isinstance(child.targets[0].value, ast.Name)
                    and child.targets[0].value.id == "self"
                ):
                    attr_name = child.targets[0].attr
                    
                    # Skip private attributes and duplicates
                    if (attr_name.startswith("_") and not attr_name.startswith("__")) or attr_name in self_assigns:
                        continue
                        
                    self_assigns.add(attr_name)
                    attributes.append(
                        ClassAttribute(
                            name=attr_name,
                            default_value=ast.unparse(child.value),
                        )
                    )
                
                # Look for type annotations in __init__
                elif (
                    isinstance(child, ast.AnnAssign)
                    and isinstance(child.target, ast.Attribute)
                    and isinstance(child.target.value, ast.Name)
                    and child.target.value.id == "self"
                ):
                    attr_name = child.target.attr
                    
                    # Skip private attributes and duplicates
                    if (attr_name.startswith("_") and not attr_name.startswith("__")) or attr_name in self_assigns:
                        continue
                        
                    self_assigns.add(attr_name)
                    attributes.append(
                        ClassAttribute(
                            name=attr_name,
                            type_hint=ast.unparse(child.annotation),
                            default_value=ast.unparse(child.value) if child.value else None,
                        )
                    )
        
        return attributes


def parse_module(file_path: str) -> ParsedModule:
    """Parse a Python module and extract its structure.
    
    This is a convenience function that creates a PythonCodeParser and uses it
    to parse the specified file.
    
    Args:
        file_path: Path to the Python file to parse
        
    Returns:
        ParsedModule: Structured information about the Python module
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        SyntaxError: If the Python code has syntax errors
        ValueError: For other parsing errors
    """
    parser = PythonCodeParser(file_path)
    return parser.parse()


def is_python_file(file_path: str) -> bool:
    """Check if a file is a Python file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        bool: True if the file is a Python file, False otherwise
    """
    # Check file extension
    if file_path.endswith(".py"):
        return True
    
    # Check file content (shebang)
    try:
        with open(file_path, "rb") as f:
            first_line = f.readline().decode("utf-8", errors="ignore").strip()
            if first_line.startswith("#!") and "python" in first_line.lower():
                return True
    except (IOError, UnicodeDecodeError):
        pass
    
    return False


def extract_all_docstrings(python_code: str) -> Dict[str, str]:
    """Extract all docstrings from Python code.
    
    Args:
        python_code: Python source code
        
    Returns:
        Dict[str, str]: Dictionary of docstrings keyed by scope
        
    Raises:
        SyntaxError: If the Python code has syntax errors
    """
    tree = ast.parse(python_code)
    extractor = DocstringExtractor()
    extractor.visit(tree)
    return extractor.docstrings


def find_python_files(directory: str, exclude_dirs: Optional[List[str]] = None) -> List[str]:
    """Find all Python files in a directory.
    
    Args:
        directory: Directory to search
        exclude_dirs: List of directories to exclude
        
    Returns:
        List[str]: List of Python file paths
    """
    if exclude_dirs is None:
        exclude_dirs = ["venv", ".venv", "env", ".env", "__pycache__", ".git", ".github", "node_modules"]
    
    python_files = []
    
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    
    return python_files
