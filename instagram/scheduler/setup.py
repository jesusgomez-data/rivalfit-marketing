# -*- coding: utf-8 -*-
"""
RivalFit -- Setup Inicial
Ejecuta esto UNA SOLA VEZ antes de usar el sistema automatico.

Hace:
  1. Valida las credenciales de Instagram y imgbb
  2. Sube todos los PNGs a imgbb (hosting publico)
  3. Guarda las URLs en image_urls.json
  4. Configura Windows Task Scheduler para publicar cada dia

USO:
  python setup.py
"""

import json
import base64
import time
import subprocess
import sys
import os
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent
PNG_DIR  = ROOT_DIR / "exported-png"
URLS_FILE = BASE_DIR / "image_urls.json"
CONFIG_FILE = BASE_DIR / "config.json"

# ── Colores consola ──────────────────────────────────────────────────────────
def c(text, color):
    colors = {"red":"\033[91m","green":"\033[92m","yellow":"\033[93m",
              "cyan":"\033[96m","white":"\033[97m","reset":"\033[0m","bold":"\033[1m"}
    return f"{colors.get(color,'')}{text}{colors['reset']}"

def header(title):
    print(f"\n{c('='*60, 'cyan')}")
    print(f"{c(f'  {title}', 'cyan')}")
    print(f"{c('='*60, 'cyan')}")

def ok(msg):   print(f"  {c('[OK]', 'green')}  {msg}")
def err(msg):  print(f"  {c('[ERROR]', 'red')}  {msg}")
def info(msg): print(f"  {c('[INFO]', 'yellow')}  {msg}")
def step(msg): print(f"\n  {c('>>', 'cyan')} {c(msg, 'bold')}")

