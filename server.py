import os
from datetime import date
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database
import config

# Initialize DB tables
database.init_db()

app = FastAPI(title="Pallet Tracker TMA")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

INDEX_HTML_PATH = os.path.join(TEMPLATES_DIR, "index.html")

# Pydantic schemas
class ProductionCreate(BaseModel):
    date: str
    lyubota: int = 0
    galkin: int = 0
    author: Optional[str] = "Користувач"

class ShipmentCreate(BaseModel):
    date: str
    quantity: int
    note: Optional[str] = ""
    author: Optional[str] = "Користувач"

class InitialStockUpdate(BaseModel):
    stock: int

@app.get("/")
async def index_page():
    if not os.path.exists(INDEX_HTML_PATH):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(INDEX_HTML_PATH, media_type="text/html")

@app.get("/api/summary")
async def get_summary(date: Optional[str] = None):
    try:
        data = database.get_stock_summary(date)
        return JSONResponse(content={"ok": True, "data": data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/production")
async def create_production(payload: ProductionCreate):
    try:
        prod_id = database.add_production(
            date_str=payload.date,
            lyubota=payload.lyubota,
            galkin=payload.galkin,
            author=payload.author or "Користувач"
        )
        summary = database.get_stock_summary(payload.date)
        return JSONResponse(content={"ok": True, "id": prod_id, "summary": summary})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/production/{prod_id}")
async def remove_production(prod_id: int):
    success = database.delete_production(prod_id)
    if not success:
        raise HTTPException(status_code=404, detail="Запис не знайдено")
    return JSONResponse(content={"ok": True})

@app.get("/api/production")
async def list_production(limit: int = 50):
    rows = database.get_recent_production(limit)
    return JSONResponse(content={"ok": True, "data": rows})

@app.post("/api/shipment")
async def create_shipment(payload: ShipmentCreate):
    try:
        shipment_id = database.add_shipment(
            date_str=payload.date,
            quantity=payload.quantity,
            note=payload.note or "",
            author=payload.author or "Користувач"
        )
        summary = database.get_stock_summary(payload.date)
        return JSONResponse(content={"ok": True, "id": shipment_id, "summary": summary})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/shipment/{shipment_id}")
async def remove_shipment(shipment_id: int):
    success = database.delete_shipment(shipment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Запис не знайдено")
    return JSONResponse(content={"ok": True})

@app.get("/api/shipments")
async def list_shipments(limit: int = 50):
    rows = database.get_recent_shipments(limit)
    return JSONResponse(content={"ok": True, "data": rows})

@app.post("/api/initial-stock")
async def update_initial_stock(payload: InitialStockUpdate):
    database.set_initial_stock(payload.stock)
    summary = database.get_stock_summary()
    return JSONResponse(content={"ok": True, "summary": summary})

@app.get("/api/report")
async def get_report(date: Optional[str] = None):
    text = database.generate_report_text(date)
    return JSONResponse(content={"ok": True, "report": text})
