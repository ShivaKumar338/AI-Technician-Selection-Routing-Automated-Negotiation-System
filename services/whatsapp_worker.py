"""
WhatsApp Worker Process — fully synchronous Playwright, no asyncio.

Launched as a subprocess by whatsapp_negotiator.py.
Reads JSON commands from stdin, writes JSON responses to stdout.
Stderr goes to terminal for logging.
"""
import json
import sys
import time
import logging

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="WA-WORKER %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

WA_URL = "https://web.whatsapp.com"
WA_LOAD_TIMEOUT = 90000  # ms

INPUT_SELECTORS = [
    'div[data-testid="conversation-compose-box-input"]',
    'div[contenteditable="true"][data-tab="10"]',
    'footer div[contenteditable="true"]',
    'div[role="textbox"][data-tab="10"]',
]

SEND_SELECTORS = [
    'button[data-testid="compose-btn-send"]',
    'button[aria-label="Send"]',
    'button[aria-label="Send message"]',
    'span[data-icon="send"]',
]


# JS that extracts all messages from the chat, returning list of
# {text, outgoing} objects. Works regardless of WhatsApp's obfuscated classes
# by using data-testid and DOM position (outgoing msgs have a tail on the right).
READ_MESSAGES_JS = """
() => {
    const results = [];

    // Strategy 1: data-testid on message rows
    const rows = document.querySelectorAll(
        '[data-testid="msg-container"], [data-testid="message-container"]'
    );
    if (rows.length > 0) {
        rows.forEach(row => {
            // Outgoing messages have data-testid="msg-dblcheck" or "msg-check" (tick icons)
            // Incoming messages have neither
            const isOutgoing = !!row.querySelector(
                '[data-testid="msg-dblcheck"], [data-testid="msg-check"], [data-testid="msg-time"]'
            ) && row.closest('[class*="message-out"], [class*="msg-out"]') !== null;

            // Simpler: check if the bubble is right-aligned (outgoing) or left-aligned (incoming)
            // WhatsApp wraps outgoing in a div that has "message-out" somewhere in its class chain
            let outgoing = false;
            let el = row;
            for (let i = 0; i < 6; i++) {
                if (!el) break;
                const cls = el.className || '';
                if (cls.includes('message-out') || cls.includes('msg-out')) {
                    outgoing = true;
                    break;
                }
                el = el.parentElement;
            }

            const spans = row.querySelectorAll('span[dir="ltr"], span[dir="rtl"]');
            let text = '';
            spans.forEach(s => {
                const t = s.innerText.trim();
                if (t && t.length > 0 && !t.match(/^[0-9]{1,2}:[0-9]{2}$/)) {
                    text = t;  // take last non-empty, non-timestamp span
                }
            });
            if (text) results.push({text, outgoing});
        });
        if (results.length > 0) return results;
    }

    // Strategy 2: fallback — all selectable-text spans, guess direction from parent
    const allSpans = document.querySelectorAll('span.selectable-text span[dir]');
    allSpans.forEach(span => {
        const text = span.innerText.trim();
        if (!text || text.match(/^[0-9]{1,2}:[0-9]{2}$/)) return;
        let outgoing = false;
        let el = span;
        for (let i = 0; i < 10; i++) {
            if (!el) break;
            const cls = el.className || '';
            if (cls.includes('message-out') || cls.includes('msg-out')) { outgoing = true; break; }
            if (cls.includes('message-in') || cls.includes('msg-in')) { outgoing = false; break; }
            el = el.parentElement;
        }
        results.push({text, outgoing});
    });
    return results;
}
"""


def send(obj: dict):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def recv() -> dict:
    line = sys.stdin.readline()
    if not line:
        return {"action": "quit"}
    return json.loads(line.strip())


def find_input(page):
    for sel in INPUT_SELECTORS:
        try:
            el = page.wait_for_selector(sel, timeout=4000)
            if el:
                return el, sel
        except Exception:
            continue
    return None, None


def clear_and_type(page, box, message: str):
    """
    Reliable message entry:
    1. Click to focus
    2. Select all + delete to clear
    3. Use clipboard paste (most reliable on WhatsApp Web)
    4. Fallback to keyboard.type if clipboard fails
    """
    box.click()
    time.sleep(0.2)

    # Clear existing content
    page.keyboard.press("Control+A")
    time.sleep(0.05)
    page.keyboard.press("Delete")
    time.sleep(0.05)
    page.keyboard.press("Control+A")
    time.sleep(0.05)
    page.keyboard.press("Backspace")
    time.sleep(0.1)

    # Verify empty
    current = box.inner_text().strip()
    if current:
        # Force clear via JS
        page.evaluate("el => { el.innerHTML = ''; el.textContent = ''; }", box)
        time.sleep(0.1)

    # Try clipboard paste first (most reliable — avoids char-by-char issues)
    try:
        page.evaluate(
            """async (text) => {
                await navigator.clipboard.writeText(text);
            }""",
            message,
        )
        time.sleep(0.1)
        box.click()
        time.sleep(0.1)
        page.keyboard.press("Control+V")
        time.sleep(0.3)

        # Verify text appeared
        typed = box.inner_text().strip()
        if typed and len(typed) > 0:
            return True
    except Exception as e:
        logger.warning("Clipboard paste failed: %s — falling back to keyboard.type", e)

    # Fallback: keyboard.type (slower but works without clipboard permission)
    box.click()
    time.sleep(0.1)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    time.sleep(0.1)
    page.keyboard.type(message, delay=15)
    time.sleep(0.3)
    return True


