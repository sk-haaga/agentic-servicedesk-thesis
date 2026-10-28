"""Mock ITSM REST API (FastAPI). Field names and paths follow the ServiceNow Table API convention.

Run:  uvicorn src.servicedesk.itsm.api:app --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from ..config import load_catalogue
from .store import Store

app = FastAPI(title="Mock ITSM (ServiceNow-style)", version="1.0")
store = Store(os.environ.get("ITSM_DB"))


@app.post("/api/now/table/incident", status_code=201)
def create_incident(fields: dict):
    number = store.create_incident({k: v for k, v in fields.items() if k != "number"})
    return {"result": store.get_incident(number)}


@app.get("/api/now/table/incident")
def list_incidents(state: str | None = None):
    return {"result": store.list_incidents(state)}


@app.get("/api/now/table/incident/{number}")
def get_incident(number: str):
    inc = store.get_incident(number)
    if not inc:
        raise HTTPException(404, "not found")
    return {"result": inc}


@app.patch("/api/now/table/incident/{number}")
def update_incident(number: str, fields: dict):
    if not store.get_incident(number):
        raise HTTPException(404, "not found")
    store.update_incident(number, fields)
    return {"result": store.get_incident(number)}


@app.get("/api/catalogue/{name}")
def catalogue(name: str = "d3"):
    c = load_catalogue(name)
    return {"categories": c.category_names, "applications": c.applications, "groups": c.groups}


@app.get("/api/audit/{number}")
def audit(number: str):
    return {"result": store.audit_events(number)}
