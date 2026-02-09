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
        # Prepare context from search results
        context_text = ""
        if search_results:
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
        else:
            # Fallback to pure generation if no search results provided
            logger.info("No search results provided. Using LLM internal knowledge for generation.")
            system_prompt = """You are a knowledgeable Product Information Specialist. Your task is to generate structured product data based on your internal knowledge.
            
            RULES:
            1. Provide accurate and factual information based on your training data.
            2. If the product is fictional or unknown, provide a best-effort realistic representation or state limitations in the description.
            3. Output MUST be valid JSON matching the specified schema.
            4. Focus on technical specifications, key features, and marketing benefits.
            5. Create a SEO-optimized title and description.
            """

        user_prompt = f"""
        Product Name: {product_name}
        Additional Context: {context if context else 'None'}
        
        Search Results:
        {context_text if context_text else "No external search results available. Please generate data based on your internal knowledge."}
        
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
                temperature=0.7 if not search_results else 0.3, # Higher temp for generation, lower for extraction
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