# ── Cargar config ─────────────────────────────────────────────────────────────
def load_config():
    if not CONFIG_FILE.exists():
        err(f"config.json no encontrado en {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)

# ── Validar credenciales Instagram ────────────────────────────────────────────
def validate_instagram(config):
    step("Validando credenciales de Instagram...")
    user_id = config.get("instagram_user_id", "")
    token   = config.get("instagram_access_token", "")

    if "PON_AQUI" in user_id or "PON_AQUI" in token:
        err("Tienes que rellenar instagram_user_id y instagram_access_token en config.json")
        err("Consulta el archivo COMO_OBTENER_CREDENCIALES.md")
        return False

    url = f"https://graph.facebook.com/v18.0/{user_id}"
    r = requests.get(url, params={"access_token": token}, timeout=10)
    data = r.json()

    if "error" in data:
        err(f"Instagram API error: {data['error'].get('message', data)}")
        return False

    name = data.get("name", "?")
    ok(f"Conectado a Instagram como: {name} (ID: {user_id})")

    # Advertir si el token expira pronto
    debug_url = "https://graph.facebook.com/debug_token"
    dr = requests.get(debug_url, params={
        "input_token": token,
        "access_token": token
    }, timeout=10)
    debug_data = dr.json().get("data", {})
    expires_at = debug_data.get("expires_at", 0)
    if expires_at:
        expires_dt = datetime.fromtimestamp(expires_at)
        days_left = (expires_dt - datetime.now()).days
        if days_left < 10:
            err(f"Tu token expira en {days_left} dias! Renovaló en COMO_OBTENER_CREDENCIALES.md")
        else:
            ok(f"Token valido por {days_left} dias mas (expira {expires_dt.strftime('%Y-%m-%d')})")

    return True

# ── Validar imgbb ─────────────────────────────────────────────────────────────
def validate_imgbb(config):
    step("Validando API key de imgbb...")
    api_key = config.get("imgbb_api_key", "")

    if "PON_AQUI" in api_key:
        err("Tienes que rellenar imgbb_api_key en config.json")
        err("Ve a imgbb.com -> API -> Get API Key (es gratis)")
        return False

    # Test con imagen minima (1x1 pixel transparente)
    pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    r = requests.post("https://api.imgbb.com/1/upload",
                      data={"key": api_key, "image": pixel, "name": "test_rival"},
                      timeout=15)
    data = r.json()
    if data.get("success"):
        ok("imgbb API key valida")
        return True
    else:
        err(f"imgbb error: {data}")
        return False

# ── Subir imagen a imgbb ──────────────────────────────────────────────────────
def upload_image(api_key, image_path):
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    r = requests.post(
        "https://api.imgbb.com/1/upload",
        data={
            "key": api_key,
            "image": image_b64,
            "name": image_path.stem,
        },
        timeout=30
    )
    data = r.json()
    if data.get("success"):
        return data["data"]["url"]
    else:
        raise Exception(f"imgbb error para {image_path.name}: {data}")

# ── Subir todos los PNGs ──────────────────────────────────────────────────────
def upload_all_images(config):
    step("Subiendo imagenes PNG a imgbb (hosting publico para Instagram)...")

    api_key = config["imgbb_api_key"]

    # Cargar URLs ya existentes (para no re-subir)
    existing_urls = {}
    if URLS_FILE.exists():
        with open(URLS_FILE, encoding="utf-8") as f:
            existing_urls = json.load(f)

    # Agrupar PNGs por carrusel
    all_pngs = sorted(PNG_DIR.glob("*.png"))
    if not all_pngs:
        err(f"No hay PNGs en {PNG_DIR}")
        err("Ejecuta primero: python auto-export.py")
        return False

    # Construir mapa carrusel -> lista de slides ordenados
    carrusel_map = {}
    for png in all_pngs:
        # Nombre: carrusel-01-motivacional-slide-01.png
        # Extraer el nombre base del carrusel (sin -slide-XX)
        name = png.stem
        if "-slide-" in name:
            carrusel_key = name.rsplit("-slide-", 1)[0]
        else:
            carrusel_key = name

        if carrusel_key not in carrusel_map:
            carrusel_map[carrusel_key] = []
        carrusel_map[carrusel_key].append(png)

    # Ordenar slides dentro de cada carrusel
    for key in carrusel_map:
        carrusel_map[key].sort()

    total = sum(len(v) for v in carrusel_map.values())
    info(f"Encontrados {len(carrusel_map)} carruseles, {total} slides en total")

    uploaded = 0
    skipped  = 0

    for carrusel_key, slides in carrusel_map.items():
        print(f"\n  Carrusel: {c(carrusel_key, 'bold')}")
        urls_for_carrusel = existing_urls.get(carrusel_key, [])

        # Si ya tiene todas las URLs, saltar
        if len(urls_for_carrusel) == len(slides):
            info(f"Ya subido ({len(slides)} slides). Saltando.")
            skipped += len(slides)
            continue

        # Subir los slides que faltan
        new_urls = []
        for slide_path in slides:
            # Comprobar si ya existe URL para este slide
            slide_idx = slides.index(slide_path)
            if slide_idx < len(urls_for_carrusel) and urls_for_carrusel[slide_idx]:
                new_urls.append(urls_for_carrusel[slide_idx])
                skipped += 1
                print(f"    {c('[SKIP]', 'yellow')} {slide_path.name} (ya subido)")
                continue

            try:
                url = upload_image(api_key, slide_path)
                new_urls.append(url)
                uploaded += 1
                print(f"    {c('[OK]', 'green')} {slide_path.name}")
                print(f"         {c(url, 'cyan')}")
                # Esperar para no superar el rate limit de imgbb (100/hora free)
                time.sleep(0.8)
            except Exception as e:
                err(str(e))
                new_urls.append(None)

        existing_urls[carrusel_key] = new_urls

        # Guardar progreso tras cada carrusel (por si se interrumpe)
        with open(URLS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_urls, f, indent=2, ensure_ascii=False)

    print()
    ok(f"Subida completada: {uploaded} nuevas, {skipped} ya existian")
    ok(f"URLs guardadas en: {URLS_FILE}")
    return True

# ── Configurar Windows Task Scheduler ────────────────────────────────────────
def setup_task_scheduler(config):
    step("Configurando Windows Task Scheduler...")

    hora = config.get("hora_publicacion", "09:00")
    publisher_path = (BASE_DIR / "publisher.py").resolve()
    python_exe = sys.executable

    # Crear un bat que use la ruta de Python correcta
    bat_path = BASE_DIR / "run_publisher.bat"
    bat_content = f"""@echo off
"{python_exe}" "{publisher_path}" >> "{BASE_DIR / 'logs' / 'task_scheduler.log'}" 2>&1
"""
    with open(bat_path, "w") as f:
        f.write(bat_content)

    task_name = "RivalFit_Instagram_Publisher"

    # Eliminar tarea anterior si existe
    subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True
    )

    # Crear nueva tarea diaria
    result = subprocess.run([
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", str(bat_path),
        "/sc", "DAILY",
        "/st", hora,
        "/rl", "HIGHEST",
        "/f"
    ], capture_output=True, text=True)

    if result.returncode == 0:
        ok(f"Task Scheduler configurado: publica cada dia a las {hora}")
        ok(f"Nombre de la tarea: {task_name}")
        info("Para ver/editar: Abre 'Programador de tareas' en Windows")
    else:
        err(f"Error configurando Task Scheduler: {result.stderr}")
        info("Alternativa: ejecuta manualmente 'python publisher.py' cada dia")

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    header("RIVALFIT -- SETUP INICIAL")
    print(f"  Directorio: {BASE_DIR}")
    print(f"  PNGs:       {PNG_DIR}")
    print()

    config = load_config()

    # Paso 1: Validar Instagram
    ig_ok = validate_instagram(config)
    if not ig_ok:
        print()
        err("Corrige las credenciales de Instagram y vuelve a ejecutar setup.py")
        print(f"\n  {c('Consulta: COMO_OBTENER_CREDENCIALES.md', 'yellow')}\n")
        sys.exit(1)

    # Paso 2: Validar imgbb
    imgbb_ok = validate_imgbb(config)
    if not imgbb_ok:
        print()
        err("Corrige la API key de imgbb y vuelve a ejecutar setup.py")
        sys.exit(1)

    # Paso 3: Subir imágenes
    upload_ok = upload_all_images(config)
    if not upload_ok:
        sys.exit(1)

    # Paso 4: Task Scheduler
    setup_task_scheduler(config)

    # Resumen final
    header("SETUP COMPLETADO")
    ok("Instagram API: conectado")
    ok("imgbb: imagenes subidas")
    ok("Windows Task Scheduler: configurado")
    print(f"\n  {c('El sistema publicara automaticamente segun schedule.json', 'green')}")
    print(f"  {c('Para cambiar el calendario, edita: scheduler/schedule.json', 'yellow')}")
    print(f"  {c('Para anadir nuevos carruseles, ejecuta de nuevo: python setup.py', 'yellow')}")
    print()

if __name__ == "__main__":
    main()
