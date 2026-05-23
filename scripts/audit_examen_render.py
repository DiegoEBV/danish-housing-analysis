"""
Structured render audit for examen/examen_respuestas.html.

This script prints DOM and Chart.js metadata used by the chart-supervisor audit.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import time
from pathlib import Path

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parent.parent
EXAM_DIR = ROOT / "examen"
PORT = 8770
URL = f"http://127.0.0.1:{PORT}/examen_respuestas.html"


async def main() -> int:
    proc = subprocess.Popen(
        ["python3", "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=EXAM_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.4)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 1100})
            await page.goto(URL, wait_until="networkidle")

            tabs = []
            for tab in ["c1", "c2", "c3", "c4", "c5"]:
                await page.click(f"button[onclick=\"activateTab('{tab}')\"]")
                await page.wait_for_timeout(300)
                tabs.append(await page.evaluate("""
                    (tab) => {
                      const panel = document.querySelector(`#panel-${tab}`);
                      const canvas = panel.querySelector('canvas');
                      const chart = canvas ? Chart.getChart(canvas) : null;
                      const imgs = [...panel.querySelectorAll('img')].map((img) => ({
                        src: img.getAttribute('src'),
                        complete: img.complete,
                        naturalWidth: img.naturalWidth,
                        naturalHeight: img.naturalHeight,
                      }));
                      return {
                        tab,
                        questions: panel.querySelectorAll('.pregunta-num').length,
                        cierre: panel.querySelectorAll('.cierre-reflexivo').length,
                        images: imgs,
                        canvas: canvas ? {
                          id: canvas.id,
                          width: canvas.width,
                          height: canvas.height,
                          clientWidth: canvas.clientWidth,
                          clientHeight: canvas.clientHeight,
                        } : null,
                        chart: chart ? {
                          type: chart.config.type,
                          labels: chart.data.labels?.length || null,
                          datasets: chart.data.datasets.map((d) => ({
                            label: d.label,
                            points: d.data.length,
                          })),
                        } : null,
                      };
                    }
                """, tab))

            mobile = await browser.new_page(viewport={"width": 390, "height": 900})
            await mobile.goto(URL, wait_until="networkidle")
            mobile_overflow = await mobile.evaluate("""
                () => ({
                  scrollWidth: document.documentElement.scrollWidth,
                  clientWidth: document.documentElement.clientWidth,
                  bodyScrollWidth: document.body.scrollWidth,
                })
            """)
            await browser.close()

        print(json.dumps({"tabs": tabs, "mobile_overflow": mobile_overflow}, indent=2))
        return 0
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
