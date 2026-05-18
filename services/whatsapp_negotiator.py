"""
WhatsApp Web Automation — subprocess worker with thread-safe pipe communication.

Single WhatsApp account using whatsapp_session_2.
"""
import json
import logging
import os
import subprocess
import sys
import threading
import asyncio
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

WORKER_SCRIPT = Path(__file__).parent / "whatsapp_worker.py"
REPLY_WAIT_TIMEOUT = int(os.getenv("WA_REPLY_TIMEOUT_SEC", "300"))
REPLY_POLL_INTERVAL = float(os.getenv("WA_POLL_INTERVAL_SEC", "2"))

SESSION_DIR = os.getenv("WA_SESSION_DIR", "./whatsapp_session_2")


class WhatsAppNegotiator:
    def __init__(self, session_dir: str, label: str = ""):
        self._session_dir = session_dir
        self._label = label or session_dir
        self._proc: Optional[subprocess.Popen] = None
        self._ready = False
        self._send_lock = threading.Lock()
        self._pending: Optional[dict] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._startup_event = threading.Event()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self):
        Path(self._session_dir).mkdir(parents=True, exist_ok=True)
        self._proc = subprocess.Popen(
            [sys.executable, str(WORKER_SCRIPT), self._session_dir],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,  # worker stderr → terminal
            bufsize=0,
        )
        logger.info("[%s] Worker started (pid=%s)", self._label, self._proc.pid)

        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name=f"wa-reader-{self._label}"
        )
        self._reader_thread.start()

        # Wait up to 90s for ready signal
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._startup_event.wait(timeout=90))
        self._ready = True
        logger.info("[%s] WhatsApp negotiator ready", self._label)

    def _reader_loop(self):
        while self._proc and self._proc.poll() is None:
            try:
                raw = self._proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode().strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("[%s] Non-JSON from worker: %s", self._label, line)
                    continue

                if msg.get("event") == "ready":
                    logger.info("[%s] Worker signalled ready", self._label)
                    self._startup_event.set()
                    continue

                if self._pending is not None:
                    self._pending["result"] = msg
                    self._pending["event"].set()
                else:
                    logger.debug("[%s] Unrouted worker message: %s", self._label, msg)

            except Exception as exc:
                logger.error("[%s] Reader loop error: %s", self._label, exc)
                break
        logger.info("[%s] Worker reader loop exited", self._label)

    async def stop(self):
        if self._proc:
            try:
                await self._send({"action": "quit"}, timeout=5.0)
            except Exception:
                pass
            self._proc.terminate()
        self._ready = False

    # ── Core send/receive ─────────────────────────────────────────────────────

    def _send_sync(self, cmd: dict, timeout: float = 35.0) -> dict:
        with self._send_lock:
            # Auto-restart worker if it died
            if self._proc is None or self._proc.poll() is not None:
                logger.warning("[%s] Worker is dead — restarting", self._label)
                self._startup_event.clear()
                self._ready = False
                Path(self._session_dir).mkdir(parents=True, exist_ok=True)
                self._proc = subprocess.Popen(
                    [sys.executable, str(WORKER_SCRIPT), self._session_dir],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=None,
                    bufsize=0,
                )
                self._reader_thread = threading.Thread(
                    target=self._reader_loop, daemon=True,
                    name=f"wa-reader-{self._label}-restart"
                )
                self._reader_thread.start()
                # Wait for ready
                self._startup_event.wait(timeout=90)
                self._ready = True
                logger.info("[%s] Worker restarted", self._label)

            event = threading.Event()
            self._pending = {"event": event, "result": None}

            line = (json.dumps(cmd) + "\n").encode()
            self._proc.stdin.write(line)
            self._proc.stdin.flush()

            if not event.wait(timeout=timeout):
                self._pending = None
                raise TimeoutError(f"[{self._label}] Worker timed out for: {cmd['action']}")

            result = self._pending["result"]
            self._pending = None
            return result or {}

    async def _send(self, cmd: dict, timeout: float = 35.0) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._send_sync(cmd, timeout))

    # ── Public API ────────────────────────────────────────────────────────────

    async def is_session_ready(self) -> bool:
        try:
            resp = await self._send({"action": "status"}, timeout=5.0)
            return resp.get("ready", False)
        except Exception:
            return False

    async def open_chat(self, phone_number: str) -> bool:
        digits = "".join(c for c in phone_number if c.isdigit())
        wa_number = f"91{digits}" if len(digits) == 10 else digits
        logger.info("[%s] Opening chat for %s", self._label, wa_number)
        resp = await self._send({"action": "open_chat", "wa_number": wa_number}, timeout=40.0)
        ok = resp.get("ok", False)
        if not ok:
            logger.error("[%s] open_chat failed: %s", self._label, resp.get("error"))
        return ok

    async def send_message(self, message: str) -> bool:
        logger.info("[%s] Sending: %s", self._label, message[:80])
        resp = await self._send({"action": "send_message", "message": message}, timeout=25.0)
        ok = resp.get("ok", False)
        if not ok:
            logger.error("[%s] send_message failed: %s", self._label, resp.get("error"))
        return ok

    async def read_last_incoming_message(self) -> tuple[Optional[str], int, str]:
        """Returns (text, incoming_count, fingerprint).
        Fingerprint = 'total:incoming_count:last_text' — unique even for repeated messages."""
        resp = await self._send({"action": "read_last"}, timeout=10.0)
        return resp.get("text"), resp.get("count", 0), resp.get("fingerprint", "0:0:")

    async def wait_for_reply(
        self,
        after_fingerprint: str = "",
        timeout_sec: int = REPLY_WAIT_TIMEOUT,
    ) -> tuple[Optional[str], str]:
        """
        Poll until a NEW incoming message appears.
        Uses fingerprint (total:count:text) so even repeated identical texts are detected.
        Returns (reply_text, new_fingerprint).
        """
        deadline = asyncio.get_event_loop().time() + timeout_sec
        while asyncio.get_event_loop().time() < deadline:
            text, count, fingerprint = await self.read_last_incoming_message()
            if fingerprint != after_fingerprint and count > 0:
                # Extra guard: only accept if total DOM count changed OR text changed
                after_total = int(after_fingerprint.split(":")[0]) if after_fingerprint else 0
                current_total = int(fingerprint.split(":")[0]) if fingerprint else 0
                if current_total > after_total or fingerprint != after_fingerprint:
                    logger.info("[%s] Reply detected fp=%s text=%s",
                                self._label, fingerprint, (text or "")[:80])
                    return text, fingerprint
            await asyncio.sleep(REPLY_POLL_INTERVAL)
        logger.warning("[%s] No reply within %ds", self._label, timeout_sec)
        return None, after_fingerprint

    async def get_session_status(self) -> dict:
        alive = self._proc is not None and self._proc.poll() is None
        ready = False
        if alive:
            try:
                ready = await self.is_session_ready()
            except Exception:
                pass
        return {
            "label": self._label,
            "ready": ready,
            "worker_alive": alive,
            "session_dir": self._session_dir,
        }


# ── Single instance ───────────────────────────────────────────────────────────

_instance: Optional[WhatsAppNegotiator] = None


def get_whatsapp(account: str = "default") -> WhatsAppNegotiator:
    global _instance
    if _instance is None:
        _instance = WhatsAppNegotiator(session_dir=SESSION_DIR, label="whatsapp")
    return _instance
