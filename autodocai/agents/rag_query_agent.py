"""
RAG query agent for AutoDoc AI.

This agent handles vector embeddings, retrieval augmented generation, and 
context-aware querying of code repositories using Qdrant and OpenRouter.
"""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from autodocai.agents.base import BaseAgent
from autodocai.schemas import CodeSnippet, MessageType


class RAGQueryAgent(BaseAgent):
    """Agent for retrieval augmented generation queries.
    
    This agent indexes code snippets in a vector database (Qdrant) and provides
    context-aware responses to queries about the codebase using RAG techniques.
    """
    
    def __init__(self, config):
        """Initialize the RAG query agent.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.qdrant_client = None
        self.collection_name = None
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the RAG indexing and querying process.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict[str, Any]: Updated workflow state with RAG results
        """
        # Get snippets from state
        snippets = state.get("snippets", [])
        if not snippets:
            self.logger.warning("No code snippets to index")
            self._add_message(state, MessageType.WARNING, "No code snippets to index")
            return state
        
        # Initialize Qdrant client
        await self._init_qdrant()
        
        # Create collection if it doesn't exist
        await self._create_collection()
        
        self.logger.info(f"Starting indexing of {len(snippets)} code snippets")
        self._add_message(state, MessageType.INFO, f"Starting indexing of {len(snippets)} code snippets")
        
        # Index snippets
        await self._index_snippets(snippets)
        
        # Generate architectural overview and module explanations
        overview = await self._generate_architectural_overview(snippets, state.get("repo_info"))
        module_explanations = await self._generate_module_explanations(snippets)
        
        # Add results to state
        state["rag_results"] = {
            "architectural_overview": overview,
            "module_explanations": module_explanations,
            "collection_name": self.collection_name
        }
        
        self.logger.info(f"Completed RAG indexing and generation")
        self._add_message(
            state, 
            MessageType.SUCCESS, 
            f"Completed RAG indexing and generation"
        )
        
        return state
    
    async def _init_qdrant(self):
        """Initialize the Qdrant client."""
        try:
            # Get Qdrant URL from config
            qdrant_url = self.config.qdrant_url
            if not qdrant_url:
                raise ValueError("Qdrant URL is not configured")
            
            # Initialize client
            self.qdrant_client = QdrantClient(url=qdrant_url)
            
            # Generate a unique collection name for this repository
            repo_hash = str(hash(self.config.target_repo_url))[:8]
            timestamp = str(int(os.path.getmtime(os.path.dirname(__file__))))[:8]
            self.collection_name = f"autodoc_{repo_hash}_{timestamp}"
            
            self.logger.info(f"Initialized Qdrant client with collection: {self.collection_name}")
            
        except Exception as e:
            self.logger.error(f"Error initializing Qdrant: {str(e)}")
            raise ValueError(f"Failed to initialize Qdrant: {str(e)}")
    
    async def _create_collection(self):
        """Create a Qdrant collection for the current repository."""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections().collections
            if any(collection.name == self.collection_name for collection in collections):
                self.logger.info(f"Collection {self.collection_name} already exists")
                return
            
            # Create collection
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=1536,  # Size for OpenAI text-embedding-3-small
                    distance=qdrant_models.Distance.COSINE
                )
            )
            
            # Create payload index for faster filtering
            self.qdrant_client.create_payload_index(
                collection_name=self.collection_name,
                field_name="file_path",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD
            )
            
            self.qdrant_client.create_payload_index(
                collection_name=self.collection_name,
                field_name="symbol_type",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD
            )
            
            self.qdrant_client.create_payload_index(
                collection_name=self.collection_name,
                field_name="language",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD
            )
            
            self.logger.info(f"Created collection {self.collection_name}")
            
        except Exception as e:
            self.logger.error(f"Error creating collection: {str(e)}")
            raise ValueError(f"Failed to create Qdrant collection: {str(e)}")
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for a text using OpenRouter.
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Vector embedding
        """
        try:
            # Get API key from config
            api_key = self.config.openrouter_api_key
            if not api_key:
                raise ValueError("OpenRouter API key is not configured")
            
            # Get model name from config
            model = self.config.embedding_model_name
            
            # Call OpenRouter API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://autodocai.com",  # Replace with your site
                "X-Title": "AutoDoc AI"
            }
            
            payload = {
                "model": model,
                "input": text,
                "encoding_format": "float"
            }
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"API request failed with status {response.status}: {error_text}")
                    
                    data = await response.json()
                    embedding = data["data"][0]["embedding"]
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            # Return a random embedding for resilience (not ideal but prevents pipeline failure)
            return list(np.random.uniform(-1, 1, 1536))
    
    async def _prepare_snippet_for_embedding(self, snippet: CodeSnippet) -> str:
        """Prepare a snippet for embedding by creating a textual representation.
        
        Args:
            snippet: Code snippet
            
        Returns:
            str: Textual representation for embedding
        """
        # Combine code and metadata for a rich representation
        content = f"File: {snippet.file_path}\n"
        content += f"Type: {snippet.symbol_type}\n"
        content += f"Name: {snippet.symbol_name}\n"
        
        if snippet.original_docstring:
            content += f"Documentation: {snippet.original_docstring}\n"
        
        content += f"Code:\n{snippet.text_content}\n"
        
        # Add AI summary if available
        if snippet.ai_summary_en:
            content += f"Summary: {snippet.ai_summary_en}\n"
        
        return content
    
    async def _index_snippets(self, snippets: List[CodeSnippet]):
        """Index code snippets in Qdrant.
        
        Args:
            snippets: List of code snippets to index
        """
        try:
            # Process snippets in batches
            batch_size = 10
            total_indexed = 0
            
            for i in range(0, len(snippets), batch_size):
                batch = snippets[i:i+batch_size]
                
                points = []
                
                for snippet in batch:
                    # Prepare text for embedding
                    text = await self._prepare_snippet_for_embedding(snippet)
                    
                    # Get embedding
                    embedding = await self._get_embedding(text)
                    
                    # Create point
                    point = qdrant_models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={
                            "snippet_id": snippet.id,
                            "file_path": snippet.file_path,
                            "start_line": snippet.start_line,
                            "end_line": snippet.end_line,
                            "text_content": snippet.text_content,
                            "symbol_name": snippet.symbol_name,
                            "symbol_type": snippet.symbol_type,
                            "language": snippet.language,
                            "original_docstring": snippet.original_docstring,
                            "ai_summary_en": snippet.ai_summary_en,
                            "ai_summary_vi": snippet.ai_summary_vi
                        }
                    )
                    
                    points.append(point)
                
                # Upsert points
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                total_indexed += len(batch)
                self.logger.info(f"Indexed {total_indexed} of {len(snippets)} snippets")
            
            self.logger.info(f"Completed indexing {total_indexed} snippets")
            
        except Exception as e:
            self.logger.error(f"Error indexing snippets: {str(e)}")
            raise ValueError(f"Failed to index snippets in Qdrant: {str(e)}")
    
    async def _generate_architectural_overview(
        self, snippets: List[CodeSnippet], repo_info: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate an architectural overview of the codebase.
        
        Args:
            snippets: List of code snippets
            repo_info: Repository information
            
        Returns:
            Dict[str, str]: Architectural overview in different languages
        """
        try:
            # Get API key from config
            api_key = self.config.openrouter_api_key
            if not api_key:
                raise ValueError("OpenRouter API key is not configured")
            
            # Get model name from config
            model = self.config.summarizer_model_name
            
            # Prepare module information
            module_info = {}
            for snippet in snippets:
                if snippet.symbol_type == "module":
                    path_parts = snippet.file_path.split("/")
                    if len(path_parts) > 1:
                        module_path = "/".join(path_parts[:-1])
                        if module_path not in module_info:
                            module_info[module_path] = []
                        module_info[module_path].append({
                            "name": snippet.symbol_name,
                            "summary": snippet.ai_summary_en,
                            "path": snippet.file_path
                        })
            
            # Prepare prompt
            prompt = f"""
I need you to generate an architectural overview of a codebase. Here's information about the repository:

Repository: {repo_info.name if repo_info else "Unknown"}
Languages: {', '.join(repo_info.languages) if repo_info else "Python"}
Description: {repo_info.description if repo_info and repo_info.description else "No description available"}

Key modules/directories:
"""
            
            for module_path, files in module_info.items():
                prompt += f"\n- {module_path}/\n"
                for file in files[:5]:  # Limit to 5 files per module to keep prompt size reasonable
                    summary = file.get("summary", "No summary available")
                    if summary:
                        summary = summary.split("\n")[0]  # Just take the first line
                    prompt += f"  - {file['name']}: {summary}\n"
            
            prompt += """
Based on this information, please provide:
1. A high-level architectural overview of the codebase
2. The main components and their responsibilities
3. The relationships between components
4. Design patterns or architectural patterns used (if identifiable)

Format your response as follows:

## OVERVIEW_EN
[Your detailed English overview here]
"""
            
            if "VI" in self.config.output_languages:
                prompt += "\n\n## OVERVIEW_VI\n[Your detailed Vietnamese overview here]"
            
            # Call OpenRouter API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://autodocai.com",  # Replace with your site
                "X-Title": "AutoDoc AI"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a software architecture expert who can analyze codebases and provide clear, informative architectural overviews."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2048
            }
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"API request failed with status {response.status}: {error_text}")
                    
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
            
            # Parse response
            overview = {}
            
            # Extract English overview
            if "## OVERVIEW_EN" in content:
                parts = content.split("## OVERVIEW_EN")
                if len(parts) > 1:
                    en_part = parts[1].strip()
                    if "## OVERVIEW_VI" in en_part:
                        en_part = en_part.split("## OVERVIEW_VI")[0].strip()
                    overview["en"] = en_part
            else:
                # If no specific format, use the entire response as English overview
                overview["en"] = content.strip()
            
            # Extract Vietnamese overview if available
            if "## OVERVIEW_VI" in content:
                parts = content.split("## OVERVIEW_VI")
                if len(parts) > 1:
                    overview["vi"] = parts[1].strip()
            
            return overview
            
        except Exception as e:
            self.logger.error(f"Error generating architectural overview: {str(e)}")
            return {"en": "Failed to generate architectural overview."}
    
    async def _generate_module_explanations(self, snippets: List[CodeSnippet]) -> Dict[str, Dict[str, str]]:
        """Generate explanations for each module.
        
        Args:
            snippets: List of code snippets
            
        Returns:
            Dict[str, Dict[str, str]]: Module explanations in different languages
        """
        try:
            # Group snippets by module (file path)
            modules = {}
            for snippet in snippets:
                if snippet.symbol_type == "module":
                    modules[snippet.file_path] = {
                        "snippet": snippet,
                        "explanation": {}
                    }
            
            # For each module, generate an explanation
            for path, module in modules.items():
                snippet = module["snippet"]
                
                # If there's already an AI summary, use that
                if snippet.ai_summary_en:
                    module["explanation"]["en"] = snippet.ai_summary_en
                    if snippet.ai_summary_vi:
                        module["explanation"]["vi"] = snippet.ai_summary_vi
                    continue
                
                # Otherwise, generate a new explanation
                explanation = await self._generate_explanation(snippet)
                module["explanation"] = explanation
            
            # Return module explanations
            return {path: module["explanation"] for path, module in modules.items()}
            
        except Exception as e:
            self.logger.error(f"Error generating module explanations: {str(e)}")
            return {}
    
    async def _generate_explanation(self, snippet: CodeSnippet) -> Dict[str, str]:
        """Generate an explanation for a code snippet.
        
        Args:
            snippet: Code snippet
            
        Returns:
            Dict[str, str]: Explanation in different languages
        """
        try:
            # Get API key from config
            api_key = self.config.openrouter_api_key
            if not api_key:
                raise ValueError("OpenRouter API key is not configured")
            
            # Get model name from config
            model = self.config.summarizer_model_name
            
            # Prepare prompt
            prompt = f"""
Please provide a detailed explanation of the following code module:

File: {snippet.file_path}
Language: {snippet.language}

```{snippet.language}
{snippet.text_content}
```

Please explain:
1. The purpose and responsibility of this module
2. Key functions or classes it contains
3. How it fits into the larger codebase
4. Any notable patterns or techniques used

Format your response as follows:

## EXPLANATION_EN
[Your detailed English explanation here]
"""
            
            if "VI" in self.config.output_languages:
                prompt += "\n\n## EXPLANATION_VI\n[Your detailed Vietnamese explanation here]"
            
            # Call OpenRouter API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://autodocai.com",  # Replace with your site
                "X-Title": "AutoDoc AI"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a code documentation expert who can analyze code modules and provide clear, informative explanations."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1024
            }
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"API request failed with status {response.status}: {error_text}")
                    
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
            
            # Parse response
            explanation = {}
            
            # Extract English explanation
            if "## EXPLANATION_EN" in content:
                parts = content.split("## EXPLANATION_EN")
                if len(parts) > 1:
                    en_part = parts[1].strip()
                    if "## EXPLANATION_VI" in en_part:
                        en_part = en_part.split("## EXPLANATION_VI")[0].strip()
                    explanation["en"] = en_part
            else:
                # If no specific format, use the entire response as English explanation
                explanation["en"] = content.strip()
            
            # Extract Vietnamese explanation if available
            if "## EXPLANATION_VI" in content:
                parts = content.split("## EXPLANATION_VI")
                if len(parts) > 1:
                    explanation["vi"] = parts[1].strip()
            
            return explanation
            
        except Exception as e:
            self.logger.error(f"Error generating explanation: {str(e)}")
            return {"en": "Failed to generate explanation."}
    
    async def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query the vector database for relevant code snippets.
        
        This method can be called by other agents or directly to retrieve
        contextually relevant code snippets.
        
        Args:
            query_text: Query text
            top_k: Number of results to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of relevant code snippets
        """
        try:
            if not self.qdrant_client or not self.collection_name:
                raise ValueError("RAG system not initialized")
            
            # Get embedding for query
            query_embedding = await self._get_embedding(query_text)
            
            # Search Qdrant
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            # Extract results
            results = []
            for hit in search_result:
                results.append({
                    "score": hit.score,
                    "snippet_id": hit.payload.get("snippet_id"),
                    "file_path": hit.payload.get("file_path"),
                    "symbol_name": hit.payload.get("symbol_name"),
                    "symbol_type": hit.payload.get("symbol_type"),
                    "text_content": hit.payload.get("text_content"),
                    "ai_summary_en": hit.payload.get("ai_summary_en"),
                    "ai_summary_vi": hit.payload.get("ai_summary_vi")
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error querying RAG system: {str(e)}")
            return []
