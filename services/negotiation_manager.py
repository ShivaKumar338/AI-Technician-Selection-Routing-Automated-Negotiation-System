"""
Negotiation Manager.

Pricing rules (enforced here, not in ai_negotiator):
- our_offer starts at (budget - 200)
- our_offer NEVER exceeds budget
- our_offer only moves UP if technician's counter is within budget
- agreed_price is always <= budget
- budget is NEVER sent to technician
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from services.ai_negotiator import (
    NEGOTIATION_ROUNDS,
    compute_our_offer,
    extract_price_from_reply,
    generate_agreement_message,
    generate_counter_offer_message,
    generate_opening_message,
    generate_rejection_response,
    is_acceptance,
    is_rejection,
)
from services.whatsapp_negotiator import get_whatsapp

logger = logging.getLogger(__name__)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class NegotiationManager:
    def __init__(self, db):
        self.db = db
        self.wa = get_whatsapp()

    async def _create_session(self, job_id, tech_id, phone, floor, budget) -> str:
        sid = str(uuid.uuid4())
        await self.db.table("whatsapp_negotiations").insert({
            "id": sid, "job_id": job_id, "technician_id": tech_id,
            "phone_number": phone, "status": "initiated", "current_round": 0,
            "floor_price": floor, "ceiling_price": budget,
            "created_at": _utc(), "started_at": _utc(),
        }).execute()
        return sid

    async def _update_session(self, sid: str, **kw):
        await self.db.table("whatsapp_negotiations").update(kw).eq("id", sid).execute()

    async def _log(self, sid, job_id, round_num, sender, message, our_offer=None, their_offer=None):
        await self.db.table("whatsapp_messages").insert({
            "id": str(uuid.uuid4()), "negotiation_id": sid, "job_id": job_id,
            "round_number": round_num, "sender": sender, "message": message,
            "our_offer": our_offer, "their_offer": their_offer, "sent_at": _utc(),
        }).execute()

    async def _finalize(self, job_id, tech_id, price):
        await self.db.table("jobs").update({
            "status": "assigned", "agreed_price": price, "assigned_tech_id": tech_id,
        }).eq("id", job_id).execute()
        logger.info("Job %s finalized at ₹%d — portal updated", job_id, price)

    # ── Entry ─────────────────────────────────────────────────────────────────

    async def run(self, job: dict, technician: dict) -> dict:
        job_id = job["id"]
        tech_id = technician["id"]
        phone = technician.get("phone_number", "")

        if not phone:
            raise ValueError(f"Technician {technician['name']} has no phone_number")

        budget = int(job["customer_budget"])
        floor = max(int(technician.get("rate_min", 100)), 1)

        # floor must be below budget, otherwise no deal is possible
        if floor >= budget:
            floor = max(1, budget - 100)

        logger.info("Negotiation | job=%s tech=%s budget=₹%d floor=₹%d", job_id, tech_id, budget, floor)

        sid = await self._create_session(job_id, tech_id, phone, floor, budget)
        await self.db.table("jobs").update({"status": "negotiating"}).eq("id", job_id).execute()

        try:
            return await self._loop(sid, job, technician, budget, floor)
        except Exception as exc:
            logger.error("Negotiation error: %s", exc)
            await self._update_session(sid, status="error", completed_at=_utc())
            await self.db.table("jobs").update({"status": "pending"}).eq("id", job_id).execute()
            raise

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _loop(self, sid, job, technician, budget, floor) -> dict:
        job_id = job["id"]
        tech_id = technician["id"]
        phone = technician["phone_number"]

        if not await self.wa.open_chat(phone):
            raise RuntimeError(f"Could not open WhatsApp chat for {phone}")

        await self._update_session(sid, status="in_progress")

        # Opening offer: budget - 200, clamped to [floor, budget]
        our_offer = max(floor, min(budget - 200, budget))
        their_last_offer: Optional[int] = None
        last_text: Optional[str] = None
        agreed_price: Optional[int] = None
        outcome = "timeout"

        # Wait for chat history to fully render, then snapshot the CURRENT
        # incoming message count. Any reply must arrive AFTER this baseline.
        await asyncio.sleep(3)  # let existing messages render
        _, last_count = await self.wa.read_last_incoming_message()
        logger.info("Baseline incoming count: %d", last_count)

        round_num = 0
        while round_num < NEGOTIATION_ROUNDS:
            round_num += 1
            await self._update_session(sid, current_round=round_num)

            # ── Send our offer ────────────────────────────────────────────────
            # Final safety clamp — never exceed budget
            our_offer = max(floor, min(our_offer, budget))

            if round_num == 1:
                msg = await generate_opening_message(job, technician, our_offer)
            else:
                msg = await generate_counter_offer_message(
                    job, technician, our_offer, their_last_offer, last_text or "", budget
                )

            if not await self.wa.send_message(msg):
                raise RuntimeError("Failed to send WhatsApp message")

            await self._log(sid, job_id, round_num, "ai", msg, our_offer=our_offer)
            logger.info("[Round %d] Sent ₹%d (budget ₹%d, floor ₹%d)", round_num, our_offer, budget, floor)

            # Re-snapshot count RIGHT AFTER sending — the send itself may have
            # triggered a UI update that shifts message indices
            await asyncio.sleep(2)
            _, last_count = await self.wa.read_last_incoming_message()
            logger.info("[Round %d] Post-send baseline count: %d", round_num, last_count)

            # ── Wait for reply ────────────────────────────────────────────────
            reply, last_count = await self.wa.wait_for_reply(after_count=last_count)

            if reply is None:
                logger.warning("[Round %d] Timeout — no reply", round_num)
                await self._log(sid, job_id, round_num, "system", "[timeout]")
                outcome = "timeout"
                break

            last_text = reply
            their_price = extract_price_from_reply(reply)
            if their_price:
                their_last_offer = their_price

            await self._log(sid, job_id, round_num, "technician", reply, their_offer=their_price)
            logger.info("[Round %d] Technician: '%s' | price extracted: %s", round_num, reply[:100], their_price)

            # ── Evaluate reply ────────────────────────────────────────────────

            if is_rejection(reply):
                farewell = await generate_rejection_response(technician, job)
                await self.wa.send_message(farewell)
                await self._log(sid, job_id, round_num, "ai", farewell)
                outcome = "rejected"
                break

            # Rule 1: technician explicitly accepted our offer
            if is_acceptance(reply, our_offer):
                agreed_price = our_offer
                outcome = "agreed"
                logger.info("[Round %d] Explicit acceptance at ₹%d", round_num, agreed_price)
                break

            # Rule 2: technician quoted a price
            if their_price:
                if their_price <= our_offer:
                    # They came down to or below what we offered — take it
                    agreed_price = their_price
                    outcome = "agreed"
                    logger.info("[Round %d] Tech ₹%d <= our offer ₹%d — deal", round_num, their_price, our_offer)
                    break
                elif their_price <= budget:
                    # Their ask is within budget but above our offer — counter toward them
                    our_offer = compute_our_offer(our_offer, their_price, budget, floor)
                    logger.info("[Round %d] Tech ₹%d in budget → our next offer ₹%d", round_num, their_price, our_offer)
                    # Continue loop — send counter next round
                else:
                    # Their ask is above budget — nudge up slightly, stay under budget
                    our_offer = compute_our_offer(our_offer, their_price, budget, floor)
                    logger.info("[Round %d] Tech ₹%d over budget → nudge to ₹%d", round_num, their_price, our_offer)
                    # Continue loop
            # else: no price extracted — keep same offer, continue loop

        # ── Finalize ──────────────────────────────────────────────────────────
        if outcome == "agreed" and agreed_price:
            # Hard safety check
            if agreed_price > budget:
                logger.error("agreed_price ₹%d > budget ₹%d — capping", agreed_price, budget)
                agreed_price = budget

            confirm = await generate_agreement_message(technician, agreed_price, job)
            await self.wa.send_message(confirm)
            await self._log(sid, job_id, round_num, "ai", confirm, our_offer=agreed_price)
            await self._finalize(job_id, tech_id, agreed_price)

        await self._update_session(sid, status=outcome, agreed_price=agreed_price,
                                   outcome=outcome, completed_at=_utc())

        return {
            "session_id": sid, "outcome": outcome,
            "agreed_price": agreed_price,
            "technician_name": technician["name"],
            "phone_number": phone, "rounds_taken": round_num,
        }