def main(session_dir: str):
    from playwright.sync_api import sync_playwright

    logger.info("Starting Playwright (sync) with session: %s", session_dir)

    # Kill only the Chromium process that's locking OUR session directory
    # (not the user's regular Chrome browser)
    import subprocess as _sp, psutil as _ps, os as _os
    session_abs = _os.path.abspath(session_dir)
    try:
        for proc in _ps.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = (proc.info['name'] or '').lower()
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'chrome' in name and session_abs in cmdline:
                    logger.info("Killing stale Chromium pid=%d locking %s", proc.pid, session_dir)
                    proc.kill()
            except (_ps.NoSuchProcess, _ps.AccessDenied):
                pass
    except Exception as e:
        logger.warning("Could not check for stale Chromium: %s", e)
    time.sleep(1)

    with sync_playwright() as pw:
        try:
            context = pw.chromium.launch_persistent_context(
                user_data_dir=session_dir,
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                ],
                viewport={"width": 1280, "height": 900},
            )
        except Exception as exc:
            logger.error("Failed to launch browser: %s", exc)
            send({"event": "ready", "ok": False, "error": str(exc)})
            return

        page = context.pages[0] if context.pages else context.new_page()

        # Grant clipboard permissions
        try:
            context.grant_permissions(["clipboard-read", "clipboard-write"])
        except Exception:
            pass

        try:
            page.goto(WA_URL, wait_until="domcontentloaded")
        except Exception as exc:
            logger.error("Failed to navigate to WhatsApp: %s", exc)
            send({"event": "ready", "ok": False, "error": str(exc)})
            return

        logger.info("Waiting for WhatsApp Web to load (scan QR if needed)...")
        try:
            page.wait_for_selector('div[data-testid="chat-list"]', timeout=WA_LOAD_TIMEOUT)
            logger.info("WhatsApp Web ready")
            send({"event": "ready", "ok": True})
        except Exception:
            logger.warning("Chat list not visible — QR scan may be needed")
            send({"event": "ready", "ok": True, "note": "scan QR if needed"})

        # ── Command loop ──────────────────────────────────────────────────────
        while True:
            try:
                cmd = recv()
                action = cmd.get("action", "")

                if action == "quit":
                    send({"ok": True})
                    break

                elif action == "status":
                    el = page.query_selector('div[data-testid="chat-list"]')
                    send({"ok": True, "ready": el is not None})

                elif action == "open_chat":
                    wa_number = cmd.get("wa_number", "")
                    url = f"https://web.whatsapp.com/send?phone={wa_number}&text="
                    logger.info("Opening chat: %s", url)
                    try:
                        page.goto(url, wait_until="domcontentloaded")
                        box, _ = find_input(page)
                        if box:
                            send({"ok": True})
                        else:
                            send({"ok": False, "error": "Could not find message input after navigation"})
                    except Exception as exc:
                        logger.error("open_chat failed: %s", exc)
                        send({"ok": False, "error": str(exc)})

                elif action == "send_message":
                    message = cmd.get("message", "")
                    try:
                        box, sel = find_input(page)
                        if not box:
                            raise RuntimeError("Could not find message input box")

                        clear_and_type(page, box, message)

                        # Find and click send button
                        sent = False
                        for selector in SEND_SELECTORS:
                            try:
                                btn = page.wait_for_selector(selector, timeout=3000)
                                if btn:
                                    btn.click()
                                    sent = True
                                    break
                            except Exception:
                                continue

                        if not sent:
                            # Fallback: press Enter
                            box.press("Enter")

                        time.sleep(0.8)

                        # Verify message was sent (input should be empty now)
                        try:
                            remaining = box.inner_text().strip()
                            if remaining:
                                logger.warning("Input not cleared after send — forcing Enter")
                                box.press("Enter")
                                time.sleep(0.5)
                        except Exception:
                            pass

                        logger.info("Sent: %s", message[:80])
                        send({"ok": True})
                    except Exception as exc:
                        logger.error("send_message failed: %s", exc)
                        send({"ok": False, "error": str(exc)})

                elif action == "read_last":
                    try:
                        all_msgs = page.evaluate(READ_MESSAGES_JS)
                        # Filter to incoming only
                        incoming = [m for m in (all_msgs or []) if not m.get("outgoing")]
                        if incoming:
                            last = incoming[-1]["text"].strip()
                            send({"ok": True, "text": last or None, "count": len(incoming)})
                            logger.info("read_last: %d incoming msgs, last: %s", len(incoming), last[:60] if last else "None")
                        else:
                            send({"ok": True, "text": None, "count": 0})
                            logger.info("read_last: no incoming messages found (total msgs: %d)", len(all_msgs or []))
                    except Exception as exc:
                        logger.error("read_last failed: %s", exc)
                        send({"ok": True, "text": None, "count": 0})

                elif action == "debug_messages":
                    # Returns ALL messages (incoming + outgoing) for diagnosis
                    try:
                        all_msgs = page.evaluate(READ_MESSAGES_JS)
                        send({"ok": True, "messages": all_msgs or []})
                    except Exception as exc:
                        send({"ok": False, "error": str(exc)})

                else:
                    send({"ok": False, "error": f"Unknown action: {action}"})

            except (EOFError, BrokenPipeError):
                logger.info("Parent process closed — exiting")
                break
            except Exception as exc:
                logger.error("Command error: %s", exc)
                # Check if browser died
                try:
                    page.title()  # will throw if browser is gone
                except Exception:
                    logger.error("Browser appears to have crashed — exiting worker")
                    send({"ok": False, "error": "browser_crashed"})
                    break
                send({"ok": False, "error": str(exc)})

        try:
            context.close()
        except Exception:
            pass
        logger.info("Worker exiting cleanly")


if __name__ == "__main__":
    session_dir = sys.argv[1] if len(sys.argv) > 1 else "./whatsapp_session"
    main(session_dir)
