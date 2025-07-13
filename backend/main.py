import asyncio
import sqlite3
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import json
import random
from datetime import datetime

import aiohttp
import aiosqlite
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# Pydantic Models
class APIEndpoint(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class APIEndpointUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    is_active: Optional[bool] = None


class PriceComparisonRequest(BaseModel):
    upc: str = Field(..., min_length=1, max_length=50)


class PriceResult(BaseModel):
    merchant: str
    price: Optional[float] = None
    url: Optional[str] = None
    error: Optional[str] = None
    in_stock: Optional[bool] = None


class PriceComparisonResponse(BaseModel):
    upc: str
    results: List[PriceResult]
    best_price: Optional[float]
    best_merchant: Optional[str]
    best_url: Optional[str]
    comparison_time: str


# Database setup
DATABASE_URL = "api_endpoints.db"


async def init_db():
    """Initialize the database with default API endpoints"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_endpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if we have any endpoints
        cursor = await db.execute("SELECT COUNT(*) FROM api_endpoints")
        count = await cursor.fetchone()
        
        if count[0] == 0:
            # Insert default endpoints
            default_endpoints = [
                {
                    "name": "Appedia",
                    "url": "https://appedia.heb-platform-interview.hebdigital-prd.com/api/v1/itemdata?upc={upc}"
                },
                {
                    "name": "Micromazon",
                    "url": "https://micromazon.heb-platform-interview.hebdigital-prd.com/{upc}/productinfo"
                },
                {
                    "name": "Googdit",
                    "url": "https://googdit.heb-platform-interview.hebdigital-prd.com/{upc}"
                }
            ]
            
            for endpoint in default_endpoints:
                await db.execute("""
                    INSERT INTO api_endpoints (name, url, is_active)
                    VALUES (?, ?, ?)
                """, (
                    endpoint["name"],
                    endpoint["url"],
                    True
                ))
            
            await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


# FastAPI app
app = FastAPI(
    title="Price Comparison Tool API",
    description="A comprehensive API for comparing prices across multiple merchants",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3010", "http://127.0.0.1:3010"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database dependency
async def get_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        yield db


# API Endpoints CRUD Operations
@app.get("/api/endpoints", response_model=List[APIEndpoint])
async def get_endpoints(db: aiosqlite.Connection = Depends(get_db)):
    """Get all API endpoints"""
    cursor = await db.execute("SELECT * FROM api_endpoints ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    
    endpoints = []
    for row in rows:
        endpoint = APIEndpoint(
            id=row[0],
            name=row[1],
            url=row[2],
            is_active=bool(row[3]),
            created_at=row[4],
            updated_at=row[5]
        )
        endpoints.append(endpoint)
    
    return endpoints


@app.get("/api/endpoints/{endpoint_id}", response_model=APIEndpoint)
async def get_endpoint(endpoint_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Get a specific API endpoint"""
    cursor = await db.execute("SELECT * FROM api_endpoints WHERE id = ?", (endpoint_id,))
    row = await cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return APIEndpoint(
        id=row[0],
        name=row[1],
        url=row[2],
        is_active=bool(row[3]),
        created_at=row[4],
        updated_at=row[5]
    )


@app.post("/api/endpoints", response_model=APIEndpoint)
async def create_endpoint(endpoint: APIEndpoint, db: aiosqlite.Connection = Depends(get_db)):
    """Create a new API endpoint"""
    cursor = await db.execute("""
        INSERT INTO api_endpoints (name, url, is_active)
        VALUES (?, ?, ?)
    """, (
        endpoint.name,
        endpoint.url,
        endpoint.is_active
    ))
    
    await db.commit()
    endpoint_id = cursor.lastrowid
    
    # Fetch the created endpoint
    cursor = await db.execute("SELECT * FROM api_endpoints WHERE id = ?", (endpoint_id,))
    row = await cursor.fetchone()
    
    return APIEndpoint(
        id=row[0],
        name=row[1],
        url=row[2],
        is_active=bool(row[3]),
        created_at=row[4],
        updated_at=row[5]
    )


@app.put("/api/endpoints/{endpoint_id}", response_model=APIEndpoint)
async def update_endpoint(
    endpoint_id: int,
    endpoint_update: APIEndpointUpdate,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Update an existing API endpoint"""
    # Check if endpoint exists
    cursor = await db.execute("SELECT * FROM api_endpoints WHERE id = ?", (endpoint_id,))
    existing = await cursor.fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Prepare update data
    update_data = {}
    if endpoint_update.name is not None:
        update_data["name"] = endpoint_update.name
    if endpoint_update.url is not None:
        update_data["url"] = endpoint_update.url
    if endpoint_update.is_active is not None:
        update_data["is_active"] = endpoint_update.is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Build update query
    set_clauses = []
    values = []
    for key, value in update_data.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)
    
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    values.append(endpoint_id)
    
    query = f"UPDATE api_endpoints SET {', '.join(set_clauses)} WHERE id = ?"
    await db.execute(query, values)
    await db.commit()
    
    # Fetch updated endpoint
    cursor = await db.execute("SELECT * FROM api_endpoints WHERE id = ?", (endpoint_id,))
    row = await cursor.fetchone()
    
    return APIEndpoint(
        id=row[0],
        name=row[1],
        url=row[2],
        is_active=bool(row[3]),
        created_at=row[4],
        updated_at=row[5]
    )


@app.delete("/api/endpoints/{endpoint_id}")
async def delete_endpoint(endpoint_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Delete an API endpoint"""
    cursor = await db.execute("SELECT * FROM api_endpoints WHERE id = ?", (endpoint_id,))
    existing = await cursor.fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    await db.execute("DELETE FROM api_endpoints WHERE id = ?", (endpoint_id,))
    await db.commit()
    
    return {"message": "Endpoint deleted successfully"}


@app.patch("/api/endpoints/{endpoint_id}/toggle")
async def toggle_endpoint(endpoint_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Toggle an API endpoint's active status"""
    cursor = await db.execute("SELECT is_active FROM api_endpoints WHERE id = ?", (endpoint_id,))
    row = await cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    new_status = not bool(row[0])
    await db.execute(
        "UPDATE api_endpoints SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_status, endpoint_id)
    )
    await db.commit()
    
    return {"message": f"Endpoint {'activated' if new_status else 'deactivated'} successfully"}


# Price Comparison Service
async def fetch_price_from_api(session: aiohttp.ClientSession, endpoint: APIEndpoint, upc: str) -> PriceResult:
    """Fetch price from a single API endpoint"""
    try:
        # Replace UPC placeholder in URL
        url = endpoint.url.replace("{upc}", upc)
        
        # Log the URL being requested
        print(f"[PRICE_FETCH] Requesting URL for {endpoint.name}: {url}")
        
        # Make API request with timeout
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                
                # Parse response based on endpoint type
                price, in_stock = parse_api_response(endpoint.name, data)
                
                if price is not None and in_stock:
                    result = PriceResult(
                        merchant=endpoint.name,
                        price=price,
                        url=url,
                        in_stock=True
                    )
                    print(f"[PRICE_RESULT] {endpoint.name}: SUCCESS - Price: ${price:.2f}, In Stock: {in_stock}")
                    return result
                elif price is not None and not in_stock:
                    result = PriceResult(
                        merchant=endpoint.name,
                        price=price,
                        url=url,
                        in_stock=False,
                        error="Out of stock"
                    )
                    print(f"[PRICE_RESULT] {endpoint.name}: OUT OF STOCK - Price: ${price:.2f}")
                    return result
                else:
                    result = PriceResult(
                        merchant=endpoint.name,
                        price=None,
                        url=None,
                        error="Invalid response format"
                    )
                    print(f"[PRICE_RESULT] {endpoint.name}: ERROR - Invalid response format")
                    return result
            else:
                result = PriceResult(
                    merchant=endpoint.name,
                    price=None,
                    url=None,
                    error=f"HTTP {response.status}"
                )
                print(f"[PRICE_RESULT] {endpoint.name}: ERROR - HTTP {response.status}")
                return result
                
    except asyncio.TimeoutError:
        result = PriceResult(
            merchant=endpoint.name,
            price=None,
            url=None,
            error="Request timeout"
        )
        print(f"[PRICE_RESULT] {endpoint.name}: ERROR - Request timeout")
        return result
    except Exception as e:
        result = PriceResult(
            merchant=endpoint.name,
            price=None,
            url=None,
            error=str(e)
        )
        print(f"[PRICE_RESULT] {endpoint.name}: ERROR - Exception: {str(e)}")
        return result


def parse_api_response(merchant_name: str, data: dict) -> tuple[Optional[float], bool]:
    """Parse API response based on merchant type"""
    try:
        if merchant_name.lower() == "appedia":
            # Appedia format: {"price": "$4.77", "stock": 7}
            price_str = data.get("price", "")
            stock = data.get("stock", 0)
            
            # Parse price string (remove $ and convert to float)
            if price_str and price_str.startswith("$"):
                price = float(price_str[1:])
                in_stock = stock > 0
                return price, in_stock
                
        elif merchant_name.lower() == "micromazon":
            # Micromazon format: {"available": true, "price": 5.67}
            available = data.get("available", False)
            price = data.get("price")
            
            if price is not None and isinstance(price, (int, float)):
                return float(price), available
                
        elif merchant_name.lower() == "googdit":
            # Googdit format: {"a": [{"l": 8839, "q": 4}, {"l": 1292, "q": 0}], "p": 478000000}
            price_microcents = data.get("p")
            availability_array = data.get("a", [])
            
            if price_microcents is not None:
                # Convert microcents to dollars
                price = price_microcents / 100000000.0
                
                # Check if in stock at any location
                in_stock = any(item.get("q", 0) > 0 for item in availability_array)
                
                return price, in_stock
                
    except (ValueError, TypeError, KeyError) as e:
        print(f"Error parsing {merchant_name} response: {e}")
        
    return None, False


@app.post("/api/compare", response_model=PriceComparisonResponse)
async def compare_prices(
    request: PriceComparisonRequest,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Compare prices across all active API endpoints"""
    # Get active endpoints
    cursor = await db.execute("SELECT * FROM api_endpoints WHERE is_active = TRUE")
    rows = await cursor.fetchall()
    
    if not rows:
        raise HTTPException(status_code=400, detail="No active API endpoints configured")
    
    endpoints = []
    for row in rows:
        endpoint = APIEndpoint(
            id=row[0],
            name=row[1],
            url=row[2],
            is_active=bool(row[3]),
            created_at=row[4],
            updated_at=row[5]
        )
        endpoints.append(endpoint)
    
    # Fetch prices concurrently
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_price_from_api(session, endpoint, request.upc) for endpoint in endpoints]
        results = await asyncio.gather(*tasks)
    
    # Find best price (only consider in-stock items)
    valid_results = [r for r in results if r.price is not None and r.in_stock is True]
    best_price = None
    best_merchant = None
    best_url = None
    
    if valid_results:
        best_result = min(valid_results, key=lambda x: x.price)
        best_price = best_result.price
        best_merchant = best_result.merchant
        best_url = best_result.url
    
    return PriceComparisonResponse(
        upc=request.upc,
        results=results,
        best_price=best_price,
        best_merchant=best_merchant,
        best_url=best_url,
        comparison_time=datetime.now().isoformat()
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Price Comparison Tool API"
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Price Comparison Tool API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)