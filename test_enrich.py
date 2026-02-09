import requests
import json

url = "http://localhost:8000/api/v1/products/enrich"
data = {
    "product_name": "iPhone 15 Pro",
    "brand": "Apple"
}

try:
    response = requests.post(url, json=data, timeout=60)
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
