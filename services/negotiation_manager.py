"""
Negotiation Manager — 3-stage WhatsApp flow.

STAGE 1 — CHECKING_AVAILABILITY
  Ask technician if they are available for the visit date/time.
  Wait for reply. If confirmed → Stage 2. If rejected → try next tech (caller handles).

STAGE 2 — NEGOTIATING_PRICE
  Start price negotiation only after availability is confirmed.
  Loop until: agreement, rejection, or max rounds.

STAGE 3 — DISPATCHED
  After deal closes, send full customer details (name, phone, address, visit, price).
  Update job status → "assigned" so frontend reflects the deal.
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
    generate_availability_message,
    generate_counter_offer_message,
    generate_dispatch_message,
    generate_price_opening,
    generate_rejection_response,
    is_acceptance,
    is_availability_confirmed,
    is_rejection,
)
from services.whatsapp_negotiator import get_whatsapp

logger = logging.getLogger(__name__)

STAGE_AVAILABILITY = "in_progress"   # maps to allowed DB value
STAGE_NEGOTIATING  = "in_progress"   # maps to allowed DB value
STAGE_DISPATCHED   = "agreed"        # maps to allowed DB value


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class NegotiationManager:
    def __init__(self, db):
        self.db = db
        self.wa = get_whatsapp()

    # ── DB helpers ────────────────────────────────────────────────────────────

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

    async def _log(self, sid, job_id, round_num, sender, message,
                   our_offer=None, their_offer=None):
        await self.db.table("whatsapp_messages").insert({
            "id": str(uuid.uuid4()), "negotiation_id": sid, "job_id": job_id,
            "round_number": round_num, "sender": sender, "message": message,
            "our_offer": our_offer, "their_offer": their_offer, "sent_at": _utc(),
        }).execute()

    async def _finalize(self, job_id, tech_id, price):
        await self.db.table("jobs").update({
            "status": "assigned", "agreed_price": price, "assigned_tech_id": tech_id,
        }).eq("id", job_id).execute()
        logger.info("Job %s finalized at Rs %d", job_id, price)

    # ── Entry ─────────────────────────────────────────────────────────────────

    async def run(self, job: dict, technician: dict) -> dict:
        job_id  = job["id"]
        tech_id = technician["id"]
        phone   = technician.get("phone_number", "")

        if not phone:
            raise ValueError(f"Technician {technician['name']} has no phone_number")

        budget = int(job["customer_budget"])
        floor  = max(int(technician.get("rate_min", 100)), 1)
        if floor >= budget:
            floor = max(1, budget - 100)

        logger.info("Negotiation start | job=%s tech=%s budget=Rs%d floor=Rs%d",
                    job_id, tech_id, budget, floor)

        sid = await self._create_session(job_id, tech_id, phone, floor, budget)
        await self.db.table("jobs").update({"status": "negotiating"}).eq("id", job_id).execute()

        try:
            return await self._run_stages(sid, job, technician, budget, floor)
        except Exception as exc:
            logger.error("Negotiation error: %s", exc)
            await self._update_session(sid, status="error", completed_at=_utc())
            await self.db.table("jobs").update({"status": "pending"}).eq("id", job_id).execute()
            raise

    # ── Stage orchestrator ────────────────────────────────────────────────────

    async def _run_stages(self, sid, job, technician, budget, floor) -> dict:
        job_id  = job["id"]
        tech_id = technician["id"]
        phone   = technician["phone_number"]

        if not await self.wa.open_chat(phone):
            raise RuntimeError(f"Could not open WhatsApp chat for {phone}")

        await self._update_session(sid, status="in_progress")

        # Snapshot existing messages so we don't mistake old texts for replies
        await asyncio.sleep(3)
        _, last_count = await self.wa.read_last_incoming_message()
        logger.info("Baseline message count: %d", last_count)

        # ── STAGE 1: Availability ─────────────────────────────────────────────
        await self._update_session(sid, status=STAGE_AVAILABILITY)
        avail_msg = await generate_availability_message(job, technician)

        if not await self.wa.send_message(avail_msg):
            raise RuntimeError("Failed to send availability message")

        await self._log(sid, job_id, 0, "ai", avail_msg)
        logger.info("[Stage 1] Sent availability check")

        # Re-snapshot after send
        await asyncio.sleep(2)
        _, last_count = await self.wa.read_last_incoming_message()

        avail_reply, last_count = await self.wa.wait_for_reply(after_count=last_count)

        if avail_reply is None:
            logger.warning("[Stage 1] No availability reply — timeout")
            await self._log(sid, job_id, 0, "system", "[No availability reply — timeout]")
            await self._update_session(sid, status="timeout", completed_at=_utc())
            return {"session_id": sid, "outcome": "timeout", "agreed_price": None,
                    "technician_name": technician["name"], "phone_number": phone, "rounds_taken": 0}

        await self._log(sid, job_id, 0, "technician", avail_reply)
        logger.info("[Stage 1] Technician replied: %s", avail_reply[:100])

        if is_rejection(avail_reply) or not is_availability_confirmed(avail_reply):
            logger.info("[Stage 1] Technician not available")
            farewell = await generate_rejection_response(technician, job)
            await self.wa.send_message(farewell)
            await self._log(sid, job_id, 0, "ai", farewell)
            await self._update_session(sid, status="rejected", completed_at=_utc())
            return {"session_id": sid, "outcome": "unavailable", "agreed_price": None,
                    "technician_name": technician["name"], "phone_number": phone, "rounds_taken": 0}

        logger.info("[Stage 1] Availability confirmed")

        # ── STAGE 2: Price negotiation ────────────────────────────────────────
        await self._update_session(sid, status=STAGE_NEGOTIATING)

        our_offer       = max(floor, min(budget - 200, budget))
        their_last_offer: Optional[int] = None
        last_text: Optional[str] = None
        agreed_price: Optional[int] = None
        outcome = "timeout"
        round_num = 0

        # Send opening price message
        price_open = await generate_price_opening(job, technician, our_offer)
        if not await self.wa.send_message(price_open):
            raise RuntimeError("Failed to send price opening message")

        await self._log(sid, job_id, 0, "ai", price_open, our_offer=our_offer)
        logger.info("[Stage 2] Sent price opening: Rs%d", our_offer)

        await asyncio.sleep(2)
        _, last_count = await self.wa.read_last_incoming_message()

        while round_num < NEGOTIATION_ROUNDS:
            round_num += 1
            await self._update_session(sid, current_round=round_num)

            # Wait for technician reply
            reply, last_count = await self.wa.wait_for_reply(after_count=last_count)

            if reply is None:
                logger.warning("[Round %d] Timeout", round_num)
                await self._log(sid, job_id, round_num, "system", "[timeout]")
                outcome = "timeout"
                break

            last_text = reply
            their_price = extract_price_from_reply(reply)
            if their_price:
                their_last_offer = their_price

            await self._log(sid, job_id, round_num, "technician", reply, their_offer=their_price)
            logger.info("[Round %d] Tech: '%s' | price: %s", round_num, reply[:100], their_price)

            # Hard rejection
            if is_rejection(reply):
                farewell = await generate_rejection_response(technician, job)
                await self.wa.send_message(farewell)
                await self._log(sid, job_id, round_num, "ai", farewell)
                outcome = "rejected"
                break

            # Accepted our offer
            if is_acceptance(reply, our_offer):
                agreed_price = our_offer
                outcome = "agreed"
                logger.info("[Round %d] Accepted Rs%d", round_num, agreed_price)
                break

            # Technician quoted a price
            if their_price:
                if their_price <= our_offer:
                    agreed_price = their_price
                    outcome = "agreed"
                    logger.info("[Round %d] Tech Rs%d <= our Rs%d — deal", round_num, their_price, our_offer)
                    break
                else:
                    # Counter toward their price (staying within budget)
                    next_offer = compute_our_offer(our_offer, their_price, budget, floor)
                    logger.info("[Round %d] Tech Rs%d → counter Rs%d", round_num, their_price, next_offer)
                    our_offer = next_offer

                    counter_msg = await generate_counter_offer_message(
                        job, technician, our_offer, their_price, reply, budget
                    )
                    if not await self.wa.send_message(counter_msg):
                        raise RuntimeError("Failed to send counter offer")

                    await self._log(sid, job_id, round_num, "ai", counter_msg, our_offer=our_offer)

                    await asyncio.sleep(2)
                    _, last_count = await self.wa.read_last_incoming_message()
                    continue
            else:
                # No price extracted — resend our current offer
                counter_msg = await generate_counter_offer_message(
                    job, technician, our_offer, None, reply, budget
                )
                if not await self.wa.send_message(counter_msg):
                    raise RuntimeError("Failed to send counter offer")

                await self._log(sid, job_id, round_num, "ai", counter_msg, our_offer=our_offer)

                await asyncio.sleep(2)
                _, last_count = await self.wa.read_last_incoming_message()

        # ── STAGE 3: Dispatch ─────────────────────────────────────────────────
        if outcome == "agreed" and agreed_price:
            if agreed_price > budget:
                logger.error("agreed_price Rs%d > budget Rs%d — capping", agreed_price, budget)
                agreed_price = budget

            await self._update_session(sid, status=STAGE_DISPATCHED)

            dispatch_msg = await generate_dispatch_message(job, technician, agreed_price)
            await self.wa.send_message(dispatch_msg)
            await self._log(sid, job_id, round_num, "ai", dispatch_msg, our_offer=agreed_price)
            logger.info("[Stage 3] Dispatch sent")

            await self._finalize(job_id, tech_id, agreed_price)

        await self._update_session(sid, status=outcome, agreed_price=agreed_price,
                                   outcome=outcome, completed_at=_utc())

        return {
            "session_id": sid, "outcome": outcome,
            "agreed_price": agreed_price,
            "technician_name": technician["name"],
            "phone_number": phone, "rounds_taken": round_num,
        }
