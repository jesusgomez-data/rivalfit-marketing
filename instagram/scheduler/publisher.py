# -*- coding: utf-8 -*-
"""
RivalFit -- Publicador Automatico de Instagram
Se ejecuta cada dia via Windows Task Scheduler.

Hace:
  1. Lee el calendario (schedule.json) y busca el post de hoy
  2. Obtiene las URLs publicas de las imagenes (image_urls.json)
  3. Publica el carrusel en Instagram via Meta Graph API
  4. Registra el resultado en logs/

USO manual:
  python publisher.py
  python publisher.py --test        (simula sin publicar)
  python publisher.py --dia Lunes   (fuerza el post de ese dia)
"""

import json
import sys
import time
import requests
import argparse
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR  = Path(__file__).parent
LOG_DIR   = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

CONFIG_FILE = BASE_DIR / "config.json"
SCHEDULE_FILE = BASE_DIR / "schedule.json"
URLS_FILE   = BASE_DIR / "image_urls.json"
HISTORY_FILE = BASE_DIR / "history.json"

# Mapeo español <-> ingles para los dias
DIAS_ES = {
    "lunes": "Monday", "martes": "Tuesday", "miercoles": "Wednesday",
    "jueves": "Thursday", "viernes": "Friday", "sabado": "Saturday",
    "domingo": "Sunday",
    "Monday":"Monday","Tuesday":"Tuesday","Wednesday":"Wednesday",
    "Thursday":"Thursday","Friday":"Friday","Saturday":"Saturday","Sunday":"Sunday"
}

