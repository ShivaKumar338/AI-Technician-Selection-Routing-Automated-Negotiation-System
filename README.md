# AI Technician Routing & Automated Negotiation API

FastAPI backend that matches customers to technicians using a weighted routing score, then negotiates pricing with two Gemini (`gemini-1.5-flash`) agents.

## Setup

### 1. Install dependencies

```powershell
cd C:\Users\HP\tech-routing-api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Environment variables

```powershell
copy .env.example .env
```

Edit `.env` with **real** values (not placeholders):

| Variable | Where to get it |
|----------|-----------------|
| `SUPABASE_URL` | Supabase → Settings → API → Project URL |
| `SUPABASE_KEY` | Supabase → Settings → API → `service_role` (recommended) or `anon` |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) |

### 3. Create database tables

Open **Supabase → SQL Editor** and run `schema.sql` from this project (creates `technicians`, `jobs`, `negotiation_logs`).

### 4. Run the server

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Docs: http://localhost:8000/docs

### 5. Seed and test

1. `POST /seed` — 20 Hyderabad technicians  
2. `POST /jobs` — create a job  
3. `POST /jobs/{job_id}/match` — top 3 technicians  
4. `POST /jobs/{job_id}/negotiate/{tech_id}` — AI negotiation  

## Routing score

For each technician:

- `skill_score` = `1.0` if `problem_type` matches a skill (case-insensitive), else `0.0`
- `distance_km` = Haversine(customer, technician)
- `proximity_score` = `max(0, 1 - distance_km / 50)`
- `final_score` = `(0.4 × skill_score) + (0.3 × proximity_score) + (0.2 × rating/5) + (0.1 × available)`

Response includes `score` (= final_score) and `distance_km`.

## Negotiation

- `urgency_multiplier` = `1 + (urgency × 0.05)`
- **Tech floor** = `round(rate_min × urgency_multiplier)`
- **Customer ceiling** = `min(round(budget × urgency_multiplier), 2 × budget)`
- 4 rounds: customer Gemini agent → technician Gemini agent
- Within **15%** → agreed price = midpoint
- After 4 rounds with no deal → `round((floor + ceiling) / 2)`
- Logs saved to `negotiation_logs`; job → `assigned`

If Gemini fails, hardcoded fallback offers are used automatically.

## API endpoints

### `POST /jobs` — Create job (201)

**Body**

```json
{
  "problem_type": "AC",
  "customer_lat": 17.385,
  "customer_lng": 78.4867,
  "urgency": 3,
  "customer_budget": 1500
}
```

**Returns:** created job object (`status`: `pending`).

---

### `POST /jobs/{job_id}/match` — Match top 3 technicians

**Returns**

```json
{
  "job_id": "uuid",
  "problem_type": "AC",
  "technicians": [
    {
      "id": "uuid",
      "name": "Ravi Reddy",
      "skills": ["AC", "electrical"],
      "score": 0.82,
      "distance_km": 5.2
    }
  ]
}
```

Sets job `status` to `matched`.

---

### `POST /jobs/{job_id}/negotiate/{tech_id}` — Negotiate price

**Returns**

```json
{
  "rounds": [
    {
      "round": 1,
      "customer_offer": 900,
      "tech_offer": 1100,
      "customer_message": "...",
      "tech_message": "...",
      "created_at": "2026-05-16T12:00:00+00:00"
    }
  ],
  "agreed_price": 1000,
  "status": "assigned",
  "technician_name": "Ravi Reddy"
}
```

---

### `GET /jobs` — List jobs

Includes `technician_name` when assigned.

---

### `GET /jobs/{job_id}` — Job detail

Includes full `negotiation_logs` array.

---

### `GET /technicians` — List technicians

---

### `POST /technicians` — Create technician (201)

```json
{
  "name": "Priya Naidu",
  "skills": ["plumbing", "AC"],
  "lat": 17.44,
  "lng": 78.49,
  "rate_min": 500,
  "rating": 4.8,
  "available": true
}
```

---

### `GET /stats` — Platform statistics

```json
{
  "total_jobs": 10,
  "completed_jobs": 2,
  "avg_agreed_price": 875.5,
  "total_savings": 3200
}
```

`total_savings` = sum of `(customer_budget - agreed_price)` where `agreed_price < customer_budget`.

---

### `POST /seed` — Seed 20 technicians

Hyderabad area: lat `17.3–17.5`, lng `78.3–78.6`, rates INR `200–800`, ratings `3.5–5.0`.

---

### `GET /health` — Health check

Reports whether Supabase and Gemini env vars are configured.

## CORS

All origins allowed (`*`) for Lovable / frontend development.

## Error handling

- Database errors → `500` with `Database error during ...` message
- Missing job/technician → `404`
- Missing/placeholder Supabase env → `500` with setup instructions
- Gemini errors → automatic fallback negotiation (request still succeeds)

## Files

| File | Description |
|------|-------------|
| `main.py` | FastAPI application (all logic) |
| `schema.sql` | Run once in Supabase SQL Editor |
| `requirements.txt` | Python packages |
| `.env.example` | Environment template |
