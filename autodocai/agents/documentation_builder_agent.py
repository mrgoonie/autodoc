"""
Documentation builder agent for AutoDoc AI.

This agent builds the final Docusaurus site from the generated documentation.
"""

import os
import asyncio
import json
from typing import Dict, Any, List, Optional
from autodocai.agents.base import BaseAgent
from autodocai.schemas import MessageType

class DocumentationBuilderAgent(BaseAgent):
    """Agent for building the final Docusaurus site."""
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the documentation building process.
        
        Args:
            state: Current workflow state containing documentation path
            
        Returns:
            Dict[str, Any]: Updated workflow state with build information
        """
        docs_path = state.get("docs_path")
        if not docs_path:
            self._add_message(state, MessageType.ERROR, "Documentation path is missing from state")
            return state
            
        self._add_message(state, MessageType.INFO, f"Building documentation site at {docs_path}")
        
        try:
            # Install dependencies
            install_success = await self._install_dependencies(docs_path)
            if not install_success:
                self._add_message(
                    state,
                    MessageType.ERROR,
                    "Failed to install dependencies"
                )
                return state
            
            # Build the documentation site
            build_path = await self._build_documentation(docs_path)
            
            # Update state with build information
            if build_path:
                state["build_path"] = build_path
                state["build_result"] = {
                    "success": True,
                    "build_path": build_path
                }
                
                self._add_message(
                    state, 
                    MessageType.SUCCESS, 
                    f"Documentation site built successfully at {build_path}"
                )
            else:
                self._add_message(
                    state,
                    MessageType.ERROR,
                    "Failed to build documentation site"
                )
                
            return state
            
        except Exception as e:
            self.logger.error(f"Error building documentation site: {str(e)}")
            self._add_message(
                state,
                MessageType.ERROR,
                f"Failed to build documentation site: {str(e)}"
            )
            raise ValueError(f"Failed to build documentation site: {str(e)}")
    
    async def _install_dependencies(self, docs_path: str) -> bool:
        """
        Install Docusaurus dependencies.
        
        Args:
            docs_path: Path to the documentation directory
            
        Returns:
            bool: True if installation was successful
        """
        try:
            # Create package.json if it doesn't exist
            package_json_path = os.path.join(docs_path, "package.json")
            if not os.path.exists(package_json_path):
                package_json = {
                    "name": "autodoc-documentation",
                    "version": "0.0.1",
                    "private": True,
                    "scripts": {
                        "docusaurus": "docusaurus",
                        "start": "docusaurus start",
                        "build": "docusaurus build",
                        "swizzle": "docusaurus swizzle",
                        "deploy": "docusaurus deploy",
                        "clear": "docusaurus clear",
                        "serve": "docusaurus serve",
                        "write-translations": "docusaurus write-translations",
                        "write-heading-ids": "docusaurus write-heading-ids"
                    },
                    "dependencies": {
                        "@docusaurus/core": "2.4.3",
                        "@docusaurus/preset-classic": "2.4.3",
                        "@docusaurus/theme-mermaid": "2.4.3",
                        "@mdx-js/react": "^1.6.22",
                        "clsx": "^1.2.1",
                        "prism-react-renderer": "^1.3.5",
                        "react": "^17.0.2",
                        "react-dom": "^17.0.2"
                    },
                    "devDependencies": {
                        "@docusaurus/module-type-aliases": "2.4.3"
                    },
                    "browserslist": {
                        "production": [
                            ">0.5%",
                            "not dead",
                            "not op_mini all"
                        ],
                        "development": [
                            "last 1 chrome version",
                            "last 1 firefox version",
                            "last 1 safari version"
                        ]
                    },
                    "engines": {
                        "node": ">=16.14"
                    }
                }
                
                with open(package_json_path, 'w') as f:
                    json.dump(package_json, f, indent=2)
            
            # Install dependencies using npm asynchronously
            self.logger.info(f"Installing Docusaurus dependencies in {docs_path}")
            
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                "npm",
                "install",
                cwd=docs_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for process to complete
            stdout, stderr = await process.communicate()
            
            # Check process result
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error during installation"
                self.logger.error(f"Error installing dependencies: {error_msg}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Exception during dependency installation: {str(e)}")
            return False
    
    async def _build_documentation(self, docs_path: str) -> Optional[str]:
        """
        Build the Docusaurus documentation site.
        
        Args:
            docs_path: Path to the documentation directory
            
        Returns:
            Optional[str]: Path to the build directory if successful, None otherwise
        """
        try:
            # Build the site using npm run build
            self.logger.info(f"Building Docusaurus documentation in {docs_path}")
            
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                "npm", "run", "build",
                cwd=docs_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for process to complete
            stdout, stderr = await process.communicate()
            
            # Check process result
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error during build"
                self.logger.error(f"Error building documentation: {error_msg}")
                return None
            
            # Check if build directory exists
            build_path = os.path.join(docs_path, "build")
            if not os.path.exists(build_path):
                self.logger.error(f"Build directory not found at {build_path}")
                return None
                
            return build_path
            
        except Exception as e:
            self.logger.error(f"Exception during documentation build: {str(e)}")
            return None
            
    async def _build_site(self, docs_path: str) -> Dict[str, Any]:
        """
        Build the Docusaurus site.
        
        Args:
            docs_path: Path to the documentation directory
            
        Returns:
            Dict[str, Any]: Build result information
        """
        try:
            self.logger.info(f"Building Docusaurus site in {docs_path}")
            
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                "npm", "run", "build",
                cwd=docs_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for process to complete
            stdout, stderr = await process.communicate()
            
            # Check process result
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error during build"
                self.logger.error(f"Error building site: {error_msg}")
                raise ValueError(f"Failed to build site: {error_msg}")
                
            build_path = os.path.join(docs_path, "build")
            if not os.path.exists(build_path):
                raise ValueError(f"Build directory not found at {build_path}")
                
            return {
                "success": True,
                "build_path": build_path,
                "output": stdout.decode() if stdout else ""
            }
            
        except Exception as e:
            self.logger.error(f"Exception during site build: {str(e)}")
            raise ValueError(f"Failed to build site: {str(e)}")