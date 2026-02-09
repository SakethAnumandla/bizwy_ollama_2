# Product Enrichment Microservice (PIMS)

A high-performance microservice designed to enrich product data using a combination of web search, intelligent scraping, and LLM-powered synthesis.

## 🚀 Key Features

*   **Intelligent Enrichment**: Takes basic product info (name, brand) and returns detailed specifications, features, and descriptions.
*   **Dual Operation Modes**:
    *   **Search Mode**: Uses live web search results (DuckDuckGo, SerpAPI, etc.) to synthesize factual data.
    *   **Generative Mode**: Falls back to LLM internal knowledge if search is disabled or returns no results.
*   **Robust Architecture**: Async-first design with FastAPI, rate limiting, and structured logging.
*   **Flexible Search**: Supports multiple providers (DuckDuckGo HTML scraper included by default).
*   **Production Ready**: Includes Pydantic validation, error handling, and Docker support (coming soon).

## 📋 Prerequisites

*   **Python 3.10+**
*   **Ollama** (for local LLM inference) or an OpenAI API Key.
    *   Recommended Model: `llama3`, `mistral`, or `openhermes`.

## 🛠️ Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-org/pims-enrichment.git
    cd pims-enrichment
    ```

2.  **Create a Virtual Environment**
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # Linux/Mac
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment**
    Copy the example configuration file:
    ```bash
    # Windows
    copy .env.example .env
    
    # Linux/Mac
    cp .env.example .env
    ```
    
    Open `.env` and configure the settings:
    *   **LLM Setup**: Set `OPENAI_BASE_URL` (e.g., `http://localhost:11434/v1` for Ollama) and `OPENAI_MODEL_NAME`.
    *   **Search Setup**: Set `SEARCH_PROVIDER=duckduckgo` (default) or providing API keys for SerpAPI/Brave.
    *   **Generative Mode**: To use **ONLY** the LLM (no search), comment out `SEARCH_PROVIDER` or leave it blank.

## 🚀 Running the Application

Start the server using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.

## 📡 Usage

### Enrich a Product

**Endpoint**: `POST /api/v1/products/enrich`

**Example Request (Curl)**:
```bash
curl -X POST "http://localhost:8000/api/v1/products/enrich" \
     -H "Content-Type: application/json" \
     -d '{
           "product_name": "iPhone 15 Pro",
           "brand": "Apple",
           "model": "A2848"
         }'
```

**Example Request (PowerShell)**:
```powershell
$body = @{
    product_name = "iPhone 15 Pro"
    brand = "Apple"
    model = "A2848"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/products/enrich" -Method Post -Body $body -ContentType "application/json"
```

### Response Check
You can check the health of the service at:
`GET http://localhost:8000/health`

## 📚 Documentation
Interactive API documentation (Swagger UI) is available at:
`http://localhost:8000/docs`
