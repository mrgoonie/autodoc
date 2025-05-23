"""
Docstring enhancer agent for AutoDoc AI.

This agent generates or improves docstrings for code that lacks proper documentation.
"""

import asyncio
from typing import Dict, Any, List, Optional, Union

import aiohttp
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from autodocai.agents.base import BaseAgent
from autodocai.schemas import MessageType, CodeSnippet

class DocstringEnhancerAgent(BaseAgent):
    """Agent for enhancing or generating docstrings for code."""
    
    async def _execute(self, state: Union[Dict[str, Any], BaseModel]) -> Union[Dict[str, Any], BaseModel]:
        """
        Execute the docstring enhancement process.
        
        Args:
            state: Current workflow state containing snippets to process (dictionary or Pydantic model)
            
        Returns:
            Union[Dict[str, Any], BaseModel]: Updated workflow state with enhanced docstrings
        """
        # Get snippets using the helper method
        snippets = self.get_state_value(state, "snippets", [])
        if not snippets:
            self._add_message(state, MessageType.WARNING, "No code snippets found to enhance docstrings")
            return state
            
        self._add_message(state, MessageType.INFO, f"Enhancing docstrings for {len(snippets)} code snippets")
        
        # Process snippets without docstrings or with minimal docstrings
        enhanced_snippets = []
        for snippet in snippets:
            # Only enhance snippets that don't have docstrings or have very short ones
            if not snippet.original_docstring or len(snippet.original_docstring.strip()) < 10:
                self.logger.info(f"Enhancing docstring for {snippet.symbol_name} with length {len(snippet.original_docstring) if snippet.original_docstring else 0}")
                # Use the OpenRouter API to generate docstrings
                enhanced_docstring = await self._generate_docstring(
                    snippet.text_content, 
                    snippet.symbol_type,
                    snippet.symbol_name
                )
                
                # Create a copy of the snippet with the enhanced docstring
                # We need to make a new object since the enhanced_docstring might be validated
                new_snippet = CodeSnippet(
                    id=snippet.id,
                    file_path=snippet.file_path,
                    start_line=snippet.start_line,
                    end_line=snippet.end_line,
                    text_content=snippet.text_content,
                    symbol_type=snippet.symbol_type,
                    language=snippet.language,
                    symbol_name=snippet.symbol_name,
                    original_docstring=snippet.original_docstring,
                    enhanced_docstring=enhanced_docstring
                )
                enhanced_snippets.append(new_snippet)
        
        # Add enhanced snippets to state using the helper method
        self.set_state_value(state, "enhanced_snippets", enhanced_snippets)
        
        # Update current stage
        self.set_state_value(state, "current_stage", "docstrings_enhanced")
        
        self._add_message(
            state, 
            MessageType.SUCCESS, 
            f"Enhanced docstrings for {len(enhanced_snippets)} code snippets"
        )
        return state
        
    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
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
            raise ValueError("OpenRouter API key is not configured")
        
        # Get model name from config or use default
        model = self.config.summarizer_model_name or "openai/gpt-4-turbo"
        
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
                    timeout=aiohttp.ClientTimeout(total=30)  # 30 second timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"API request failed with status {response.status}: {error_text}")
                    
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
        except aiohttp.ClientError as e:
            self.logger.error(f"API request error: {str(e)}") 
            raise  # Will be retried by the decorator
        except asyncio.TimeoutError:
            self.logger.error("API request timed out")
            raise ValueError("OpenRouter API request timed out") 
        except Exception as e:
            self.logger.error(f"Unexpected error calling OpenRouter API: {str(e)}")
            raise ValueError(f"OpenRouter API error: {str(e)}") 
            
    async def _generate_docstring(self, code: str, symbol_type: str, symbol_name: str) -> Dict[str, str]:
        """
        Generate enhanced docstring for a code snippet using OpenRouter API.
        
        Args:
            code: The code content to generate docstring for
            symbol_type: Type of symbol (function, class, method)
            symbol_name: Name of the symbol
            
        Returns:
            Dict[str, str]: Enhanced docstring in English and Vietnamese
        """
        try:
            # Prepare prompt for English docstring
            en_prompt = f"""
            Generate a comprehensive docstring for the following {symbol_type} named {symbol_name}:
            
            ```python
            {code}
            ```
            
            The docstring should follow Google style format and include:
            - A clear description of the {symbol_type}'s purpose
            - All parameters with types and descriptions
            - Return value with type and description (if applicable)
            - Exceptions raised (if applicable)
            - Example usage (if possible)
            
            Only return the docstring content, without any additional explanation.
            """
            
            system_message = "You are an expert Python documentation writer specializing in clear, comprehensive docstrings."
            
            # Call API for English docstring
            en_docstring = await self._call_openrouter_api(en_prompt, system_message)
            if not en_docstring:
                self.logger.warning(f"Failed to generate English docstring for {symbol_name}")
                en_docstring = f"Docstring for {symbol_name}"
            
            # Prepare prompt for Vietnamese translation
            vi_prompt = f"""
            Translate the following Python docstring from English to Vietnamese:
            
            ```
            {en_docstring}
            ```
            
            Please maintain the same format and structure. Only return the translated docstring, without any additional explanation.
            """
            
            vi_system_message = "You are an expert technical translator specializing in translating programming documentation from English to Vietnamese."
            
            # Call API for Vietnamese translation
            vi_docstring = await self._call_openrouter_api(vi_prompt, vi_system_message)
            if not vi_docstring:
                self.logger.warning(f"Failed to generate Vietnamese docstring for {symbol_name}")
                vi_docstring = f"Docstring cho {symbol_name}"
            
            return {
                "en": en_docstring.strip(),
                "vi": vi_docstring.strip()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating docstring for {symbol_name}: {str(e)}")
            return {
                "en": f"Docstring for {symbol_name} (English version)",
                "vi": f"Docstring cho {symbol_name} (Phiên bản tiếng Việt)"
            }