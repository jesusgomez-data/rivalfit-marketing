# -*- coding: utf-8 -*-
"""
RivalFit -- Diagnostico de credenciales Instagram
Identifica exactamente que IDs y permisos tienes disponibles.

USO:
  python diagnostico.py --token TU_TOKEN_NUEVO
  python diagnostico.py  (usa el token del config.json)
"""

import json
import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"

def get(url, params, timeout=10):
    r = requests.get(url, params=params, timeout=timeout)
    return r.json()

def post(url, data, timeout=15):
    r = requests.post(url, data=data, timeout=timeout)
    return r.json()

def sep(title=""):
    print(f"\n{'-'*60}")
    if title:
        print(f"  {title}")
    print()

def ok(msg):   print(f"  [OK]   {msg}")
def err(msg):  print(f"  [ERR]  {msg}")
def info(msg): print(f"  [INFO] {msg}")
def warn(msg): print(f"  [WARN] {msg}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", type=str, default=None,
                        help="Token a usar (si no se pone, usa el de config.json)")
    parser.add_argument("--app-id", type=str, default=None)
    parser.add_argument("--app-secret", type=str, default=None)
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  RIVALFIT -- DIAGNOSTICO DE INSTAGRAM API")
    print("="*60)

    # Cargar config
    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = json.load(f)

    token = args.token or config.get("instagram_access_token", "")
    if not token or "PON_AQUI" in token:
        err("No hay token. Usa: python diagnostico.py --token TU_TOKEN")
        sys.exit(1)

    # ── 1. Verificar token ────────────────────────────────────────────────────
    sep("1. ESTADO DEL TOKEN")
    debug = get("https://graph.facebook.com/debug_token",
                {"input_token": token, "access_token": token})
    data = debug.get("data", {})

    is_valid   = data.get("is_valid", False)
    expires_at = data.get("expires_at", 0)
    app_id     = data.get("app_id", "?")
    scopes     = data.get("scopes", [])

    print(f"  Valido:      {'SI' if is_valid else 'NO -- NECESITAS GENERAR NUEVO TOKEN'}")
    print(f"  App ID:      {app_id}")
    if expires_at:
        exp_dt = datetime.fromtimestamp(expires_at)
        days   = (exp_dt - datetime.now()).days
        print(f"  Expira:      {exp_dt.strftime('%Y-%m-%d')} ({days} dias restantes)")
        if days < 1:
            warn("Token expirado o expira hoy. Genera uno nuevo (ver instrucciones abajo).")
        elif days < 10:
            warn(f"Token expira pronto ({days} dias). Renuvalo.")
    else:
        print("  Expira:      Nunca (token de sistema)")

    print(f"\n  Permisos activos:")
    needed = {"instagram_basic", "instagram_content_publish", "pages_read_engagement"}
    for scope in scopes:
        mark = "[OK]" if scope in needed else "    "
        print(f"    {mark} {scope}")

    missing = needed - set(scopes)
    if missing:
        err(f"Permisos faltantes: {', '.join(missing)}")
        print("  >> En Meta Developers > API Explorer, activa estos permisos y regenera el token.")

    if not is_valid:
        sep("INSTRUCCIONES PARA NUEVO TOKEN")
        print("  1. Ve a: https://developers.facebook.com/tools/explorer/")
        print("  2. Selecciona tu App")
        print("  3. Activa los permisos:")
        print("       - instagram_basic")
        print("       - instagram_content_publish")
        print("       - pages_read_engagement")
        print("  4. Click 'Generar token de acceso'")
        print("  5. Ejecuta este diagnostico con el nuevo token:")
        print("     python diagnostico.py --token TU_NUEVO_TOKEN")
        print()
        sys.exit(0)

    # ── 2. Quien soy (Facebook User) ─────────────────────────────────────────
    sep("2. TU USUARIO DE FACEBOOK")
    me = get("https://graph.facebook.com/v18.0/me",
             {"fields": "id,name", "access_token": token})
    fb_user_id = me.get("id", "?")
    fb_name    = me.get("name", "?")
    print(f"  Nombre:    {fb_name}")
    print(f"  FB User ID: {fb_user_id}")

    # ── 3. Paginas de Facebook conectadas ─────────────────────────────────────
    sep("3. PAGINAS DE FACEBOOK CONECTADAS")
    pages_data = get("https://graph.facebook.com/v18.0/me/accounts",
                     {"access_token": token})
    pages = pages_data.get("data", [])

    if not pages:
        err("No se encontraron Paginas de Facebook.")
        err("Necesitas tener una Pagina de Facebook conectada a tu Instagram Business.")
        print("\n  >> Crea una Pagina en facebook.com/pages/create")
        print("  >> Conectala en Instagram: Configuracion > Cuenta > Pagina vinculada")
        sys.exit(0)

    ig_accounts = []

    for page in pages:
        page_id    = page.get("id")
        page_name  = page.get("name")
        page_token = page.get("access_token")
        print(f"  Pagina: {page_name} (ID: {page_id})")

        # Buscar cuenta de Instagram Business vinculada
        ig_data = get(
            f"https://graph.facebook.com/v18.0/{page_id}",
            {"fields": "instagram_business_account", "access_token": page_token or token}
        )
        ig_biz = ig_data.get("instagram_business_account")
        if ig_biz:
            ig_id = ig_biz.get("id")
            # Obtener detalles de la cuenta IG
            ig_details = get(
                f"https://graph.facebook.com/v18.0/{ig_id}",
                {"fields": "id,name,username,followers_count,media_count",
                 "access_token": page_token or token}
            )
            ig_username  = ig_details.get("username", "?")
            ig_followers = ig_details.get("followers_count", 0)
            ig_media     = ig_details.get("media_count", 0)
            print(f"    >> Instagram Business: @{ig_username} (ID: {ig_id})")
            print(f"       Seguidores: {ig_followers} | Posts: {ig_media}")
            ig_accounts.append({
                "ig_id": ig_id, "ig_username": ig_username,
                "page_id": page_id, "page_name": page_name,
                "page_token": page_token
            })
        else:
            warn(f"    La pagina '{page_name}' no tiene Instagram Business vinculado")

    if not ig_accounts:
        sep("NO HAY CUENTA INSTAGRAM BUSINESS")
        err("Ninguna pagina de Facebook tiene un Instagram Business vinculado.")
        print("\n  Pasos para solucionarlo:")
        print("  1. En Instagram: Perfil > Configuracion > Tipo de cuenta")
        print("     Cambia a 'Cuenta de empresa' o 'Creador de contenido'")
        print("  2. Durante el proceso, vincula tu Pagina de Facebook")
        print("  3. Vuelve a ejecutar este diagnostico")
        sys.exit(0)

    # ── 4. Resultado: el ID correcto ──────────────────────────────────────────
    sep("4. RESULTADO -- ID CORRECTO PARA CONFIG.JSON")

    if len(ig_accounts) == 1:
        acct = ig_accounts[0]
        current_id = config.get("instagram_user_id", "")
        print(f"  Tu Instagram Business Account ID es:")
        print(f"\n    {acct['ig_id']}   (@{acct['ig_username']})\n")

        if current_id == acct["ig_id"]:
            ok("El instagram_user_id en config.json ES CORRECTO")
        else:
            warn(f"El instagram_user_id actual en config.json es: {current_id}")
            warn(f"Debe ser: {acct['ig_id']}")
            print()

            # Actualizar automaticamente
            config["instagram_user_id"] = acct["ig_id"]
            config["instagram_access_token"] = token
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            ok(f"config.json actualizado automaticamente con el ID correcto!")

    else:
        print("  Tienes varias cuentas de Instagram Business:")
        for i, acct in enumerate(ig_accounts):
            print(f"  [{i+1}] @{acct['ig_username']} -- ID: {acct['ig_id']} (via pagina '{acct['page_name']}')")
        print(f"\n  Pon el ID que corresponda en config.json -> instagram_user_id")

    # ── 5. Convertir a token de larga duracion ────────────────────────────────
    if args.app_id and args.app_secret:
        sep("5. CONVIRTIENDO A TOKEN DE 60 DIAS")
        r = get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": args.app_id,
                "client_secret": args.app_secret,
                "fb_exchange_token": token
            }
        )
        if "access_token" in r:
            long_token = r["access_token"]
            expires_in = r.get("expires_in", 5184000)
            config["instagram_access_token"] = long_token
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            ok(f"Token de {expires_in // 86400} dias guardado en config.json")
        else:
            err(f"Error convirtiendo token: {r}")
    elif is_valid and expires_at and (datetime.fromtimestamp(expires_at) - datetime.now()).days < 60:
        sep("5. CONVERTIR A TOKEN DE 60 DIAS (recomendado)")
        print("  Para convertir este token a uno de 60 dias necesitas:")
        print("  Tu App ID y App Secret (en developers.facebook.com > tu app > Configuracion > Basica)")
        print()
        print("  Ejecuta:")
        print("  python diagnostico.py --token TU_TOKEN --app-id TU_APP_ID --app-secret TU_APP_SECRET")

    # ── 6. Resumen final ──────────────────────────────────────────────────────
    sep("RESUMEN")
    if is_valid and ig_accounts:
        ok("Token valido")
        ok(f"Instagram Business ID encontrado: {ig_accounts[0]['ig_id']}")
        if not missing:
            ok("Todos los permisos correctos")
            print()
            print("  Ejecuta ahora:")
            print("  python setup.py    (para subir imagenes y configurar Task Scheduler)")
            print("  python publisher.py --test   (para probar sin publicar)")
        else:
            err(f"Faltan permisos: {', '.join(missing)}")
            print("  Regenera el token con los permisos correctos y vuelve a ejecutar.")
    print()

if __name__ == "__main__":
    main()