# ── Logger ───────────────────────────────────────────────────────────────────
class Logger:
    def __init__(self, date_str):
        self.log_file = LOG_DIR / f"{date_str}.log"
        self.entries = []

    def log(self, level, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        self.entries.append(line)
        print(line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def info(self, msg):  self.log("INFO", msg)
    def ok(self, msg):    self.log("OK  ", msg)
    def warn(self, msg):  self.log("WARN", msg)
    def error(self, msg): self.log("ERR ", msg)

# ── Cargar archivos ───────────────────────────────────────────────────────────
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ── Encontrar post de hoy ─────────────────────────────────────────────────────
def get_todays_post(schedule, force_day=None, force_time=False):
    today_en = force_day or datetime.now().strftime("%A")
    today_en = DIAS_ES.get(today_en.lower(), today_en)
    now = datetime.now()

    posts_today = [p for p in schedule["posts"]
                   if DIAS_ES.get(p["day_of_week"].lower(), p["day_of_week"]) == today_en
                   and p.get("activo", True)]

    if not posts_today:
        return None

    # Si hay varios para el mismo dia, rotamos semanalmente
    week_num = now.isocalendar()[1]
    idx = (week_num - 1) % len(posts_today)
    post = posts_today[idx]

    # Verificar que ya sea la hora programada (a menos que se fuerce con --dia)
    if not force_day and not force_time:
        hora_prog = post.get("hora", "00:00")
        try:
            h, m = map(int, hora_prog.split(":"))
            hora_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if now < hora_dt:
                return None  # Aun no es la hora
        except Exception:
            pass  # Si el formato falla, publicamos igualmente

    return post

# ── Comprobar si ya publicamos hoy ───────────────────────────────────────────
def already_published_today(post_id):
    if not HISTORY_FILE.exists():
        return False
    history = load_json(HISTORY_FILE)
    today_str = datetime.now().strftime("%Y-%m-%d")
    return any(
        h["date"].startswith(today_str) and h["post_id"] == post_id
        for h in history.get("published", [])
    )

def record_published(post_id, carrusel, result):
    history = {"published": []}
    if HISTORY_FILE.exists():
        history = load_json(HISTORY_FILE)

    history["published"].append({
        "date": datetime.now().isoformat(),
        "post_id": post_id,
        "carrusel": carrusel,
        "instagram_id": result.get("id", ""),
        "success": "id" in result
    })

    # Mantener solo los ultimos 90 dias
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    history["published"] = [h for h in history["published"] if h["date"] > cutoff]
    save_json(HISTORY_FILE, history)

# ── Verificar token ───────────────────────────────────────────────────────────
def check_token_expiry(config, logger):
    try:
        token = config["instagram_access_token"]
        r = requests.get(
            "https://graph.facebook.com/debug_token",
            params={"input_token": token, "access_token": token},
            timeout=10
        )
        data = r.json().get("data", {})
        expires_at = data.get("expires_at", 0)
        if expires_at:
            expires_dt = datetime.fromtimestamp(expires_at)
            days_left = (expires_dt - datetime.now()).days
            if days_left < 7:
                logger.warn(f"URGENTE: Tu token de Instagram expira en {days_left} dias!")
                logger.warn("Renuevalo en: https://developers.facebook.com/tools/explorer/")
            elif days_left < 20:
                logger.warn(f"Token expira en {days_left} dias. Planifica renovarlo pronto.")
            else:
                logger.info(f"Token valido: {days_left} dias restantes")
    except Exception as e:
        logger.warn(f"No se pudo verificar expiracion del token: {e}")

# ── Publicar carrusel en Instagram ───────────────────────────────────────────
def publish_carousel(config, image_urls, caption, logger, dry_run=False):
    ig_user_id = config["instagram_user_id"]
    access_token = config["instagram_access_token"]
    base_url = f"https://graph.facebook.com/v18.0/{ig_user_id}"

    if dry_run:
        logger.info("[TEST] Modo simulacion -- no se publica nada")
        logger.info(f"[TEST] Caption: {caption[:80]}...")
        for i, url in enumerate(image_urls, 1):
            logger.info(f"[TEST] Slide {i}: {url}")
        return {"id": "TEST_ID_123", "dry_run": True}

    # Paso 1: Crear contenedor para cada imagen
    logger.info(f"Creando contenedores para {len(image_urls)} slides...")
    container_ids = []

    for i, url in enumerate(image_urls, 1):
        if not url:
            logger.warn(f"Slide {i}: URL no disponible, saltando")
            continue

        success = False
        for attempt in range(1, 4):  # 3 intentos
            r = requests.post(
                f"{base_url}/media",
                data={
                    "image_url": url,
                    "is_carousel_item": "true",
                    "access_token": access_token
                },
                timeout=30
            )
            data = r.json()

            if "id" in data:
                container_ids.append(data["id"])
                logger.ok(f"Slide {i}/{len(image_urls)}: container {data['id']}")
                success = True
                break
            else:
                msg = data.get("error", {}).get("message", str(data))
                if attempt < 3:
                    logger.warn(f"Slide {i}: intento {attempt} fallido -- {msg} -- reintentando en 5s...")
                    time.sleep(5)
                else:
                    logger.error(f"Slide {i}: error tras 3 intentos -- {msg}")

        if not success:
            time.sleep(2)
        else:
            time.sleep(1)  # Rate limit

    if not container_ids:
        raise Exception("No se pudo crear ningun container de imagen")

    if len(container_ids) < 2:
        raise Exception(f"Instagram requiere minimo 2 slides para carrusel. Solo {len(container_ids)} OK.")

    # Paso 2: Crear contenedor del carrusel
    logger.info(f"Creando carrusel con {len(container_ids)} slides...")
    r = requests.post(
        f"{base_url}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(container_ids),
            "caption": caption,
            "access_token": access_token
        },
        timeout=30
    )
    carousel_data = r.json()

    if "id" not in carousel_data:
        msg = carousel_data.get("error", {}).get("message", str(carousel_data))
        raise Exception(f"Error creando carrusel: {msg}")

    carousel_id = carousel_data["id"]
    logger.ok(f"Carrusel creado: {carousel_id}")

    # Paso 3: Publicar
    logger.info("Publicando en Instagram...")
    time.sleep(2)  # Espera recomendada por Meta antes de publicar

    r = requests.post(
        f"{base_url}/media_publish",
        data={
            "creation_id": carousel_id,
            "access_token": access_token
        },
        timeout=30
    )
    result = r.json()

    if "id" in result:
        logger.ok(f"Publicado con exito! ID: {result['id']}")
    else:
        msg = result.get("error", {}).get("message", str(result))
        raise Exception(f"Error publicando: {msg}")

    return result

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="RivalFit Instagram Publisher")
    parser.add_argument("--test",       action="store_true", help="Simula sin publicar")
    parser.add_argument("--dia",        type=str, default=None, help="Forzar dia (ej: Monday, Lunes)")
    parser.add_argument("--force-time", action="store_true", help="Ignorar hora programada y publicar ahora")
    args = parser.parse_args()

    today_str = datetime.now().strftime("%Y-%m-%d")
    logger = Logger(today_str)

    logger.info(f"=== RivalFit Instagram Publisher ===")
    logger.info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.test:
        logger.info("MODO TEST (no publicara nada real)")
    if args.dia:
        logger.info(f"Dia forzado: {args.dia}")

    # Verificar archivos necesarios
    for f in [CONFIG_FILE, SCHEDULE_FILE, URLS_FILE]:
        if not f.exists():
            logger.error(f"Archivo no encontrado: {f}")
            logger.error("Ejecuta primero: python setup.py")
            sys.exit(1)

    # Cargar datos
    config   = load_json(CONFIG_FILE)
    schedule = load_json(SCHEDULE_FILE)
    urls_db  = load_json(URLS_FILE)

    # Verificar token
    check_token_expiry(config, logger)

    # Encontrar post de hoy
    force_time = getattr(args, 'force_time', False)
    post = get_todays_post(schedule, force_day=args.dia, force_time=force_time)

    if not post:
        day_name = args.dia or datetime.now().strftime("%A")
        now_str  = datetime.now().strftime("%H:%M")
        logger.info(f"No hay post programado para hoy ({day_name}) a las {now_str}. Nada que hacer.")
        sys.exit(0)

    logger.info(f"Post programado: {post['id']} -- {post['titulo']}")
    logger.info(f"Carrusel: {post['carrusel']}")

    # Comprobar si ya publicamos hoy este post
    if not args.test and not args.dia and already_published_today(post["id"]):
        logger.warn(f"El post '{post['id']}' ya fue publicado hoy. Saltando.")
        sys.exit(0)

    # Obtener URLs de las imagenes
    carrusel_key = post["carrusel"]
    image_urls = urls_db.get(carrusel_key, [])

    if not image_urls:
        logger.error(f"No hay URLs para el carrusel '{carrusel_key}'")
        logger.error("Ejecuta setup.py para subir las imagenes a imgbb")
        sys.exit(1)

    # Filtrar URLs None o vacias
    valid_urls = [u for u in image_urls if u]
    logger.info(f"Slides disponibles: {len(valid_urls)}/{len(image_urls)}")

    if len(valid_urls) < 2:
        logger.error(f"Instagram requiere minimo 2 slides. Solo hay {len(valid_urls)} validas.")
        sys.exit(1)

    # Construir caption
    caption_parts = [post.get("caption", "")]
    hashtags = post.get("hashtags", "").strip()
    if hashtags:
        caption_parts.append(hashtags)
    caption = "\n\n".join(p for p in caption_parts if p)

    # Publicar
    try:
        result = publish_carousel(
            config=config,
            image_urls=valid_urls,
            caption=caption,
            logger=logger,
            dry_run=args.test
        )

        if not args.test:
            record_published(post["id"], carrusel_key, result)

        logger.ok("=== PUBLICACION EXITOSA ===")
        logger.info(f"Log guardado en: {logger.log_file}")

    except Exception as e:
        logger.error(f"FALLO: {e}")
        logger.error("Revisa el log para mas detalles")
        sys.exit(1)

if __name__ == "__main__":
    main()
