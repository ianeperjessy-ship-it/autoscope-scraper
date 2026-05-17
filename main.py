from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
    "Referer": "https://www.olx.ro/",
}

@app.get("/")
def root():
    return {"status": "AutoScope Scraper running OK"}

@app.get("/search")
async def search(
    make: Optional[str] = None,
    model: Optional[str] = None,
    min_price: Optional[str] = None,
    max_price: Optional[str] = None,
):
    query = " ".join(filter(None, [make, model]))
    
    # Try different category IDs
    for cat_id in ["84", "108", "5", "271"]:
        params = {
            "offset": "0",
            "limit": "20",
            "sort_by": "price:asc",
            "category_id": cat_id,
        }
        if query:
            params["query"] = query
        if min_price:
            params["filter_float_price:from"] = min_price
        if max_price:
            params["filter_float_price:to"] = max_price

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(
                "https://www.olx.ro/api/v1/offers/",
                params=params,
                headers=HEADERS,
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", [])
                listings = []
                for item in items:
                    params_list = item.get("params", [])
                    price_p = next((p for p in params_list if p.get("key") == "price"), None)
                    price = price_p.get("value", {}).get("value") if price_p else None
                    currency = price_p.get("value", {}).get("currency", "EUR") if price_p else "EUR"
                    photos = item.get("photos", [])
                    image = photos[0].get("link", "").replace("{width}", "400").replace("{height}", "300") if photos else None
                    def get_p(key):
                        for p in params_list:
                            if p.get("key") == key:
                                v = p.get("value", {})
                                return v.get("label") or v.get("value")
                        return None
                    listings.append({
                        "title": item.get("title", "Anunț OLX"),
                        "url": item.get("url", ""),
                        "price": price,
                        "currency": currency,
                        "image": image,
                        "year": get_p("year"),
                        "mileage": get_p("mileage"),
                        "fuelType": get_p("fuel"),
                        "location": item.get("location", {}).get("city", {}).get("name"),
                    })
                return {"listings": listings, "count": len(listings), "category_used": cat_id}
    
    return {"error": "All categories failed", "listings": []}
