import asyncio
import time
from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import (
    EnrichmentRequest,
    EnrichmentResponse,
    BatchEnrichmentRequest,
    BatchEnrichmentResponse,
)
from app.services.enrichment_service import enrichment_service
from app.core import logging

router = APIRouter()
logger = logging.logger

# Rate limiting (get limiter from app state if needed, or use global)
# For simplicity, we can rely on main.py limiter if attached to request state
# or just import a global limiter if defined in dependencies.
# Here we'll just use the service.

@router.post("/enrich", response_model=EnrichmentResponse)
async def enrich_product(
    request: Request,
    enrichment_request: EnrichmentRequest,
):
    """
    Enrich product data using minimal input information.
    
    1. Searches the web for product details
    2. Scrapes relevant content
    3. Uses LLM to synthesize structured data
    4. Returns comprehensive product information
    """
    try:
        # Rate limiting check could go here if using slowapi decorator
        
        response = await enrichment_service.enrich_product(enrichment_request)
        
        if not response.success:
            # We return 200 even on logical failure, but with success=False
            # Alternatively, we could raise HTTPException based on error type
            logger.warning(f"Enrichment failed for {enrichment_request.product_name}: {response.error}")
            
        return response
        
    except Exception as e:
        logger.error(f"Unexpected error in enrichment endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error processing enrichment request")


@router.post("/enrich/batch", response_model=BatchEnrichmentResponse)
async def enrich_products_batch(request: Request, batch_request: BatchEnrichmentRequest):
    """
    Enrich multiple products in one request. Each product is enriched in parallel
    (search → scrape → LLM). Returns one result per product plus summary.
    """
    start_time = time.time()
    try:
        tasks = [
            enrichment_service.enrich_product(product)
            for product in batch_request.products
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        normalized = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(
                    f"Batch item failed for {batch_request.products[i].product_name}: {r}",
                    exc_info=True,
                )
                normalized.append(
                    EnrichmentResponse(
                        success=False,
                        product_name=batch_request.products[i].product_name,
                        error=str(r),
                    )
                )
            else:
                normalized.append(r)
                if not r.success:
                    logger.warning(f"Enrichment failed for {r.product_name}: {r.error}")

        total = len(normalized)
        succeeded = sum(1 for x in normalized if x.success)
        failed = total - succeeded
        total_processing_time = round(time.time() - start_time, 2)

        return BatchEnrichmentResponse(
            results=normalized,
            total=total,
            succeeded=succeeded,
            failed=failed,
            total_processing_time=total_processing_time,
        )
    except Exception as e:
        logger.error(f"Unexpected error in batch enrichment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing batch enrichment request",
        )
