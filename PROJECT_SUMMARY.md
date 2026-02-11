# PIMS Enrichment – Project Summary & Code Flow

## 1. Project Summary

**PIMS (Product Enrichment Microservice)** is a FastAPI-based microservice that enriches product data from minimal input (name, brand, model) by:

1. **Searching the web** (DuckDuckGo, SerpAPI, or Google) for product info  
2. **Scraping** top result pages for text and metadata  
3. **Synthesizing** structured data with an LLM (OpenAI API or Ollama)

It supports two modes:

- **Search mode**: Search → scrape → LLM synthesis (factual, source-based)  
- **Generative mode**: No search; LLM uses internal knowledge only (when `SEARCH_PROVIDER` is unset or `"none"`)

Tech stack: **FastAPI**, **Pydantic**, **httpx**, **BeautifulSoup**, **OpenAI client** (Ollama-compatible), **SlowAPI** (rate limiting), **Uvicorn**.

---

## 2. How FastAPI Is Wired

### 2.1 Application creation

- **Entry point**: `app/main.py`
- **Factory**: `create_application()` returns a `FastAPI` instance.
- **Singleton**: `app = create_application()` is the ASGI app Uvicorn runs (`uvicorn app.main:app`).

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
         ↑        ↑
      module   app instance
```

### 2.2 What gets registered

| Component        | Purpose |
|-----------------|--------|
| **OpenAPI**     | `openapi_url="/openapi.json"`, `docs_url="/docs"` (Swagger UI) |
| **Rate limiter**| `Limiter` (SlowAPI) with `get_remote_address`; `RateLimitExceeded` handled globally |
| **CORS**        | `CORSMiddleware` from `settings.CORS_ORIGINS` |
| **Router**      | `api_router` included with prefix `settings.API_V1_STR` → `/api/v1` |
| **Health**      | `GET /health` defined on the app (not under API prefix) |

### 2.3 Startup / shutdown

- `@application.on_event("startup")`: logs “Application starting up…”
- `@application.on_event("shutdown")`: logs “Application shutting down…”

(No Redis or other resources initialized yet.)

---

## 3. Routes and How They’re Connected

### 3.1 Route tree

```text
FastAPI app (main.app)
│
├── GET  /health                    → health_check() in main.py
├── GET  /docs                      → Swagger UI (built-in)
├── GET  /openapi.json              → OpenAPI schema (built-in)
│
└── prefix: /api/v1  (api_router from app/api/v1/router.py)
    │
    └── prefix: /products  (enrich.router from endpoints/enrich.py)
        │
        └── POST  /enrich   → enrich_product()  [EnrichmentRequest → EnrichmentResponse]
```

### 3.2 Full URL of the main endpoint

```text
POST /api/v1/products/enrich
```

- **Prefix 1**: `settings.API_V1_STR` = `/api/v1` (in `main.py`: `include_router(api_router, prefix=settings.API_V1_STR)`)
- **Prefix 2**: `/products` (in `router.py`: `include_router(enrich.router, prefix="/products", ...)`)
- **Path**: `/enrich` (in `enrich.py`: `@router.post("/enrich", ...)`)

### 3.3 File → route mapping

| File | What it defines | Mount point |
|------|------------------|------------|
| `app/main.py` | Creates app, CORS, limiter, includes `api_router`, defines `/health` | — |
| `app/api/v1/router.py` | `api_router`, includes `enrich.router` with prefix `/products` | `/api/v1` |
| `app/api/v1/endpoints/enrich.py` | `router` with `POST /enrich` | `/api/v1/products` |

So: **main** includes **v1 router** under `/api/v1`; **v1 router** includes **enrich** under `/products`; **enrich** defines `/enrich`. One route in practice: **POST /api/v1/products/enrich**.

---

## 4. End-to-End Code Flow

### 4.1 Request flow (one diagram)

```text
HTTP POST /api/v1/products/enrich
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  main.app (FastAPI)                                              │
│  CORS → Rate limit check → Router /api/v1                        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  api/v1/router.py  api_router                                    │
│  prefix /products  →  enrich.router                              │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  api/v1/endpoints/enrich.py  enrich_product(request, body)       │
│  • Parse body → EnrichmentRequest (Pydantic)                     │
│  • Call enrichment_service.enrich_product(enrichment_request)    │
│  • Return EnrichmentResponse (200; or 500 on unhandled exception)│
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  services/enrichment_service.py  EnrichmentService               │
│  1. Build search query (product_name + brand + model)            │
│  2. If SEARCH_PROVIDER set: search_service.search(query)         │
│  3. If results: scraper_service.extract_content(url) x N (async) │
│  4. openai_service.synthesize_product_data(name, content, ctx)   │
│  5. Build EnrichmentResponse(success, enriched_data, sources…)   │
└─────────────────────────────────────────────────────────────────┘
    │
    ├──► search_service   → DuckDuckGo / SerpAPI / Google → List[SearchResult]
    ├──► scraper_service  → httpx GET + BeautifulSoup → ProductContent per URL
    └──► openai_service   → OpenAI API (or Ollama) → EnrichedProductData (JSON)
