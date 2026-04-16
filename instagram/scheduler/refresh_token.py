# -*- coding: utf-8 -*-
"""
RivalFit -- Renovador de Access Token
Renueva automaticamente el token de Instagram antes de que expire (60 dias).

USO:
  python refresh_token.py
"""

import json
import requests
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"

def main():
    print("\n=== RivalFit -- Renovar Token de Instagram ===\n")

    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = json.load(f)

    token = config.get("instagram_access_token", "")
    if not token or "PON_AQUI" in token:
        print("[ERROR] No hay token configurado en config.json")
        sys.exit(1)

    # Verificar estado actual
    r = requests.get(
        "https://graph.facebook.com/debug_token",
        params={"input_token": token, "access_token": token},
        timeout=10
    )
    debug = r.json().get("data", {})
    expires_at = debug.get("expires_at", 0)
    is_valid   = debug.get("is_valid", False)

    if expires_at:
        expires_dt = datetime.fromtimestamp(expires_at)
        days_left  = (expires_dt - datetime.now()).days
        print(f"  Token actual: {'VALIDO' if is_valid else 'INVALIDO'}")
        print(f"  Expira: {expires_dt.strftime('%Y-%m-%d')} ({days_left} dias)")

    if not is_valid:
        print("\n[ERROR] El token ya no es valido. Debes generar uno nuevo manualmente.")
        print("  Consulta: COMO_OBTENER_CREDENCIALES.md -> Paso 4")
        sys.exit(1)

    # Renovar usando el endpoint de refresh de tokens largos
    print("\n  Renovando token...")
    r = requests.get(
        "https://graph.facebook.com/v18.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "fb_exchange_token": token,
            "access_token": token
        },
        timeout=15
    )
    result = r.json()

    if "access_token" in result:
        new_token = result["access_token"]
        expires_in = result.get("expires_in", 5184000)
        new_days = expires_in // 86400

        # Guardar nuevo token
        config["instagram_access_token"] = new_token
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"  [OK] Token renovado correctamente!")
        print(f"  [OK] Nuevo token valido por {new_days} dias")
        print(f"  [OK] Guardado en config.json")
    else:
        msg = result.get("error", {}).get("message", str(result))
        print(f"  [ERROR] No se pudo renovar: {msg}")
        print("  Genera un nuevo token manualmente: COMO_OBTENER_CREDENCIALES.md")
        sys.exit(1)

    print()

if __name__ == "__main__":
    main()
