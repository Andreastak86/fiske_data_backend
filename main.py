from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import csv
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Fangst-API")


class Catch(BaseModel):
    id: int
    date: str
    location: str
    species: str
    length_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    method: Optional[str] = None
    weather: Optional[str] = None
    water_temp_c: Optional[float] = None
    notes: Optional[str] = None


class Summary(BaseModel):
    total_catches: int
    unique_species: int
    unique_locations: int
    biggest_fish_kg: Optional[float]
    most_common_species: Optional[str]
    last_trip_date: Optional[str]


class SpeciesCount(BaseModel):
    species: str
    count: int


CATCHES: List[Catch] = []


def load_csv(path: str = "catch_log.csv") -> None:
    """Leser CSV-filen inn i minnet når appen starter."""
    global CATCHES
    CATCHES = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                CATCHES.append(
                    Catch(
                        id=int(row.get("id", len(CATCHES) + 1)),
                        date=row["date"],
                        location=row["location"],
                        species=row["species"],
                        length_cm=(
                            float(row["length_cm"]) if row.get("length_cm") else None
                        ),
                        weight_kg=(
                            float(row["weight_kg"]) if row.get("weight_kg") else None
                        ),
                        method=row.get("method") or None,
                        weather=row.get("weather") or None,
                        water_temp_c=(
                            float(row["water_temp_c"])
                            if row.get("water_temp_c")
                            else None
                        ),
                        notes=row.get("notes") or None,
                    )
                )
    except FileNotFoundError:
        CATCHES = []


def compute_summary() -> Summary:
    if not CATCHES:
        return Summary(
            total_catches=0,
            unique_species=0,
            unique_locations=0,
            biggest_fish_kg=None,
            most_common_species=None,
            last_trip_date=None,
        )

    total = len(CATCHES)
    species_set = {c.species for c in CATCHES}
    location_set = {c.location for c in CATCHES}
    biggest = max(
        (c.weight_kg for c in CATCHES if c.weight_kg is not None),
        default=None,
    )

    counts = {}
    for c in CATCHES:
        counts[c.species] = counts.get(c.species, 0) + 1
    most_common = max(counts, key=counts.get) if counts else None

    # siste tur (nyeste dato)
    def parse_date(d: str):
        return datetime.strptime(d, "%Y-%m-%d")

    last_date = max(parse_date(c.date) for c in CATCHES)

    return Summary(
        total_catches=total,
        unique_species=len(species_set),
        unique_locations=len(location_set),
        biggest_fish_kg=biggest,
        most_common_species=most_common,
        last_trip_date=last_date.strftime("%Y-%m-%d"),
    )


@app.on_event("startup")
def startup_event():
    load_csv("fangst_fisk.csv")
    print(f"⚓ Loaded {len(CATCHES)} fangster fra CSV!")


@app.get("/api/summary", response_model=Summary)
def get_summary():
    return compute_summary()


@app.get("/api/catches", response_model=List[Catch])
def get_catches(
    species: Optional[str] = None,
    location: Optional[str] = None,
):
    data = CATCHES
    if species:
        data = [c for c in data if c.species.lower() == species.lower()]
    if location:
        data = [c for c in data if c.location.lower() == location.lower()]
    return data


@app.get("/api/species", response_model=List[SpeciesCount])
def get_species_counts():
    counts = {}
    for c in CATCHES:
        counts[c.species] = counts.get(c.species, 0) + 1
    return [
        SpeciesCount(species=s, count=c)
        for s, c in sorted(counts.items(), key=lambda x: -x[1])
    ]


@app.get("/api/test_count")
def test_count():
    return {"rows": len(CATCHES)}


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
