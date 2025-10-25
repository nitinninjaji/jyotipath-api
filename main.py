from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import json

app = FastAPI(title="JyotiPath API")

# ---------- Request Model ----------
class NatalRequest(BaseModel):
    name: str
    email: str
    date: str           # YYYY-MM-DD
    time: str           # HH:MM 24h or AM/PM
    place: str

# ---------- Response Model ----------
class NatalResponse(BaseModel):
    input_received: Dict[str, str]
    planets: Dict[str, float]       # Degrees for each planet
    dasha: Dict[str, Any]           # Mahadasha info
    ayanamsha: str
    summary: str

# ---------- Dummy Astrology Logic ----------
def compute_natal_chart(date:str, time:str, place:str) -> Dict[str, Any]:
    # In production, integrate with your astrology library
    planets = {
        "Ascendant": 15.2,
        "Sun": 13.59,
        "Moon": 18.34,
        "Mars": 18.90,
        "Mercury": 7.53,
        "Jupiter": 25.34,
        "Venus": 16.93,
        "Saturn": 16.78,
        "Rahu": 8.05,
        "Ketu": 8.48
    }

    # Example Mahadasha
    dasha = {
        "current_maha": {"lord": "Sun", "start": "2024-01-01", "end": "2030-12-31"},
        "maha_sequence": [
            {"lord":"Sun","start":"2024-01-01","end":"2030-12-31"},
            {"lord":"Moon","start":"2031-01-01","end":"2036-12-31"},
            {"lord":"Mars","start":"2037-01-01","end":"2043-12-31"}
        ]
    }

    ayanamsha = "Lahiri"

    summary = "Natal chart computed successfully with planetary positions and dasha info."

    return {"planets":planets,"dasha":dasha,"ayanamsha":ayanamsha,"summary":summary}

# ---------- API Endpoint ----------
@app.post("/compute_natal", response_model=NatalResponse)
async def compute_natal(req: NatalRequest):
    try:
        chart = compute_natal_chart(req.date, req.time, req.place)
        response = {
            "input_received":{
                "name": req.name,
                "email": req.email,
                "date": req.date,
                "time": req.time,
                "place_name": req.place
            },
            "planets": chart["planets"],
            "dasha": chart["dasha"],
            "ayanamsha": chart["ayanamsha"],
            "summary": chart["summary"]
        }
        return response
    except Exception as e:
        return {
            "input_received":{
                "name": req.name,
                "email": req.email,
                "date": req.date,
                "time": req.time,
                "place_name": req.place
            },
            "planets":{},
            "dasha":{},
            "ayanamsha":"",
            "summary": f"Error computing natal chart: {str(e)}"
        }

# ---------- Run with Uvicorn ----------
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
