import json
import asyncio
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
from app.config import settings
from app.core import logging
from app.models.schemas import ProductContent, EnrichedProductData

logger = logging.logger

class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL_NAME
        self.max_tokens = settings.MAX_TOKENS

    async def synthesize_product_data(
        self,
        product_name: str,
        search_results: List[ProductContent],
        context: Optional[str] = None
    ) -> EnrichedProductData:
        """
        Synthesize structured product data from search results using LLM.
        """
        if not search_results:
            raise ValueError("No search results provided for synthesis")

        # Prepare context from search results
        context_text = ""
        for i, result in enumerate(search_results):
            context_text += f"\n--- Source {i+1}: {result.url} ---\n"
            context_text += f"Title: {result.title}\n"
            context_text += f"Content: {result.text_content[:2000]}...\n" # Truncate to avoid context limit

        system_prompt = """You are a precise Product Information Specialist. Your task is to extract and synthesize structured product data from the provided web search results.
        
        RULES:
        1. ONLY use information found in the provided sources. Do not hallucinate features.
        2. If information is missing (e.g., price), explicitly state it or leave it null.
        3. Output MUST be valid JSON matching the specified schema.
        4. Focus on technical specifications, key features, and marketing benefits.
        5. Create a SEO-optimized title and description based on the finding.
        """

        user_prompt = f"""
        Product Name: {product_name}
        Additional Context: {context if context else 'None'}
        
        Search Results:
        {context_text}
        
        Please synthesize this information into the following JSON structure:
        {{
            "detailed_description": "Comprehensive description...",
            "features": ["feature 1", "feature 2"],
            "specifications": {{"spec_name": "value"}},
            "benefits": ["benefit 1", "benefit 2"],
            "use_cases": ["use case 1", "use case 2"],
            "images": ["url1", "url2"],
            "price_range": "$X - $Y (or null)",
            "category_hierarchy": ["Category", "Subcategory"],
            "tags": ["tag1", "tag2"],
            "seo_title": "SEO Title",
            "seo_description": "SEO Description"
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3, # Low temperature for factual extraction
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")
                
            data = json.loads(content)
            
            # Validate and clean data using Pydantic model
            # This ensures we return expected structure even if LLM missed some optional fields
            return EnrichedProductData(**data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            # Fallback or retry logic could go here
            raise ValueError("LLM returned invalid JSON")
        except Exception as e:
            logger.error(f"OpenAI synthesis failed: {e}")
            raise

openai_service = OpenAIService()
