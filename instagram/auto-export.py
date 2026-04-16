# -*- coding: utf-8 -*-
"""
RivalFit -- Auto Export Instagram Slides
Abre cada carrusel en un navegador headless y guarda todos los slides como PNG.

USO:
  python auto-export.py

Los PNGs se guardan en: ./exported-png/
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import sys
import time

# ─── CONFIG ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "exported-png"
OUTPUT_DIR.mkdir(exist_ok=True)

# Todos los archivos HTML a procesar (nuevos y existentes)
CARRUSELES = [
    # Nuevos carruseles
    "carrusel-01-motivacional.html",
    "carrusel-02-biomecanica-squat.html",
    "carrusel-03-promo-app.html",
    "carrusel-04-gestion-centros.html",
    "carrusel-05-anatomia-core.html",
    # Carruseles existentes
    "carousel-s1.html",
    "carousel-s2.html",
    "carousel-s3.html",
    "carousel-s4.html",
    "carousel-s5.html",
    # Posts individuales existentes
    "post-03-mindset.html",
    "post-04-duels.html",
    "post-05-centers.html",
    "story-01-hook.html",
    "story-02-reveal.html",
    "story-03-cta.html",
]

# ─── COLORES EN CONSOLA ────────────────────────────────────────────────
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def log(msg, color=RESET):
    print(f"{color}{msg}{RESET}", flush=True)

# ─── MAIN ──────────────────────────────────────────────────────────────
def main():
    log(f"\n{BOLD}{'='*60}", CYAN)
    log(f"  RIVALFIT -- AUTO EXPORT INSTAGRAM SLIDES", CYAN)
    log(f"{'='*60}{RESET}\n")
    log(f"  📁 Output: {OUTPUT_DIR}", YELLOW)
    log(f"  📄 Archivos a procesar: {len(CARRUSELES)}\n")

    total_slides = 0
    total_errors = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-web-security", "--allow-file-access-from-files"]
        )

        # Viewport grande para no afectar el layout
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
        )
        page = context.new_page()

        for html_file in CARRUSELES:
            file_path = BASE_DIR / html_file

            if not file_path.exists():
                log(f"  ⚠  {html_file} — no encontrado, saltando", YELLOW)
                continue

            log(f"  {BOLD}→ {html_file}{RESET}")

            try:
                # Cargar el HTML
                file_url = f"file:///{file_path.as_posix()}"
                page.goto(file_url, wait_until="networkidle", timeout=30000)

                # Esperar a que las fuentes de Google carguen
                page.wait_for_timeout(2500)

                # Obtener todos los elementos .canvas
                canvases = page.query_selector_all(".canvas")

                if not canvases:
                    log(f"     ⚠  Sin elementos .canvas encontrados", YELLOW)
                    continue

                stem = Path(html_file).stem

                for i, canvas in enumerate(canvases, start=1):
                    # Nombre del archivo de salida
                    output_name = f"{stem}-slide-{i:02d}.png"
                    output_path = OUTPUT_DIR / output_name

                    # Screenshot del elemento específico
                    canvas.screenshot(
                        path=str(output_path),
                        type="png",
                    )

                    # Obtener dimensiones para info
                    box = canvas.bounding_box()
                    w = int(box['width']) if box else 0
                    h = int(box['height']) if box else 0

                    log(f"     ✓  Slide {i:02d}: {output_name} ({w}×{h}px)", GREEN)
                    total_slides += 1

                log(f"     → {len(canvases)} slides exportados\n")

            except Exception as e:
                log(f"     ✗  Error: {e}", RED)
                total_errors += 1

        browser.close()

    # ─── RESUMEN ───────────────────────────────────────────────────────
    log(f"{BOLD}{'='*60}", CYAN)
    log(f"  EXPORTACION COMPLETADA", CYAN)
    log(f"{'='*60}", CYAN)
    log(f"  ✅ Slides generados: {total_slides}", GREEN if total_slides > 0 else YELLOW)
    if total_errors > 0:
        log(f"  ⚠  Errores: {total_errors}", RED)
    log(f"  📁 Carpeta: {OUTPUT_DIR}", YELLOW)
    log(f"{'='*60}\n", CYAN)

    # Listar archivos generados
    pngs = sorted(OUTPUT_DIR.glob("*.png"))
    if pngs:
        log(f"  Archivos PNG generados ({len(pngs)} total):\n", CYAN)
        for png in pngs:
            size_kb = png.stat().st_size // 1024
            log(f"    > {png.name} ({size_kb} KB)")

    print()

if __name__ == "__main__":
    main()
