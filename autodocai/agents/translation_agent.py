"""
Translation agent for AutoDoc AI.

This agent handles translation of content from English to Vietnamese,
ensuring multilingual documentation support.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

import aiohttp
from pydantic import BaseModel

from autodocai.agents.base import BaseAgent
from autodocai.schemas import MessageType


class TranslationAgent(BaseAgent):
    """Agent for translating content from English to Vietnamese.
    
    This agent processes English content (summaries, explanations, etc.) and
    translates it to Vietnamese using AI models via OpenRouter.
    """
    
    async def _execute(self, state: Union[Dict[str, Any], BaseModel]) -> Union[Dict[str, Any], BaseModel]:
        """Execute the translation process.
        
        Args:
            state: Current workflow state (dictionary or Pydantic model)
            
        Returns:
            Union[Dict[str, Any], BaseModel]: Updated workflow state with translated content
        """
        # Check if Vietnamese translation is needed
        if "VI" not in self.config.output_languages:
            self.logger.info("Vietnamese translation not requested, skipping")
            return state
        
        self.logger.info("Starting translation to Vietnamese")
        self._add_message(state, MessageType.INFO, "Starting translation to Vietnamese")
        
        # Initialize translations dictionary
        translations = {}
        
        # Translate summaries using helper method to access state
        summaries = self.get_state_value(state, "summaries", {})
        if summaries:
            self.logger.info(f"Translating {len(summaries)} code summaries")
            translated_summaries = await self._translate_summaries(summaries)
            translations["summaries"] = translated_summaries
        
        # Translate RAG results using helper method to access state
        rag_results = self.get_state_value(state, "rag_results", {})
        if rag_results:
            self.logger.info("Translating architectural overview and module explanations")
            
            # Translate architectural overview
            arch_overview = rag_results.get("architectural_overview", {})
            if arch_overview and "en" in arch_overview and "vi" not in arch_overview:
                vi_overview = await self._translate_text(arch_overview["en"], "architectural_overview")
                if vi_overview:
                    arch_overview["vi"] = vi_overview
            
            # Translate module explanations
            module_explanations = rag_results.get("module_explanations", {})
            translated_explanations = {}
            
            for path, explanation in module_explanations.items():
                if "en" in explanation and "vi" not in explanation:
                    vi_explanation = await self._translate_text(explanation["en"], f"module_explanation_{path}")
                    if vi_explanation:
                        explanation["vi"] = vi_explanation
                translated_explanations[path] = explanation
            
            rag_results["module_explanations"] = translated_explanations
            translations["rag_results"] = rag_results
        
        # Add translations to state using the helper method
        self.set_state_value(state, "translations", translations)
        
        # Update current stage
        self.set_state_value(state, "current_stage", "translation_complete")
        
        self.logger.info("Completed Vietnamese translation")
        self._add_message(state, MessageType.SUCCESS, "Completed Vietnamese translation")
        
        return state
    
    async def _translate_summaries(self, summaries: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """Translate code summaries from English to Vietnamese.
        
        Args:
            summaries: Dictionary of summaries by snippet ID
            
        Returns:
            Dict[str, Dict[str, str]]: Translated summaries
        """
        translated_summaries = {}
        batch_size = 5
        total_processed = 0
        
        # Get list of summaries that need translation
        to_translate = []
        for snippet_id, summary in summaries.items():
            if "en" in summary and "vi" not in summary:
                to_translate.append((snippet_id, summary["en"]))
        
        self.logger.info(f"Found {len(to_translate)} summaries to translate")
        
        # Process summaries in batches
        for i in range(0, len(to_translate), batch_size):
            batch = to_translate[i:i+batch_size]
            
            # Process batch concurrently
            tasks = []
            for snippet_id, text in batch:
                tasks.append(self._translate_text(text, f"summary_{snippet_id}"))
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, (snippet_id, _) in enumerate(batch):
                result = batch_results[j]
                
                if isinstance(result, Exception):
                    self.logger.warning(f"Error translating summary {snippet_id}: {str(result)}")
                    continue
                
                if result:
                    # Copy original summary
                    translated_summaries[snippet_id] = {
                        "en": summaries[snippet_id]["en"],
                        "vi": result
                    }
                    
                    total_processed += 1
            
            # Log progress
            self.logger.info(f"Translated {total_processed} of {len(to_translate)} summaries")
        
        # Add any summaries that already have translations
        for snippet_id, summary in summaries.items():
            if snippet_id not in translated_summaries and "vi" in summary:
                translated_summaries[snippet_id] = summary
        
        return translated_summaries
    
    async def _translate_text(self, text: str, context: str = "") -> Optional[str]:
        """Translate text from English to Vietnamese.
        
        Args:
            text: Text to translate
            context: Context of the translation (for logging)
            
        Returns:
            Optional[str]: Translated text or None if translation fails
        """
        try:
            # Skip if text is empty
            if not text.strip():
                return ""
            
            # Get API key from config
            api_key = self.config.openrouter_api_key
            if not api_key:
                raise ValueError("OpenRouter API key is not configured")
            
            # Get model name from config
            model = self.config.translation_model_name
            
            # Prepare prompt
            prompt = f"""
Translate the following English text to Vietnamese. 
Maintain the technical meaning and formatting (including Markdown if present).
Use appropriate Vietnamese technical terminology.

TEXT TO TRANSLATE:
{text}

VIETNAMESE TRANSLATION:
"""
            
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
                    {"role": "system", "content": "You are a technical translator with expertise in software development and programming. Your task is to translate English technical content to Vietnamese with high accuracy."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": min(len(text.split()) * 2, 2048)  # Roughly estimate tokens needed
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
                    translation = data["choices"][0]["message"]["content"]
            
            # Clean up the response
            # Remove any "VIETNAMESE TRANSLATION:" prefix if present
            translation = translation.replace("VIETNAMESE TRANSLATION:", "").strip()
            
            return translation
            
        except Exception as e:
            self.logger.error(f"Error translating text ({context}): {str(e)}")
            return None
