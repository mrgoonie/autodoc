"""
Summarizer agent for AutoDoc AI.

This agent generates concise, informative summaries of code snippets using AI models via OpenRouter.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp

from autodocai.agents.base import BaseAgent
from autodocai.schemas import CodeSnippet, MessageType


class SummarizerAgent(BaseAgent):
    """Agent for summarizing code snippets using AI.
    
    This agent processes code snippets and generates human-readable summaries
    using AI models via OpenRouter. It handles batching and concurrency to
    efficiently process multiple snippets.
    """
    
    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the code summarization process.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict[str, Any]: Updated workflow state with code summaries
        """
        # Get snippets from state
        snippets = state.get("snippets", [])
        if not snippets:
            self.logger.warning("No code snippets to summarize")
            self._add_message(state, MessageType.WARNING, "No code snippets to summarize")
            return state
        
        self.logger.info(f"Starting summarization of {len(snippets)} code snippets")
        self._add_message(state, MessageType.INFO, f"Starting summarization of {len(snippets)} code snippets")
        
        # Initialize summaries dictionary
        summaries = {}
        
        # Process snippets in batches
        batch_size = 10
        total_processed = 0
        
        for i in range(0, len(snippets), batch_size):
            batch = snippets[i:i+batch_size]
            
            # Process batch concurrently
            tasks = [self._summarize_snippet(snippet) for snippet in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for snippet, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Error summarizing snippet {snippet.id}: {str(result)}")
                    continue
                
                if result:
                    # Update snippet with summaries
                    snippet.ai_summary_en = result.get("en")
                    
                    # Add to summaries dictionary
                    summaries[snippet.id] = {
                        "en": result.get("en"),
                        "vi": result.get("vi")
                    }
                    
                    total_processed += 1
            
            # Log progress
            self.logger.info(f"Processed {total_processed} of {len(snippets)} snippets")
        
        # Update state
        state["summaries"] = summaries
        
        self.logger.info(f"Completed summarization: {total_processed} snippets summarized")
        self._add_message(
            state, 
            MessageType.SUCCESS, 
            f"Completed summarization: {total_processed} snippets summarized"
        )
        
        return state
    
    async def _summarize_snippet(self, snippet: CodeSnippet) -> Optional[Dict[str, str]]:
        """Summarize a code snippet using OpenRouter AI.
        
        Args:
            snippet: Code snippet to summarize
            
        Returns:
            Optional[Dict[str, str]]: Summaries in English and Vietnamese (if requested)
        """
        # Skip if snippet already has a summary
        if snippet.ai_summary_en:
            return {
                "en": snippet.ai_summary_en,
                "vi": snippet.ai_summary_vi
            }
        
        try:
            # Get API key from config
            api_key = self.config.openrouter_api_key
            if not api_key:
                raise ValueError("OpenRouter API key is not configured")
            
            # Get model name from config
            model = self.config.summarizer_model_name
            
            # Prepare prompt
            prompt = self._create_summarization_prompt(snippet)
            
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
                    {"role": "system", "content": "You are a technical documentation expert specializing in code analysis and explanation. Your task is to provide clear, concise summaries of code snippets."},
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
            
            # Parse response to extract summaries
            summaries = self._parse_summary_response(content)
            
            return summaries
            
        except Exception as e:
            self.logger.error(f"Error summarizing snippet {snippet.id}: {str(e)}")
            raise
    
    def _create_summarization_prompt(self, snippet: CodeSnippet) -> str:
        """Create a prompt for code summarization.
        
        Args:
            snippet: Code snippet to summarize
            
        Returns:
            str: Prompt for the AI model
        """
        languages_needed = self.config.output_languages
        
        prompt = f"""
Please analyze the following {snippet.language.upper()} code snippet and provide a clear, concise summary of its purpose and functionality.

CODE SNIPPET ({snippet.symbol_type}):
```{snippet.language}
{snippet.text_content}
```

EXISTING DOCSTRING:
{snippet.original_docstring or "None"}

Please provide:
1. A concise summary of what this code does (2-3 sentences)
2. Key functionality and features
3. Important parameters or dependencies

Format your response as follows:

## SUMMARY_EN
[Your detailed English summary here]
"""

        if "VI" in languages_needed:
            prompt += "\n\n## SUMMARY_VI\n[Your detailed Vietnamese summary here - ensure proper technical terminology]"
        
        return prompt
    
    def _parse_summary_response(self, response: str) -> Dict[str, str]:
        """Parse the AI response to extract summaries.
        
        Args:
            response: AI model response
            
        Returns:
            Dict[str, str]: Summaries in requested languages
        """
        summaries = {}
        
        # Extract English summary
        if "## SUMMARY_EN" in response:
            parts = response.split("## SUMMARY_EN")
            if len(parts) > 1:
                en_part = parts[1].strip()
                if "## SUMMARY_VI" in en_part:
                    en_part = en_part.split("## SUMMARY_VI")[0].strip()
                summaries["en"] = en_part
        else:
            # If no specific format, use the entire response as English summary
            summaries["en"] = response.strip()
        
        # Extract Vietnamese summary if available
        if "## SUMMARY_VI" in response:
            parts = response.split("## SUMMARY_VI")
            if len(parts) > 1:
                summaries["vi"] = parts[1].strip()
        
        return summaries
