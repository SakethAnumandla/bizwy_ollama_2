from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime

# --- Shared Models ---

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
    position: int = 0

class SourceReference(BaseModel):
    """Source URL reference for transparency"""
    url: str
    title: str
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0)

# --- Enrichment Models ---

class EnrichedProductData(BaseModel):
    """Structured enriched product information"""
    detailed_description: str = Field(..., description="Comprehensive description from web sources")
    features: List[str] = Field(default_factory=list, description="Key features")
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Technical specs")
    benefits: List[str] = Field(default_factory=list, description="Product benefits")
    use_cases: List[str] = Field(default_factory=list, description="Common use cases")
    images: List[str] = Field(default_factory=list, description="Product image URLs")
    price_range: Optional[str] = Field(None, description="Price information if found")
    category_hierarchy: List[str] = Field(default_factory=list, description="Category hierarchy")
    tags: List[str] = Field(default_factory=list, description="Relevant tags")
    seo_title: str = Field(..., description="SEO-optimized title")
    seo_description: str = Field(..., description="SEO meta description")

class EnrichmentRequest(BaseModel):
    """Request from main PIMS system"""
    model_config = {"extra": "ignore"}  # Ignore extra fields
    
    product_name: str = Field(..., min_length=1, max_length=500, description="Product name")
    category: Optional[str] = Field(None, description="Product category (helps search)")
    brand: Optional[str] = Field(None, description="Brand name")
    model: Optional[str] = Field(None, description="Model number")
    additional_context: Optional[str] = Field(None, max_length=1000, description="Any additional context")

class EnrichmentResponse(BaseModel):
    """Complete microservice response"""
    success: bool
    product_name: str
    enriched_data: Optional[EnrichedProductData] = None
    sources: List[SourceReference] = Field(default_factory=list, description="Web sources used")
    processing_time: float = Field(0.0, description="Processing time in seconds")
    search_results_count: int = Field(0, description="Number of search results processed")
    cached: bool = Field(default=False, description="Whether result was cached")
    error: Optional[str] = Field(None, description="Error message if failed")

# --- Scraper Models ---

class ProductContent(BaseModel):
    url: str
    title: str
    description: Optional[str] = None
    text_content: str  # cleaned text
    images: List[str] = []
    price: Optional[str] = None
    specifications: Dict[str, Any] = {}