```

### 4.2 Step-by-step (enrich only)

1. **Client** sends `POST /api/v1/products/enrich` with JSON body (e.g. `product_name`, `brand`, `model`).
2. **FastAPI** validates body with **EnrichmentRequest** (Pydantic); invalid body → 422.
3. **enrich_product** (enrich.py) receives the request and calls **enrichment_service.enrich_product**.
4. **EnrichmentService**:
   - Reads **config** (`settings.SEARCH_PROVIDER`, etc.).
   - If search enabled: builds query → **search_service.search(query)** → list of **SearchResult** (title, url, snippet).
   - Takes top N (e.g. 3) URLs → **scraper_service.extract_content(url)** in parallel (`asyncio.gather`) → list of **ProductContent** (and builds **SourceReference** list).
   - Calls **openai_service.synthesize_product_data(product_name, valid_content, additional_context)**:
     - If there is scraped content: system prompt = “extract from sources only”.
     - If no content: system prompt = “generate from internal knowledge”.
     - Sends chat completion (OpenAI/Ollama), expects JSON → parses into **EnrichedProductData**.
   - Builds **EnrichmentResponse** (success, product_name, enriched_data, sources, processing_time, etc.).
5. **enrich_product** returns that response; FastAPI serializes with **EnrichmentResponse** as `response_model`.
6. Any uncaught exception in the endpoint → **HTTP 500** and error log.

### 4.3 Data flow (schemas)

```text
EnrichmentRequest (in)
  product_name, category?, brand?, model?, additional_context?
        │
        ▼
  EnrichmentService
        │
        ├── SearchResult (from search_service)  → url, title, snippet, source, position
        ├── ProductContent (from scraper_service)  → url, title, text_content, images, …
        └── EnrichedProductData (from openai_service)  → detailed_description, features, specifications, …
        │
        ▼
EnrichmentResponse (out)
  success, product_name, enriched_data?, sources[], processing_time, search_results_count, cached, error?
```

---

## 5. Configuration and Environment

- **Source**: `app/config.py` uses **pydantic_settings** with `env_file=".env"`.
- **Important settings**:
  - **API**: `API_V1_STR`, `CORS_ORIGINS`, `API_RATE_LIMIT`
  - **LLM**: `OPENAI_API_KEY`, `OPENAI_BASE_URL` (e.g. `http://localhost:11434/v1` for Ollama), `OPENAI_MODEL_NAME`, `MAX_TOKENS`
  - **Search**: `SEARCH_PROVIDER` (`duckduckgo` | `serpapi` | `googlesearch` | unset/none = no search), `MAX_SEARCH_RESULTS`
  - **Optional API keys**: `SERPAPI_KEY`, `BRAVE_API_KEY`, etc. (SerpAPI not fully implemented)
- **Logging**: `app/core/logging.py` sets up a logger `pims_enrichment` (level from `ENVIRONMENT`), used across services.

---

## 6. Summary Table

| Layer        | File / Component        | Responsibility |
|-------------|--------------------------|----------------|
| **App**     | `main.py`                | Create FastAPI app, CORS, rate limit, mount `/api/v1`, health |
| **Router**  | `api/v1/router.py`       | Mount product routes under `/products` |
| **Endpoint**| `api/v1/endpoints/enrich.py` | `POST /enrich` → enrichment service → response |
| **Orchestration** | `services/enrichment_service.py` | Search → scrape → LLM → EnrichmentResponse |
| **Search**  | `services/search_service.py` | DuckDuckGo (HTML/scraper) or Google/SerpAPI stubs |
| **Scrape**  | `services/scraper_service.py` | httpx + BeautifulSoup → ProductContent |
| **LLM**     | `services/openai_service.py` | OpenAI client → JSON → EnrichedProductData |
| **Models**  | `models/schemas.py`      | EnrichmentRequest, EnrichmentResponse, EnrichedProductData, etc. |
| **Config**  | `config.py`              | Settings from `.env` |

**Single main route**: **POST /api/v1/products/enrich** — everything else (health, docs, openapi) is supporting. FastAPI ties together config, routers, and services so that one HTTP call flows: **main → api_router → enrich router → enrichment_service → search / scraper / openai_service** and back as **EnrichmentResponse**.
