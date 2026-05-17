"""
AI Negotiation Engine.

Role: We are the PLATFORM negotiating with a technician.
Goal: Get the technician to accept the LOWEST price possible, strictly under customer budget.

Strategy:
- Never reveal customer budget to technician
- Start at (budget - 200), negotiate upward slowly only if needed
- Only go up if technician's counter is within budget
- Never exceed budget under any circumstance
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


# ── Price extraction ──────────────────────────────────────────────────────────

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
        "not possible", "won't do", "will not", "not coming"
    ]
    lower = text.lower()
    return any(k in lower for k in keywords)


def is_acceptance(text: str, our_offer: int) -> bool:
    """
    True only if technician clearly accepted without quoting a higher price.
    """
    lower = text.lower()

    # Strong phrases — always acceptance if no higher price mentioned
    strong = ["deal", "agreed", "confirmed", "i accept", "i'll do it",
              "i will do it", "ok deal", "okay deal", "done deal",
              "that works", "sounds good", "let's do it", "i'm in",
              "will come", "i'll come", "coming"]
    for phrase in strong:
        if phrase in lower:
            price = extract_price_from_reply(text)
            if price is None or price <= our_offer:
                return True

    # Weak words (ok/yes) — only accept if no price mentioned or price matches ours
    weak = ["ok", "okay", "fine", "sure", "yes", "alright", "haan", "done"]
    for word in weak:
        if re.search(rf'\b{word}\b', lower):
            price = extract_price_from_reply(text)
            if price is None:
                return True
            if abs(price - our_offer) <= our_offer * 0.03:
                return True

    return False


def compute_our_offer(
    our_last_offer: int,
    their_offer: int,
    budget: int,
    floor: int,
) -> int:
    """
    Given technician's counter-offer, compute our next offer.

    Logic:
    - If their offer > budget: we can't go there. Nudge up by 50 from our last, stay under budget.
    - If their offer <= budget: move halfway between our last offer and their offer (but stay <= budget).
    - Never go below floor, never exceed budget.
    """
    if their_offer > budget:
        # They're asking more than budget — inch up slightly to show willingness, stay under budget
        nudge = min(50, budget - our_last_offer)
        offer = our_last_offer + nudge
    else:
        # Their ask is within budget — meet halfway
        offer = our_last_offer + int((their_offer - our_last_offer) * 0.5)

    return max(floor, min(offer, budget))


# ── Gemini calls ──────────────────────────────────────────────────────────────

def _call_gemini_sync(prompt: str) -> str:
    model = _get_model()
    if not model:
        return ""
    try:
        resp = model.generate_content(
            prompt,
            generation_config={"temperature": 0.7, "max_output_tokens": 120},
        )
        return (resp.text or "").strip()
    except Exception as exc:
        logger.warning("Gemini error: %s", exc)
        return ""


async def _call_gemini(prompt: str) -> str:
    return await asyncio.to_thread(_call_gemini_sync, prompt)


# ── Message generators ────────────────────────────────────────────────────────

async def generate_opening_message(job: dict, technician: dict, our_offer: int) -> str:
    prompt = f"""You are a job coordinator sending a WhatsApp message to a technician.

Technician name: {technician['name']}
Job type: {job['problem_type']}
Your offer: ₹{our_offer}

Write a short, friendly message (2 sentences max):
- Mention the job type
- State your offer of ₹{our_offer}
- Ask if they are available
- Do NOT mention any budget or customer details
- Plain text only, no emojis, no markdown

Write only the message text."""

    msg = await _call_gemini(prompt)
    if not msg:
        msg = (
            f"Hi {technician['name']}, we have a {job['problem_type']} job available "
            f"and can offer ₹{our_offer}. Are you available?"
        )
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
        context = f"Their asking price ₹{their_offer} is too high for this job."
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
- Sound like a real person, not a bot
- Do NOT mention any budget limit or customer details
- Plain text only

Write only the message."""

    msg = await _call_gemini(prompt)
    if not msg:
        if above_budget:
            msg = f"That's a bit high for us, we can offer ₹{our_offer} for this {job['problem_type']} job. Would that work?"
        else:
            msg = f"We can do ₹{our_offer} for this job. Does that work for you?"
    return msg


async def generate_agreement_message(technician: dict, agreed_price: int, job: dict) -> str:
    prompt = f"""Write a short WhatsApp confirmation message.
Technician: {technician['name']}, Job: {job['problem_type']}, Price: ₹{agreed_price}
2 sentences: confirm the deal and say customer details follow. Plain text only."""

    msg = await _call_gemini(prompt)
    if not msg:
        msg = (
            f"Great, deal confirmed at ₹{agreed_price} for the {job['problem_type']} job! "
            f"We'll send you the customer details shortly."
        )
    return msg


async def generate_rejection_response(technician: dict, job: dict) -> str:
    return (
        f"No problem {technician['name']}, thanks for your time. "
        f"We'll reach out for future {job['problem_type']} jobs!"
    )
