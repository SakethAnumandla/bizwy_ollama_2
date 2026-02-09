from fastapi import APIRouter, Depends, HTTPException, Request
from app.models.schemas import EnrichmentRequest, EnrichmentResponse
from app.services.enrichment_service import enrichment_service
from app.core import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

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
