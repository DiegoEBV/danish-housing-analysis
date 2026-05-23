"""
Capture screenshots for the exam dashboard tabs.

Requires Playwright, installed as a dev dependency:
    uv sync --group dev
    uv run playwright install chromium

Usage:
    .venv/bin/python scripts/capture_examen_screenshots.py
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EXAM_DIR = ROOT / "examen"
HTML_FILE = EXAM_DIR / "examen_respuestas.html"
OUT_DIR = EXAM_DIR / "screenshots"
PORT = 8765
BASE_URL = f"http://127.0.0.1:{PORT}/examen_respuestas.html"

TABS = [
    ("caso1", "button[onclick=\"activateTab('c1')\"]"),
    ("caso2", "button[onclick=\"activateTab('c2')\"]"),
    ("caso3", "button[onclick=\"activateTab('c3')\"]"),
    ("caso4", "button[onclick=\"activateTab('c4')\"]"),
    ("caso5", "button[onclick=\"activateTab('c5')\"]"),
]


def ensure_playwright() -> Any:
    try:
        from playwright.async_api import async_playwright
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Playwright is not installed. Install it with:\n"
            "  .venv/bin/python -m pip install playwright\n"
            "  .venv/bin/python -m playwright install chromium"
        ) from exc
    return async_playwright


def start_server() -> subprocess.Popen[str]:
    if not HTML_FILE.exists():
        raise SystemExit(f"Missing HTML file: {HTML_FILE}")

    python = shutil.which("python3") or sys.executable
    proc = subprocess.Popen(
        [python, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=EXAM_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    time.sleep(0.5)
    if proc.poll() is not None:
        raise SystemExit("Could not start local HTTP server for screenshot capture.")
    return proc


async def capture() -> int:
    async_playwright = ensure_playwright()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    console_messages: list[dict[str, str]] = []
    page_errors: list[str] = []
    bad_responses: list[dict[str, str | int]] = []
    failed_requests: list[dict[str, str]] = []

    server = start_server()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 1100})
            page.on(
                "console",
                lambda msg: console_messages.append({"type": msg.type, "text": msg.text}),
            )
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on(
                "response",
                lambda response: bad_responses.append({
                    "status": response.status,
                    "url": response.url,
                }) if response.status >= 400 else None,
            )
            page.on(
                "requestfailed",
                lambda request: failed_requests.append({
                    "url": request.url,
                    "failure": request.failure or "",
                }),
            )

            await page.goto(BASE_URL, wait_until="networkidle")

            for name, selector in TABS:
                await page.click(selector)
                await page.wait_for_timeout(500)
                await page.screenshot(path=OUT_DIR / f"{name}.png", full_page=True)

            await browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)

    report = {
        "url": BASE_URL,
        "screenshots": [f"{name}.png" for name, _ in TABS],
        "console": console_messages,
        "page_errors": page_errors,
        "bad_responses": bad_responses,
        "failed_requests": failed_requests,
    }
    (OUT_DIR / "console.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    severe_console = [
        msg for msg in console_messages
        if msg["type"] in {"error", "warning"} and "favicon" not in msg["text"].lower()
    ]
    print(f"Screenshots written to {OUT_DIR}")
    print(f"Console warnings/errors: {len(severe_console)}")
    print(f"Page errors: {len(page_errors)}")
    print(f"HTTP 4xx/5xx responses: {len(bad_responses)}")
    print(f"Failed requests: {len(failed_requests)}")
    return 1 if severe_console or page_errors or bad_responses or failed_requests else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(capture()))
