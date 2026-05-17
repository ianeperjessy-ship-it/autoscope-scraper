from fastapi import FastAPI, Query
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
    "Accept": "application/json",
    "Accept-Language": "ro-RO,ro;q=0.9",
    "Referer": "https://www.olx.ro/auto-masini-moto-ambarcatiuni/autoturisme/",
    "Origin": "https://www.olx.ro",
}

@app.get("/")
def root():
    return {"status": "AutoScope Scraper running"}

@app.get("/search")
async def search(
    make: Optional[str] = None,
    model: Optional[str] = None,
    min_price: Optional[str] = None,
    max_price: Optional[str] = None,
    min_year: Optional[str] = None,
    max_year: Optional[str] = None,
):
    query = " ".join(filter(None, [make, model]))
    
    params = {
        "offset": "0",
        "limit": "20",
        "category_id": "108",
        "sort_by": "price:asc",
    }
    
    if query:
        params["query"] = query
    if min_price:
        params["filter_float_price:from"] = min_price
    if max_price:
        params["filter_float_price:to"] = max_price

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://www.olx.ro/api/v1/offers/",
            params=params,
            headers=HEADERS,
        )
        
        if response.status_code != 200:
            return {"error": f"OLX returned {response.status_code}", "listings": []}
        
        data = response.json()
        items = data.get("data", [])
        
        listings = []
        for item in items:
            params_list = item.get("params", [])
            
            def get_param(key):
                for p in params_list:
                    if p.get("key") == key:
                        return p.get("value", {}).get("label") or p.get("value", {}).get("value")
                return None
            
            price_param = next((p for p in params_list if p.get("key") == "price"), None)
            price = None
            currency = "EUR"
            if price_param:
                price = price_param.get("value", {}).get("value")
                currency = price_param.get("value", {}).get("currency", "EUR")
            
            photos = item.get("photos", [])
            image = None
            if photos:
                link = photos[0].get("link", "")
                image = link.replace("{width}", "400").replace("{height}", "300")
            
            listings.append({
                "title": item.get("title", "Anunț OLX"),
                "url": item.get("url", ""),
                "price": price,
                "currency": currency,
                "image": image,
                "year": get_param("year"),
                "mileage": get_param("mileage"),
                "fuelType": get_param("fuel"),
                "location": item.get("location", {}).get("city", {}).get("name"),
            })
        
        return {"listings": listings, "count": len(listings)}
