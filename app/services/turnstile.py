import httpx

from app.config import TURNSTILE_SECRET_KEY

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verificar_turnstile(token: str, remote_ip: str | None) -> bool:
    if not token:
        return False

    datos = {"secret": TURNSTILE_SECRET_KEY, "response": token}
    if remote_ip:
        datos["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10) as cliente:
            respuesta = await cliente.post(VERIFY_URL, data=datos)
        return respuesta.json().get("success", False)
    except httpx.HTTPError:
        return False
