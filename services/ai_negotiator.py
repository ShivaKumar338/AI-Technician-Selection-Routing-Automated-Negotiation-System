"""
AI Negotiation Engine.

3-stage flow:
  STAGE 1 — Availability check (ask about visit date/time)
  STAGE 2 — Price negotiation (start ONLY after availability confirmed)
  STAGE 3 — Dispatch (send full customer details after deal closes)

Pricing rules:
  - Never reveal customer budget to technician
  - Start at (budget - 200), move up slowly only if needed
  - Never exceed budget
"""
import asyncio
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
NEGOTIATION_ROUNDS = int(os.getenv("NEGOTIATION_ROUNDS", "8"))

_gemini_model = None


def _get_model():
    global _gemini_model
    if _gemini_model is None and GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    return _gemini_model


# ── Parsing helpers ───────────────────────────────────────────────────────────

def extract_price_from_reply(text: str) -> Optional[int]:
    text = text.lower().replace(",", "")
    k_match = re.search(r"(\d+(?:\.\d+)?)\s*k\b", text)
    if k_match:
        return int(float(k_match.group(1)) * 1000)
    matches = re.findall(r"(?:rs\.?|₹|inr)?\s*(\d{3,5})", text)
    if matches:
        return max(int(m) for m in matches)
    return None


def is_rejection(text: str) -> bool:
    keywords = [
        "not available", "not interested", "can't take", "cannot take",
        "busy", "no thanks", "decline", "reject", "unavailable",
        "not possible", "won't do", "will not", "not coming",
        "can't come", "cannot come", "not free",
    ]
    lower = text.lower()
    return any(k in lower for k in keywords)


def is_availability_confirmed(text: str) -> bool:
    """
    Returns True if technician confirmed they are available for the slot.
    Must NOT have a rejection keyword.
    """
    if is_rejection(text):
        return False
    lower = text.lower()
    confirm_words = [
        "available", "yes", "ok", "okay", "sure", "confirmed",
        "will come", "i'll come", "coming", "can come", "i can",
        "haan", "ha", "fine", "alright", "no problem", "ready",
    ]
    return any(w in lower for w in confirm_words)


def is_acceptance(text: str, our_offer: int) -> bool:
    """True only if technician clearly accepted our price offer."""
    lower = text.lower()

    strong = [
        "deal", "agreed", "confirmed", "i accept", "i'll do it",
        "i will do it", "ok deal", "okay deal", "done deal",
        "that works", "sounds good", "let's do it", "i'm in",
        "will come", "i'll come", "coming",
    ]
    for phrase in strong:
        if phrase in lower:
            price = extract_price_from_reply(text)
            if price is None or price <= our_offer:
                return True

    weak = ["ok", "okay", "fine", "sure", "yes", "alright", "haan", "done"]
    for word in weak:
        if re.search(rf'\b{word}\b', lower):
            price = extract_price_from_reply(text)
            if price is None:
                return True
            if abs(price - our_offer) <= our_offer * 0.03:
                return True

    return False


def compute_our_offer(our_last_offer: int, their_offer: int, budget: int, floor: int) -> int:
    if their_offer > budget:
        nudge = min(50, budget - our_last_offer)
        offer = our_last_offer + nudge
    else:
        offer = our_last_offer + int((their_offer - our_last_offer) * 0.5)
    return max(floor, min(offer, budget))


# ── Gemini ────────────────────────────────────────────────────────────────────

def _call_gemini_sync(prompt: str) -> str:
    model = _get_model()
    if not model:
        return ""
    try:
        resp = model.generate_content(
            prompt,
            generation_config={"temperature": 0.7, "max_output_tokens": 150},
        )
        return (resp.text or "").strip()
    except Exception as exc:
        logger.warning("Gemini error: %s", exc)
        return ""


async def _call_gemini(prompt: str) -> str:
    return await asyncio.to_thread(_call_gemini_sync, prompt)


# ── Stage 1: Availability check ───────────────────────────────────────────────

