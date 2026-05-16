import json
import math
import os
import random
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypeVar

import google.generativeai as genai
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import Client, ClientOptions, create_client

T = TypeVar("T")

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

app = FastAPI(
    title="AI Technician Routing & Negotiation API",
    description="Match customers to technicians and negotiate pricing autonomously.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_supabase: Optional[Client] = None
_gemini_model: Optional[Any] = None
_db_lock = threading.Lock()
DB_RETRIES = 4
DB_RETRY_DELAY_SEC = 0.2

NEGOTIATION_ROUNDS = 4
CONVERGENCE_THRESHOLD = 0.15
PLACEHOLDER_MARKERS = ("your-", "example", "changeme", "replace")


def is_configured(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return not any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_supabase() -> Client:
    global _supabase
    if not is_configured(SUPABASE_URL) or not is_configured(SUPABASE_KEY):
        raise HTTPException(
            status_code=500,
            detail=(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env with real values. "
                "Get them from Supabase → Settings → API."
            ),
        )
    if _supabase is None:
        http_client = httpx.Client(
            http2=False,
            timeout=httpx.Timeout(60.0, connect=20.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        _supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
            options=ClientOptions(httpx_client=http_client),
        )
    return _supabase


def is_transient_db_error(exc: Exception) -> bool:
    markers = (
        "10035",
        "would block",
        "wsaewouldblock",
        "connection reset",
        "connection aborted",
        "timed out",
        "timeout",
        "temporary failure",
        "broken pipe",
        "errno 11",
    )
    text = str(exc).lower()
    return any(marker in text for marker in markers)


def get_gemini_model():
    global _gemini_model
    if _gemini_model is None and is_configured(GEMINI_API_KEY):
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    return _gemini_model


def format_db_error(operation: str, exc: Exception) -> str:
    message = str(exc)
    if "PGRST205" in message or "Could not find the table" in message:
        return (
            f"Tables not found during {operation}. "
            "Run schema.sql in Supabase → SQL Editor (recommended), "
            "or call POST /init-db after setting DATABASE_URL in .env. "
            f"Original error: {exc}"
        )
    return f"Database error during {operation}: {exc}"


def db_call(operation: str, fn: Callable[[], T]) -> T:
    last_exc: Optional[Exception] = None
    for attempt in range(DB_RETRIES):
        try:
            with _db_lock:
                return fn()
        except HTTPException:
            raise
        except Exception as exc:
            last_exc = exc
            if is_transient_db_error(exc) and attempt < DB_RETRIES - 1:
                time.sleep(DB_RETRY_DELAY_SEC * (attempt + 1))
                continue
            raise HTTPException(
                status_code=500, detail=format_db_error(operation, exc)
            ) from exc
    raise HTTPException(
        status_code=500,
        detail=format_db_error(operation, last_exc or RuntimeError("Unknown database error")),
    )


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def skill_matches(problem_type: str, skills: list) -> bool:
    if not skills:
        return False
    target = problem_type.strip().lower()
    return any(str(skill).strip().lower() == target for skill in skills)


def compute_technician_score(
    problem_type: str,
    customer_lat: float,
    customer_lng: float,
    technician: dict,
) -> tuple[float, float, float]:
    skill_score = 1.0 if skill_matches(problem_type, technician.get("skills") or []) else 0.0
    distance_km = haversine_km(
        customer_lat,
        customer_lng,
        float(technician["lat"]),
        float(technician["lng"]),
    )
    proximity_score = max(0.0, 1.0 - distance_km / 50.0)
    rating = float(technician.get("rating") or 0.0)
    available_flag = 1.0 if technician.get("available") else 0.0
    final_score = (
        (0.4 * skill_score)
        + (0.3 * proximity_score)
        + (0.2 * (rating / 5.0))
        + (0.1 * available_flag)
    )
    return round(final_score, 4), round(distance_km, 2), skill_score


def urgency_multiplier(urgency: int) -> float:
    return 1.0 + (urgency * 0.05)


def compute_negotiation_bounds(
    customer_budget: int, urgency: int, rate_min: int
) -> tuple[int, int]:
    mult = urgency_multiplier(urgency)
    tech_floor = int(round(rate_min * mult))
    raw_ceiling = int(round(customer_budget * mult))
    customer_ceiling = min(raw_ceiling, customer_budget * 2)
    return tech_floor, customer_ceiling


def offers_within_threshold(offer_a: int, offer_b: int) -> bool:
    if offer_a <= 0 or offer_b <= 0:
        return False
    return abs(offer_a - offer_b) <= CONVERGENCE_THRESHOLD * max(offer_a, offer_b)


def midpoint_price(offer_a: int, offer_b: int) -> int:
    return int(round((offer_a + offer_b) / 2))


def extract_json_from_text(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Invalid JSON object from model")
    return {
        "offer": int(data["offer"]),
        "message": str(data.get("message", "")).strip() or "No message provided.",
    }


def call_gemini_agent(prompt: str) -> dict:
    model = get_gemini_model()
    if model is None:
        raise RuntimeError("Gemini API key not configured")
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.7, "max_output_tokens": 300},
    )
    text = (response.text or "").strip()
    if not text:
        raise ValueError("Empty response from Gemini")
    return extract_json_from_text(text)


def fallback_customer_offer(
    round_num: int,
    ceiling: int,
    min_offer: int,
    tech_last_offer: Optional[int],
) -> dict:
    anchor = tech_last_offer if tech_last_offer is not None else ceiling
    gap = max(anchor - min_offer, 1)
    progress = round_num / NEGOTIATION_ROUNDS
    offer = int(round(ceiling - gap * 0.55 * progress))
    offer = max(min_offer, min(offer, ceiling))
    return {
        "offer": offer,
        "message": (
            f"Round {round_num}: Our offer is INR {offer}. "
            "We want a fair price within budget."
        ),
    }


def fallback_tech_offer(
    round_num: int,
    floor: int,
    ceiling: int,
    customer_last_offer: Optional[int],
) -> dict:
    anchor = customer_last_offer if customer_last_offer is not None else floor
    gap = max(ceiling - anchor, 1)
    progress = round_num / NEGOTIATION_ROUNDS
    offer = int(round(floor + gap * 0.45 * progress))
    offer = max(floor, min(offer, ceiling))
    return {
        "offer": offer,
        "message": (
            f"Round {round_num}: I can do INR {offer} including travel and labor."
        ),
    }


def run_customer_agent(
    problem_type: str,
    ceiling: int,
    round_num: int,
    tech_last_offer: Optional[int],
) -> dict:
    tech_display = tech_last_offer if tech_last_offer is not None else "none yet"
    prompt = (
        f"You are negotiating on behalf of a customer for a {problem_type} job. "
        f"Your absolute maximum budget is INR {ceiling}. Current round: {round_num}. "
        f"Tech's last offer: INR {tech_display}. "
        f"Make a realistic counter-offer that moves toward agreement. "
        f'Respond in JSON: {{"offer": integer, "message": string}}'
    )
    try:
        return call_gemini_agent(prompt)
    except Exception:
        min_offer = max(1, int(ceiling * 0.4))
        return fallback_customer_offer(round_num, ceiling, min_offer, tech_last_offer)


def run_tech_agent(
    problem_type: str,
    floor: int,
    ceiling: int,
    round_num: int,
    customer_last_offer: Optional[int],
) -> dict:
    customer_display = (
        customer_last_offer if customer_last_offer is not None else "none yet"
    )
    prompt = (
        f"You are a technician negotiating your service rate for a {problem_type} job. "
        f"Your minimum acceptable rate is INR {floor}. Current round: {round_num}. "
        f"Customer's last offer: INR {customer_display}. "
        f"Make a realistic counter-offer. "
        f'Respond in JSON: {{"offer": integer, "message": string}}'
    )
    try:
        return call_gemini_agent(prompt)
    except Exception:
        return fallback_tech_offer(round_num, floor, ceiling, customer_last_offer)


def fetch_technician_names(tech_ids: list[str]) -> dict[str, str]:
    if not tech_ids:
        return {}

    def _query():
        client = get_supabase()
        result = (
            client.table("technicians")
            .select("id, name")
            .in_("id", list(set(tech_ids)))
            .execute()
        )
        return {row["id"]: row["name"] for row in (result.data or [])}

    return db_call("fetch technician names", _query)


def attach_technician_name(job: dict, name_map: dict[str, str]) -> dict:
    tech_id = job.get("assigned_tech_id")
    job["technician_name"] = name_map.get(tech_id) if tech_id else None
    return job


class JobCreate(BaseModel):
    problem_type: str
    customer_lat: float
    customer_lng: float
    urgency: int = Field(ge=1, le=5)
    customer_budget: int = Field(gt=0)


class TechnicianCreate(BaseModel):
    name: str
    skills: list[str]
    lat: float
    lng: float
    rate_min: int = Field(gt=0)
    rating: float = Field(ge=1.0, le=5.0)
    available: bool = True


@app.get("/health")
def health():
    tables_ok = False
    if is_configured(SUPABASE_URL) and is_configured(SUPABASE_KEY):
        try:
            get_supabase().table("jobs").select("id").limit(1).execute()
            tables_ok = True
        except Exception:
            tables_ok = False
    return {
        "status": "ok",
        "timestamp": utc_now_iso(),
        "supabase_configured": is_configured(SUPABASE_URL) and is_configured(SUPABASE_KEY),
        "gemini_configured": is_configured(GEMINI_API_KEY),
        "database_tables_ready": tables_ok,
    }


@app.post("/init-db")
def init_database():
    if not is_configured(DATABASE_URL):
        raise HTTPException(
            status_code=400,
            detail=(
                "DATABASE_URL is not set. Either add it to .env "
                "(Supabase → Settings → Database → Connection string → URI), "
                "or open schema.sql in Supabase → SQL Editor and click Run."
            ),
        )
    try:
        import psycopg2
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="psycopg2-binary is required for /init-db. Run: pip install psycopg2-binary",
        ) from exc

    try:
        with open(SCHEMA_PATH, encoding="utf-8") as schema_file:
            sql = schema_file.read()
        connection = psycopg2.connect(DATABASE_URL)
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute(sql)
        cursor.close()
        connection.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Schema init failed: {exc}") from exc

    return {
        "message": "Database tables created successfully",
        "tables": ["technicians", "jobs", "negotiation_logs"],
    }


@app.post("/jobs", status_code=201)
def create_job(body: JobCreate):
    record = {
        "id": str(uuid.uuid4()),
        "problem_type": body.problem_type.strip(),
        "customer_lat": body.customer_lat,
        "customer_lng": body.customer_lng,
        "urgency": body.urgency,
        "customer_budget": body.customer_budget,
        "status": "pending",
        "assigned_tech_id": None,
        "agreed_price": None,
        "created_at": utc_now_iso(),
    }

    def _insert():
        result = get_supabase().table("jobs").insert(record).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create job")
        return result.data[0]

    return db_call("create job", _insert)


@app.post("/jobs/{job_id}/match")
def match_technicians(job_id: str):
    def _match():
        client = get_supabase()
        job_result = client.table("jobs").select("*").eq("id", job_id).limit(1).execute()
        if not job_result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        job = job_result.data[0]

        tech_result = client.table("technicians").select("*").execute()
        ranked = []
        for tech in tech_result.data or []:
            final_score, distance_km, _ = compute_technician_score(
                job["problem_type"],
                float(job["customer_lat"]),
                float(job["customer_lng"]),
                tech,
            )
            ranked.append(
                {
                    "id": tech["id"],
                    "name": tech["name"],
                    "skills": tech.get("skills") or [],
                    "lat": tech["lat"],
                    "lng": tech["lng"],
                    "rate_min": tech["rate_min"],
                    "rating": tech["rating"],
                    "available": tech["available"],
                    "score": final_score,
                    "distance_km": distance_km,
                }
            )

        ranked.sort(key=lambda row: row["score"], reverse=True)
        client.table("jobs").update({"status": "matched"}).eq("id", job_id).execute()
        return {
            "job_id": job_id,
            "problem_type": job["problem_type"],
            "technicians": ranked[:3],
        }

    return db_call("match technicians", _match)


@app.post("/jobs/{job_id}/negotiate/{tech_id}")
def negotiate_job(job_id: str, tech_id: str):
    def _negotiate():
        client = get_supabase()
        job_result = client.table("jobs").select("*").eq("id", job_id).limit(1).execute()
        tech_result = (
            client.table("technicians").select("*").eq("id", tech_id).limit(1).execute()
        )
        if not job_result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        if not tech_result.data:
            raise HTTPException(status_code=404, detail="Technician not found")

        job = job_result.data[0]
        tech = tech_result.data[0]
        floor, ceiling = compute_negotiation_bounds(
            int(job["customer_budget"]),
            int(job["urgency"]),
            int(tech["rate_min"]),
        )

        client.table("jobs").update({"status": "negotiating"}).eq("id", job_id).execute()

        rounds_output: list[dict] = []
        agreed_price: Optional[int] = None
        tech_last_offer: Optional[int] = None
        customer_last_offer: Optional[int] = None

        for round_num in range(1, NEGOTIATION_ROUNDS + 1):
            customer_turn = run_customer_agent(
                job["problem_type"], ceiling, round_num, tech_last_offer
            )
            customer_offer = max(floor, min(int(customer_turn["offer"]), ceiling))
            customer_message = customer_turn["message"]
            customer_last_offer = customer_offer

            tech_turn = run_tech_agent(
                job["problem_type"], floor, ceiling, round_num, customer_last_offer
            )
            tech_offer = max(floor, min(int(tech_turn["offer"]), ceiling))
            tech_message = tech_turn["message"]
            tech_last_offer = tech_offer

            created_at = utc_now_iso()
            log_record = {
                "id": str(uuid.uuid4()),
                "job_id": job_id,
                "round": round_num,
                "customer_offer": customer_offer,
                "tech_offer": tech_offer,
                "customer_message": customer_message,
                "tech_message": tech_message,
                "created_at": created_at,
            }
            client.table("negotiation_logs").insert(log_record).execute()

            rounds_output.append(
                {
                    "round": round_num,
                    "customer_offer": customer_offer,
                    "tech_offer": tech_offer,
                    "customer_message": customer_message,
                    "tech_message": tech_message,
                    "created_at": created_at,
                }
            )

            if offers_within_threshold(customer_offer, tech_offer):
                agreed_price = midpoint_price(customer_offer, tech_offer)
                break

        if agreed_price is None:
            agreed_price = int(round((floor + ceiling) / 2))

        client.table("jobs").update(
            {
                "status": "assigned",
                "agreed_price": agreed_price,
                "assigned_tech_id": tech_id,
            }
        ).eq("id", job_id).execute()

        return {
            "rounds": rounds_output,
            "agreed_price": agreed_price,
            "status": "assigned",
            "technician_name": tech["name"],
        }

    return db_call("negotiate job", _negotiate)


@app.get("/jobs")
def list_jobs():
    def _list():
        result = (
            get_supabase()
            .table("jobs")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        jobs = result.data or []
        tech_ids = [j["assigned_tech_id"] for j in jobs if j.get("assigned_tech_id")]
        name_map = fetch_technician_names(tech_ids)
        return {
            "jobs": [attach_technician_name(dict(job), name_map) for job in jobs],
            "count": len(jobs),
        }

    return db_call("list jobs", _list)


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    def _get():
        client = get_supabase()
        job_result = client.table("jobs").select("*").eq("id", job_id).limit(1).execute()
        if not job_result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        job = dict(job_result.data[0])
        tech_id = job.get("assigned_tech_id")
        name_map = fetch_technician_names([tech_id]) if tech_id else {}
        attach_technician_name(job, name_map)
        logs = (
            client.table("negotiation_logs")
            .select("*")
            .eq("job_id", job_id)
            .order("round")
            .execute()
        )
        job["negotiation_logs"] = logs.data or []
        return job

    return db_call("get job", _get)


@app.get("/technicians")
def list_technicians():
    def _list():
        result = get_supabase().table("technicians").select("*").order("name").execute()
        data = result.data or []
        return {"technicians": data, "count": len(data)}

    return db_call("list technicians", _list)


@app.post("/technicians", status_code=201)
def create_technician(body: TechnicianCreate):
    record = {
        "id": str(uuid.uuid4()),
        "name": body.name.strip(),
        "skills": [skill.strip() for skill in body.skills if skill.strip()],
        "lat": body.lat,
        "lng": body.lng,
        "rate_min": body.rate_min,
        "rating": round(body.rating, 1),
        "available": body.available,
    }

    def _create():
        result = get_supabase().table("technicians").insert(record).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create technician")
        return result.data[0]

    return db_call("create technician", _create)


@app.get("/stats")
def get_stats():
    def _stats():
        jobs = get_supabase().table("jobs").select("*").execute().data or []
        total_jobs = len(jobs)
        completed_jobs = sum(1 for job in jobs if job.get("status") == "completed")
        agreed_prices = [
            int(job["agreed_price"]) for job in jobs if job.get("agreed_price") is not None
        ]
        avg_agreed_price = (
            round(sum(agreed_prices) / len(agreed_prices), 2) if agreed_prices else 0.0
        )
        total_savings = 0
        for job in jobs:
            agreed = job.get("agreed_price")
            budget = job.get("customer_budget")
            if agreed is not None and budget is not None and int(agreed) < int(budget):
                total_savings += int(budget) - int(agreed)
        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "avg_agreed_price": avg_agreed_price,
            "total_savings": total_savings,
        }

    return db_call("get stats", _stats)


SEED_FIRST = [
    "Ravi", "Suresh", "Kiran", "Anil", "Prasad", "Venkat", "Harish", "Naveen",
    "Mahesh", "Rajesh", "Srinivas", "Gopal", "Arjun", "Vikram", "Deepak",
    "Sanjay", "Ramesh", "Ajay", "Karthik", "Manoj",
]
SEED_LAST = [
    "Reddy", "Rao", "Kumar", "Sharma", "Naidu", "Gupta", "Singh", "Patel",
    "Varma", "Iyer", "Chowdary", "Babu", "Prasad", "Murthy", "Goud",
    "Yadav", "Mohan", "Das", "Pillai", "Acharya",
]
SKILLS = ["AC", "plumbing", "electrical", "appliance", "carpentry", "painting"]


@app.post("/seed")
def seed_technicians():
    random.seed(42)
    records = []
    for index in range(20):
        records.append(
            {
                "id": str(uuid.uuid4()),
                "name": f"{SEED_FIRST[index]} {SEED_LAST[index]}",
                "skills": random.sample(SKILLS, random.randint(1, 3)),
                "lat": round(random.uniform(17.3, 17.5), 6),
                "lng": round(random.uniform(78.3, 78.6), 6),
                "rate_min": random.randint(200, 800),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "available": random.choice([True, True, True, False]),
            }
        )

    def _seed():
        result = get_supabase().table("technicians").insert(records).execute()
        data = result.data or records
        return {
            "message": "Seeded 20 technicians for Hyderabad region",
            "count": len(data),
            "technicians": data,
        }

    return db_call("seed technicians", _seed)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
