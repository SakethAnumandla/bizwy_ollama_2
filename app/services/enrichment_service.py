import asyncio
import time
from typing import List, Optional
from app.models.schemas import EnrichmentRequest, EnrichmentResponse, EnrichedProductData, SourceReference
from app.services.search_service import search_service
from app.services.scraper_service import scraper_service
from app.services.openai_service import openai_service
from app.core import logging

logger = logging.logger

class EnrichmentService:
    async def enrich_product(self, request: EnrichmentRequest) -> EnrichmentResponse:
        start_time = time.time()
        logger.info(f"Starting enrichment for: {request.product_name}")
        
        try:
            # 1. Search Query construction
            from app.config import settings
            
            search_results = []
            valid_content = []
            
            # Check if search is enabled
            if settings.SEARCH_PROVIDER and settings.SEARCH_PROVIDER.lower() != "none":
                query = f"{request.product_name}"
                if request.brand:
                    query += f" {request.brand}"
                if request.model:
                    query += f" {request.model}"
                
                # 2. Perform Web Search
                logger.info(f"Calling search_service.search with query: '{query}'")
                
                search_results = await search_service.search(query)
                
                logger.info(f"Search returned {len(search_results) if search_results else 0} results")
                
                if search_results:
                    # 3. Scrape Top Results (e.g., top 3-4 deep scrape)
                    # Use asyncio.gather for parallel scraping
                    scrape_tasks = []
                    sources = []
                    
                    # Filter results to avoid generic pages if possible (e.g. Amazon listing vs generic search page)
                    # For now, just take top 3 results
                    results_to_scrape = search_results[:3]
                    
                    for result in results_to_scrape:
                        scrape_tasks.append(scraper_service.extract_content(result.url))
                        sources.append(SourceReference(url=result.url, title=result.title, relevance_score=1.0 - (result.position * 0.1)))
        
                    scraped_content = await asyncio.gather(*scrape_tasks, return_exceptions=True)
                    
                    # Filter failed scrapes
                    valid_content = [c for c in scraped_content if c and not isinstance(c, Exception)]
                else:
                    logger.warning("Search returned no results, proceeding to LLM generation only")
            else:
                logger.info("Search provider not configured, skipping search and using LLM generation only")

            # 4. Synthesize with LLM
            enriched_data = await openai_service.synthesize_product_data(
                product_name=request.product_name,
                search_results=valid_content,
                context=request.additional_context
            )
            
            # 5. Construct Response
            processing_time = time.time() - start_time
            logger.info(f"Enrichment completed in {processing_time:.2f}s")
            
            return EnrichmentResponse(
                success=True,
                product_name=request.product_name,
                enriched_data=enriched_data,
                sources=sources,
                search_results_count=len(search_results),
                processing_time=processing_time,
                cached=False
            )

        except Exception as e:
            logger.error(f"Enrichment process failed: {str(e)}", exc_info=True)
            return EnrichmentResponse(
                success=False,
                product_name=request.product_name,
                error=f"Internal processing error: {str(e)}",
                processing_time=time.time() - start_time
            )

enrichment_service = EnrichmentService()