async def generate_availability_message(job: dict, technician: dict) -> str:
    description = (job.get("description") or "").strip()
    visit_date = (job.get("visit_date") or "").strip()
    visit_time = (job.get("visit_time") or "").strip()

    issue_line = f"Issue: {description}" if description else ""
    date_line = f"Visit Date: {visit_date}" if visit_date else ""
    time_line = f"Visit Time: {visit_time}" if visit_time else ""
    slot_parts = [p for p in [date_line, time_line] if p]
    slot_block = "\n".join(slot_parts) if slot_parts else ""

    prompt = f"""You are a job coordinator sending a WhatsApp message to a technician to check availability.

Technician: {technician['name']}
Job type: {job['problem_type']}
{issue_line}
{slot_block}

Write a short, friendly WhatsApp message (3-4 lines):
- Greet by name
- Mention the job type and issue briefly
- Mention the visit date/time if provided
- Ask if they are available for this slot
- Do NOT mention price or budget
- Plain text only, no markdown

Write only the message."""

    msg = await _call_gemini(prompt)
    if not msg:
        parts = [f"Hi {technician['name']}, we have a {job['problem_type']} job."]
        if description:
            parts.append(f"Issue: {description}.")
        if visit_date or visit_time:
            slot = " ".join(filter(None, [visit_date, f"at {visit_time}" if visit_time else ""]))
            parts.append(f"Visit: {slot}.")
        parts.append("Are you available for this slot?")
        msg = " ".join(parts)
    return msg


# ── Stage 2: Price negotiation ────────────────────────────────────────────────

async def generate_price_opening(job: dict, technician: dict, our_offer: int) -> str:
    prompt = f"""You are a job coordinator. The technician just confirmed availability.
Now start price negotiation.

Technician: {technician['name']}
Job: {job['problem_type']}
Your offer: ₹{our_offer}

Write 1-2 sentences:
- Thank them for confirming
- State your offer of ₹{our_offer} for this job
- Ask if they can accept
- Do NOT mention customer budget
- Plain text only

Write only the message."""

    msg = await _call_gemini(prompt)
    if not msg:
        msg = f"Great, thanks for confirming! We can offer ₹{our_offer} for this {job['problem_type']} job. Can you accept this?"
    return msg


async def generate_counter_offer_message(
    job: dict,
    technician: dict,
    our_offer: int,
    their_offer: Optional[int],
    their_reply: str,
    budget: int,
) -> str:
    above_budget = their_offer is not None and their_offer > budget

    if above_budget:
        context = f"Their asking price ₹{their_offer} is too high."
        instruction = f"Politely say that's too high and counter with ₹{our_offer}."
    elif their_offer:
        context = f"They asked for ₹{their_offer}."
        instruction = f"Counter with ₹{our_offer} and try to close the deal."
    else:
        context = f"They replied: \"{their_reply}\""
        instruction = f"Respond naturally and offer ₹{our_offer}."

    prompt = f"""You are negotiating a {job['problem_type']} job on WhatsApp.

Technician said: "{their_reply}"
{context}
{instruction}

Rules:
- 1-2 sentences only
- State your offer of ₹{our_offer} clearly
- Sound like a real person
- Do NOT mention budget limit or customer details
- Plain text only

Write only the message."""

    msg = await _call_gemini(prompt)
    if not msg:
        if above_budget:
            msg = f"That's a bit high, we can offer ₹{our_offer} for this job. Would that work?"
        else:
            msg = f"We can do ₹{our_offer} for this job. Does that work for you?"
    return msg


# ── Stage 3: Dispatch ─────────────────────────────────────────────────────────

async def generate_dispatch_message(job: dict, technician: dict, agreed_price: int) -> str:
    """
    Final message sent after deal closes — full customer details for the technician.
    """
    name = job.get("customer_name") or "Customer"
    phone = job.get("customer_phone") or "—"
    address = job.get("customer_address") or "—"
    description = (job.get("description") or "").strip()
    visit_date = (job.get("visit_date") or "").strip()
    visit_time = (job.get("visit_time") or "").strip()

    visit_str = " ".join(filter(None, [visit_date, f"at {visit_time}" if visit_time else ""]))

    # Build dispatch message directly — no Gemini needed, must be exact
    lines = [
        "Job Confirmed",
        "",
        f"Customer: {name}",
        f"Phone: {phone}",
        f"Address: {address}",
    ]
    if description:
        lines += ["", f"Issue: {description}"]
    if visit_str:
        lines += [f"Visit: {visit_str}"]
    lines += [
        "",
        f"Job: {job['problem_type']}",
        f"Agreed Price: Rs {agreed_price}",
        "",
        "Please be on time. Thank you!",
    ]
    return "\n".join(lines)


async def generate_rejection_response(technician: dict, job: dict) -> str:
    return (
        f"No problem {technician['name']}, thanks for your time. "
        f"We'll reach out for future {job['problem_type']} jobs!"
    )
