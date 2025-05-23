"""
Documentation builder agent for AutoDoc AI.

This agent builds the final Docusaurus site from the generated documentation.
"""

import os
import subprocess
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
            raise ValueError("Documentation path is missing from state")
            
        self._add_message(state, MessageType.INFO, f"Building documentation site at {docs_path}")
        
        try:
            # Install dependencies
            await self._install_dependencies(docs_path)
            
            # Build the site
            build_result = await self._build_site(docs_path)
            
            # Update state with build information
            state["build_result"] = build_result
            state["build_path"] = os.path.join(docs_path, "build")
            
            self._add_message(
                state, 
                MessageType.SUCCESS, 
                f"Documentation site built successfully at {state['build_path']}"
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
                import json
                json.dump(package_json, f, indent=2)
        
        # Install dependencies using npm
        self.logger.info(f"Installing Docusaurus dependencies in {docs_path}")
        result = subprocess.run(
            ["npm", "install"],
            cwd=docs_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            self.logger.error(f"Error installing dependencies: {result.stderr}")
            raise ValueError(f"Failed to install dependencies: {result.stderr}")
            
        return True
    
    async def _build_site(self, docs_path: str) -> Dict[str, Any]:
        """
        Build the Docusaurus site.
        
        Args:
            docs_path: Path to the documentation directory
            
        Returns:
            Dict[str, Any]: Build result information
        """
        self.logger.info(f"Building Docusaurus site in {docs_path}")
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=docs_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            self.logger.error(f"Error building site: {result.stderr}")
            raise ValueError(f"Failed to build site: {result.stderr}")
            
        build_path = os.path.join(docs_path, "build")
        if not os.path.exists(build_path):
            raise ValueError(f"Build directory not found at {build_path}")
            
        return {
            "success": True,
            "build_path": build_path,
            "output": result.stdout
        }