"""
Mermaid diagram agent for AutoDoc AI.

This agent generates Mermaid.js diagrams for visualizing code structure,
dependencies, and flows in the Docusaurus documentation.
"""

import logging
import os
import re
import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple
import json

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_exception, wait_random_exponential

from autodocai.agents.base import BaseAgent
from autodocai.schemas import CodeSnippet, MessageType, ParsedClass, ParsedFunction, ParsedModule


class MermaidDiagramAgent(BaseAgent):
    """Agent for generating Mermaid.js diagrams.
    
    This agent analyzes code structure and relationships to create diagrams 
    that visualize code architecture, dependencies, and flows using Mermaid.js syntax.
    """
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the diagram generation process.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict[str, Any]: Updated workflow state with Mermaid diagrams
        """
        # Get modules and snippets from state
        modules = state.get("modules", [])
        snippets = state.get("snippets", [])
        
        if not modules and not snippets:
            self.logger.warning("No code modules or snippets to generate diagrams for")
            self._add_message(state, MessageType.WARNING, "No code to generate diagrams for")
            return state
        
        self.logger.info("Starting Mermaid diagram generation")
        self._add_message(state, MessageType.INFO, "Starting Mermaid diagram generation")
        
        # Initialize diagrams dictionary
        diagrams = {}
        
        # Generate module dependency diagram
        if modules:
            module_diagram = await self._generate_module_dependency_diagram(modules)
            if module_diagram:
                diagrams["module_dependencies"] = module_diagram
        
        # Generate class diagrams
        class_diagrams = await self._generate_class_diagrams(modules)
        diagrams.update(class_diagrams)
        
        # Generate flow diagrams for complex functions
        flow_diagrams = await self._generate_function_flow_diagrams(snippets)
        diagrams.update(flow_diagrams)
        
        # Generate architectural overview diagram using AI
        arch_diagram = await self._generate_architectural_diagram(state)
        if arch_diagram:
            diagrams["architecture"] = arch_diagram
        
        # Add diagrams to state
        state["diagrams"] = diagrams
        
        self.logger.info(f"Completed diagram generation: {len(diagrams)} diagrams created")
        self._add_message(
            state, 
            MessageType.SUCCESS, 
            f"Completed diagram generation: {len(diagrams)} diagrams created"
        )
        
        return state
    
    async def _generate_module_dependency_diagram(self, modules: List[ParsedModule]) -> Optional[str]:
        """Generate a Mermaid diagram showing module dependencies.
        
        Args:
            modules: List of parsed modules
            
        Returns:
            Optional[str]: Mermaid diagram in text format or None if generation fails
        """
        try:
            # Extract module dependencies
            dependencies = {}
            
            for module in modules:
                module_name = os.path.basename(module.file_path).replace('.py', '')
                dependencies[module_name] = set()
                
                # Find imports
                for imp in module.imports:
                    # Skip standard library imports
                    if imp.module and not imp.module.startswith(('os', 'sys', 're', 'json', 'time', 'datetime', 
                                                               'math', 'random', 'collections', 'typing')):
                        target = imp.module.split('.')[-1]
                        dependencies[module_name].add(target)
            
            # Build diagram nodes and edges
            nodes = set(dependencies.keys())
            edges = []
            
            # Add edges for dependencies
            for source, targets in dependencies.items():
                for target in targets:
                    # Only include target if it's a node (part of our modules)
                    if target in nodes:
                        edges.append(f'    {self._sanitize_id(source)} --> {self._sanitize_id(target)}')
            
            # If no edges, create a simple node list
            if not edges:
                diagram_content = 'graph TD\n'
                for node in nodes:
                    diagram_content += f'    {self._sanitize_id(node)}[{node}]\n'
            else:
                # Create diagram with edges
                diagram_content = 'graph TD\n'
                for edge in edges:
                    diagram_content += edge + '\n'
            
            # Return diagram in markdown format
            return f"```mermaid\n{diagram_content}```"
                
        except Exception as e:
            self.logger.error(f"Error generating module dependency diagram: {str(e)}")
            return None
    
    async def _generate_class_diagrams(self, modules: List[ParsedModule]) -> Dict[str, str]:
        """Generate class diagrams for each module with classes.
        
        Args:
            modules: List of parsed modules
            
        Returns:
            Dict[str, str]: Dictionary of class diagrams by module name
        """
        diagrams = {}
        
        for module in modules:
            # Skip modules without classes
            if not module.classes:
                continue
                
            module_name = os.path.basename(module.file_path).replace('.py', '')
            
            try:
                # Create class diagram
                diagram_content = 'classDiagram\n'
                
                # Add classes and relationships
                class_names = [cls.name for cls in module.classes]
                relationships = []
                
                for cls in module.classes:
                    # Add class definition
                    diagram_content += f'    class {self._sanitize_id(cls.name)} {{\n'
                    
                    # Add attributes
                    for attr in cls.attributes:
                        diagram_content += f'        +{attr}\n'
                    
                    # Add methods
                    for method in cls.methods:
                        # Use params instead of parameters
                        params_list = [param.name for param in method.params] if hasattr(method, 'params') else []
                        params = ', '.join(params_list)
                        diagram_content += f'        +{method.name}({params})\n'
                    
                    diagram_content += '    }\n'
                    
                    # Add inheritance relationships
                    if hasattr(cls, 'base_classes') and cls.base_classes:
                        for base in cls.base_classes:
                            base_name = base.split('.')[-1] if isinstance(base, str) else base
                            diagram_content += f'    {base_name} <|-- {cls.name}\n'
                
                # Add relationships
                for rel in relationships:
                    diagram_content += rel + '\n'
                
                # Add diagram to results
                diagrams[f'class_{module_name}'] = f"```mermaid\n{diagram_content}```"
                
            except Exception as e:
                self.logger.error(f"Error generating class diagram for {module_name}: {str(e)}")
        
        return diagrams
    
    async def _generate_function_flow_diagrams(self, snippets: List[CodeSnippet]) -> Dict[str, str]:
        """Generate flow diagrams for complex functions using AI.
        
        Args:
            snippets: List of code snippets
            
        Returns:
            Dict[str, str]: Dictionary of flow diagrams by function name
        """
        diagrams = {}
        
        # Get complex functions (more than 10 lines of code)
        complex_functions = [
            s for s in snippets 
            if s.symbol_type in ['function', 'method'] and len(s.text_content.strip().split('\n')) > 10
        ]
        
        # Generate diagrams for complex functions (limit to 5 to avoid too many API calls)
        for snippet in complex_functions[:5]:
            # Generate diagram
            diagram = await self._generate_function_flow_with_ai(snippet)
            
            # Add to results if generation succeeded
            if diagram:
                key = f"flow_{snippet.symbol_name.replace('.', '_')}"
                diagrams[key] = diagram
        
        return diagrams
    
    def _sanitize_id(self, text: str) -> str:
        """Sanitize text for use as a Mermaid ID.
        
        Args:
            text: The text to sanitize
            
        Returns:
            str: The sanitized ID
        """
        if not text:
            return ""
            
        # Replace spaces and hyphens with underscores
        sanitized = text.replace(" ", "_").replace("-", "_")
        
        # Replace special characters with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", sanitized)
        
        # Ensure ID doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = "n" + sanitized
            
        return sanitized
        
    @staticmethod
    def _should_retry_exception(exception):
        """Determine if an exception should trigger a retry.
        
        Args:
            exception: The exception to check
            
        Returns:
            bool: True if the exception should trigger a retry, False otherwise
        """
        # Retry on network errors, timeouts, and rate limits (HTTP 429)
        if isinstance(exception, (aiohttp.ClientError, asyncio.TimeoutError)):
            return True
        
        # Retry on certain API errors (rate limits, server errors)
        if isinstance(exception, ValueError):
            error_str = str(exception).lower()
            if any(term in error_str for term in ['rate limit', '429', '500', '503', 'timeout', 'too many requests']):
                return True
        
        return False
        
    @retry(
        retry=retry_if_exception(lambda e: MermaidDiagramAgent._should_retry_exception(e)),
        stop=stop_after_attempt(5),  # Increased from 3 to 5 attempts
        wait=wait_random_exponential(multiplier=1, min=2, max=60),  # More robust backoff strategy
        reraise=True
    )
    async def _call_openrouter_api(self, prompt: str, system_message: str) -> Optional[str]:
        """Call OpenRouter API with retry logic.
        
        Args:
            prompt: The prompt to send to the API
            system_message: The system message to include
            
        Returns:
            Optional[str]: The content of the API response or None if failed
            
        Raises:
            ValueError: If the API request fails or API key is not configured
        """
        # Get API key from config
        api_key = self.config.openrouter_api_key
        if not api_key:
            self.logger.error("OpenRouter API key is not configured")
            raise ValueError("OpenRouter API key is not configured")
        
        # Get model name from config or use default
        model = self.config.summarizer_model_name or "openai/gpt-4-turbo"
        
        # Call OpenRouter API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://autodocai.com",
            "X-Title": "AutoDoc AI"
        }
        
        # Truncate prompt if it's too long (to avoid token limit issues)
        max_prompt_length = 4000
        if len(prompt) > max_prompt_length:
            self.logger.warning(f"Truncating prompt from {len(prompt)} to {max_prompt_length} characters")
            prompt = prompt[:max_prompt_length] + "...[truncated]"
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1024
        }
        
        try:
            # Make API request with timeout
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)  # Increased timeout to 60 seconds
                ) as response:
                    response_text = await response.text()
                    
                    # Handle non-200 responses
                    if response.status != 200:
                        error_message = f"API request failed with status {response.status}"
                        
                        # Try to extract more detailed error information
                        try:
                            error_data = json.loads(response_text)
                            error_type = error_data.get('error', {}).get('type', 'unknown')
                            error_message = f"{error_message}: {error_type} - {error_data.get('error', {}).get('message', 'No message')}"
                        except json.JSONDecodeError:
                            error_message = f"{error_message}: {response_text[:200]}..."
                        
                        # Raise appropriate error based on status code
                        if response.status == 429:
                            self.logger.warning(f"Rate limit exceeded: {error_message}")
                            raise ValueError(f"Rate limit exceeded: {error_message}")
                        elif response.status >= 500:
                            self.logger.warning(f"Server error: {error_message}")
                            raise ValueError(f"Server error: {error_message}")
                        else:
                            self.logger.error(f"API error: {error_message}")
                            raise ValueError(f"API error: {error_message}")
                    
                    try:
                        data = json.loads(response_text)
                        if not data.get("choices") or not data["choices"][0].get("message"):
                            self.logger.error(f"Unexpected API response format: {response_text[:200]}...")
                            raise ValueError("API response missing expected fields")
                        
                        return data["choices"][0]["message"]["content"]
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse JSON response: {str(e)}")
                        raise ValueError(f"Invalid JSON response: {str(e)}")
                    except KeyError as e:
                        self.logger.error(f"Missing key in API response: {str(e)}")
                        raise ValueError(f"Invalid API response structure: {str(e)}")
        except aiohttp.ClientError as e:
            self.logger.warning(f"Network error: {str(e)}")
            raise  # Will be retried by the decorator
        except asyncio.TimeoutError as e:
            self.logger.warning(f"API request timed out: {str(e)}")
            raise  # Will be retried by the decorator
        except ValueError as e:
            # Check if this is a retriable error
            if self._should_retry_exception(e):
                self.logger.warning(f"Retriable error: {str(e)}")
                raise  # Will be retried by the decorator
            else:
                self.logger.error(f"Non-retriable error: {str(e)}")
                raise
    
    async def _generate_function_flow_with_ai(self, snippet: CodeSnippet) -> Optional[str]:
        """Generate a flow diagram for a function using AI.
        
        Args:
            snippet: Code snippet of a function
            
        Returns:
            Optional[str]: Mermaid diagram in text format or None if generation fails
        """
        try:
            # Skip if code is too short or not a function/method
            if len(snippet.text_content) < 20:
                self.logger.info(f"Skipping flow diagram for {snippet.symbol_name}: code too short")
                return None
                
            if snippet.symbol_type not in ["function", "method"]:
                self.logger.info(f"Skipping flow diagram for {snippet.symbol_name}: not a function/method")
                return None
            
            # Prepare prompt with more detailed instructions
            prompt = (
                f"I need you to create a Mermaid.js flowchart diagram for the following function:\n\n"
                f"```python\n{snippet.text_content}\n```\n\n"
                "Please create a flowchart that shows the execution flow of this function. Make sure to:\n"
                "1. Identify the main steps in the function\n"
                "2. Show decision points (if statements) with proper branching\n"
                "3. Indicate loops clearly\n"
                "4. Keep the diagram clean and readable\n"
                "5. Use meaningful node labels that reflect what each step does\n"
                "6. Focus on the logical flow rather than line-by-line translation\n\n"
                "Your response should be a valid Mermaid.js flowchart diagram enclosed in triple backticks with the mermaid tag.\n\n"
                "Example of expected format:\n"
                "```mermaid\n"
                "graph TD\n"
                "A[Start] --> B[Step 1]\n"
                "B --> C{{Decision?}}\n"
                "C -->|Yes| D[Step 2]\n"
                "C -->|No| E[Step 3]\n"
                "D --> E\n"
                "E --> F[End]\n"
                "```\n\n"
                "Or another example:\n"
                "```mermaid\n"
                "graph TD\n"
                "A[Start] --> B[Process Data]\n"
                "B --> C{{Valid Data?}}\n"
                "C -->|Yes| D[Save Result]\n"
                "C -->|No| E[Handle Error]\n"
                "D --> F[Return Success]\n"
                "E --> G[Return Error]\n"
                "```\n\n"
                "Please create the diagram now for the function I provided."
            )
            
            system_message = "You are an expert at analyzing code and creating clear, informative Mermaid.js diagrams that visualize code flow and structure."
            
            # Call API with retry logic
            self.logger.info(f"Generating flow diagram for {snippet.symbol_name}")
            content = await self._call_openrouter_api(prompt, system_message)
            if not content:
                self.logger.warning(f"No content returned from API for {snippet.symbol_name}")
                return None
                
            # Extract Mermaid diagram
            pattern = r"```mermaid\s*(.*?)```"
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                diagram_content = match.group(1).strip()
                
                # Validate the diagram content has minimum requirements
                if len(diagram_content) < 30 or "graph" not in diagram_content.lower():
                    self.logger.warning(f"Invalid or incomplete diagram for {snippet.symbol_name}")
                    return None
                else:
                    diagram = "```mermaid\n" + diagram_content + "\n```"
                    self.logger.info(f"Successfully generated flow diagram for {snippet.symbol_name}")
                    return diagram
            else:
                self.logger.warning(f"No mermaid diagram found in API response for {snippet.symbol_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating function flow diagram for {snippet.symbol_name}: {str(e)}")
            return None
    
    async def _generate_architectural_diagram(self, state: Dict[str, Any]) -> Optional[str]:
        """Generate an architectural overview diagram using AI.
        
        Args:
            state: Current workflow state
            
        Returns:
            Optional[str]: Mermaid diagram in text format or None if generation fails
        """
        try:
            # Get repo info and rag results
            repo_info = state.get("repo_info", {})
            rag_results = state.get("rag_results", {})
            
            # If no architectural overview, we can't generate a diagram
            if not rag_results.get("architectural_overview"):
                self.logger.warning("No architectural overview found in RAG results")
                return None
            
            # Get repo name
            repo_name = repo_info.get("name", "Project")
            
            # Get architectural overview
            architectural_overview = rag_results.get("architectural_overview", {}).get("en", "")
            
            # Get file paths (up to 10 to avoid overly complex diagrams)
            file_paths = []
            for snippet in state.get("snippets", [])[:10]:  # Limit to first 10 snippets
                if snippet.file_path and snippet.file_path not in file_paths:
                    file_paths.append(snippet.file_path)
            
            # Join file paths with newlines
            file_paths_str = "\n".join(['- ' + path for path in file_paths])
            
            # Prepare prompt
            prompt = (
                f"I need you to create a Mermaid.js diagram that visualizes the architecture of a software project named '{repo_name}'.\n\n"
                f"Here's an architectural overview of the project:\n\n{architectural_overview}\n\n"
                f"The project contains these key files/modules (partial list):\n{file_paths_str}\n\n"
                "Based on this information, please create a Mermaid.js diagram that shows:\n"
                "1. The main components of the system\n"
                "2. How these components interact with each other\n"
                "3. The overall structure of the application\n"
                "4. Any clear layering or architectural patterns present\n\n"
                "Your response should be a valid Mermaid.js diagram enclosed in triple backticks with the mermaid tag.\n"
                "Keep the diagram clean, readable, and focused on the high-level architecture.\n\n"
                "Prefer using 'flowchart TD' or 'graph TD' for directional flows, or 'classDiagram' if showing class relationships.\n\n"
                "Example of the expected format:\n"
                "```mermaid\n"
                "graph TD\n"
                "    A[Component A] --> B[Component B]\n"
                "    A --> C[Component C]\n"
                "    B --> D[Component D]\n"
                "    C --> D\n"
                "```"
            )
            
            system_message = "You are an expert software architect who can create clear, informative Mermaid.js diagrams that visualize software architecture based on limited information."
            
            # Call API with retry logic
            self.logger.info("Generating architectural diagram")
            content = await self._call_openrouter_api(prompt, system_message)
            if not content:
                self.logger.warning("No content returned from API for architectural diagram")
                return None
            
            # Extract Mermaid diagram
            pattern = r"```mermaid\s*(.*?)```"
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                diagram_content = match.group(1).strip()
                if diagram_content:
                    diagram = "```mermaid\n" + diagram_content + "\n```"
                    self.logger.info("Successfully generated architectural diagram")
                    return diagram
                else:
                    self.logger.warning("Empty diagram content in API response for architectural diagram")
                    return None
            else:
                self.logger.warning("No mermaid diagram found in API response for architectural diagram")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating architectural diagram: {str(e)}")
            return None
