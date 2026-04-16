# Cómo obtener las credenciales para la automatización

Tiempo estimado: **25-30 minutos** (solo una vez)

---

## PASO 1 — Convertir tu Instagram a cuenta Business o Creator

**Si ya tienes cuenta Business/Creator, salta al Paso 2.**

1. Abre Instagram en el móvil
2. Ve a tu perfil → ☰ menú → **Configuración y privacidad**
3. **Tipo de cuenta y herramientas** → **Cambiar a cuenta profesional**
4. Elige **Empresa** o **Creador de contenido**
5. Sigue los pasos y conecta (o crea) una **Página de Facebook**

> ⚠️ Esto es obligatorio. La API de Instagram solo funciona con cuentas Business/Creator.

---

## PASO 2 — Crear una app en Meta for Developers

1. Ve a **developers.facebook.com** (inicia sesión con tu Facebook)
2. Click en **Mis aplicaciones** → **Crear app**
3. Tipo de app: **Otro** → Siguiente
4. Nombre: `RivalFit Publisher` (el nombre es solo para ti)
5. Click **Crear app**

### Añadir el producto Instagram

6. En el panel de tu app, click en **Añadir producto**
7. Encuentra **Instagram** → click **Configurar**
8. Sigue el asistente de configuración

---

## PASO 3 — Obtener tu Instagram User ID

1. En el panel de Meta Developers, ve a **Herramientas** → **Explorador de la API Graph**
2. En el campo de la petición, escribe:
   ```
   me?fields=id,name,instagram_business_account
   ```
3. Click **Ejecutar** (el botón azul)
4. Busca en el resultado: `"instagram_business_account": {"id": "XXXXXXXXXX"}`
5. **Ese número es tu `instagram_user_id`** → cópialo en `config.json`

---

## PASO 4 — Obtener el Access Token

### Opción A — Token temporal (para probar, dura 1 hora)
1. En el Explorador de la API Graph → botón **Generar token de acceso**
2. Selecciona tu app y tu página de Facebook
3. Activa los permisos:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
4. Click **Generar token**
5. Copia el token → es tu `instagram_access_token` en config.json

### Opción B — Token de larga duración (dura 60 días, RECOMENDADO)
1. Con el token del paso anterior, abre esta URL en tu navegador:
   ```
   https://graph.facebook.com/v18.0/oauth/access_token?
   grant_type=fb_exchange_token&
   client_id=TU_APP_ID&
   client_secret=TU_APP_SECRET&
   fb_exchange_token=TOKEN_CORTO_DEL_PASO_ANTERIOR
   ```
   - `TU_APP_ID` y `TU_APP_SECRET` están en **Configuración** → **Básica** de tu app
2. El resultado contiene el `access_token` de larga duración
3. Cópialo en `config.json`

> ⏰ **Recuerda:** Este token dura 60 días. El sistema te avisará antes de que expire.
> Para renovarlo, repite la Opción B con el token actual.

---

## PASO 5 — Obtener la API Key de imgbb (imagen hosting)

1. Ve a **imgbb.com** y crea una cuenta gratuita (con tu email)
2. Una vez dentro, ve a: **imgbb.com/api**
3. Click en **Get API Key**
4. Copia la clave → es tu `imgbb_api_key` en config.json

> imgbb es completamente gratuito. Sube tus imágenes y las mantiene permanentemente.

---

## PASO 6 — Rellenar config.json

Abre el archivo `scheduler/config.json` y rellena:

```json
{
  "instagram_user_id": "1234567890",
  "instagram_access_token": "EAABwzLixnjYBO...",
  "imgbb_api_key": "abc123def456...",
  "hora_publicacion": "09:00"
}
```

---

## PASO 7 — Ejecutar el setup

```bash
cd marketing/instagram/scheduler
python setup.py
```

El script validará todo y configurará la automatización automáticamente.

---

## Renovar el token (cada 60 días)

Cuando el sistema te avise de que el token está a punto de expirar:

```bash
python refresh_token.py
```

O repite el **Paso 4, Opción B** manualmente.

---

## Solución de problemas

| Error | Solución |
|-------|---------|
| `Error de OAuthException` | Token expirado o permisos insuficientes. Regenera el token. |
| `Media posted cannot be a photo` | La URL de la imagen no es accesible públicamente. Re-ejecuta setup.py. |
| `No hay URLs para el carrusel` | Ejecuta `python setup.py` para subir las imágenes. |
| `Application does not have permission` | Activa los permisos de Instagram en tu app de Meta Developers. |
