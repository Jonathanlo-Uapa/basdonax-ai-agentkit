"""El visto azul y el «escribiendo…», en el WhatsApp de la persona.

Chatwoot tiene su «escribiendo…», pero no lo pasa a WhatsApp: se ve solo
adentro de su bandeja. Para que la persona lo vea en su celular hay que
pedírselo a Meta directo, y eso pide dos datos de tu cuenta de WhatsApp
Business (los mismos que usa Chatwoot):

    WHATSAPP_TOKEN              el token de acceso
    WHATSAPP_PHONE_NUMBER_ID    el id del número

Es opcional: sin esos datos todo anda igual, solo que la persona no ve el
visto ni los puntitos. Y es cosmético: si Meta no contesta, la respuesta
sale igual. No cuenta como mensaje: Meta no lo cobra.

Los dos van en el MISMO pedido, que es lo que hace que se vea bien: primero
el visto y enseguida los puntitos, como alguien que abre el chat y se pone a
escribir. Los puntitos duran 25 segundos, o hasta que llega la respuesta.

Esto le suma al agente un segundo interlocutor además de Chatwoot, que es lo
que el diseño evitaba: es a propósito y es el único camino.
"""

from __future__ import annotations

import json
import logging
import re
import ssl
import urllib.request

registro = logging.getLogger("agente.whatsapp")

VERSION_DE_LA_API = "v21.0"
ESPERA = 10


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    """Meta no redirige esta API: seguirla sería mandar el token a otro lado."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError(f"Meta contestó con una redirección ({code}): no la sigo.")


_ABRIDOR = urllib.request.build_opener(
    _SinRedirecciones,
    urllib.request.HTTPSHandler(context=ssl.create_default_context()),
)


def wamid_del_evento(evento: dict) -> str:
    """El id que le puso WhatsApp al mensaje que llegó, o "".

    Chatwoot lo guarda en `source_id`. Es el único que Meta acepta para el
    visto: el id de Chatwoot no le sirve.
    """
    valor = evento.get("source_id") if isinstance(evento, dict) else ""
    valor = str(valor or "")
    # Solo los que entran se pueden marcar como leídos, y tienen esta forma.
    if valor.startswith("wamid.") and len(valor) < 200 and valor.isprintable():
        return valor
    return ""


def marcar_visto_y_escribiendo(wamid: str, token: str, numero_id: str) -> bool:
    """El visto en el mensaje y los puntitos. Devuelve True si salió.

    Nunca levanta un error: es cosmético y no puede voltear una respuesta.
    """
    if not (wamid and token and numero_id) or not str(numero_id).isdigit():
        return False

    cuerpo = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": wamid,
        "typing_indicator": {"type": "text"},
    }
    pedido = urllib.request.Request(
        f"https://graph.facebook.com/{VERSION_DE_LA_API}/{numero_id}/messages",
        data=json.dumps(cuerpo).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    pedido.add_unredirected_header("Authorization", f"Bearer {token}")
    try:
        with _ABRIDOR.open(pedido, timeout=ESPERA) as respuesta:
            respuesta.read()
        return True
    except Exception as e:
        registro.info("no salió el visto (%s…): %s", wamid[:16], type(e).__name__)
        return False


def enviar_botones(
    numero_destino: str,
    texto: str,
    botones: list[tuple[str, str]],
    token: str,
    numero_id: str,
) -> bool:
    """Envía un mensaje interactivo con hasta 3 botones de respuesta rápida a WhatsApp.

    botones: lista de tuplas (id, titulo). Cada título máximo 20 caracteres.
    Devuelve True si Meta aceptó el envío. Nunca levanta excepciones.
    """
    numero_destino = "".join(c for c in str(numero_destino or "") if c.isdigit())
    if not (numero_destino and texto and botones and token and numero_id) or not str(numero_id).isdigit():
        return False

    botones_payload = []
    for b_id, b_titulo in botones[:3]:
        botones_payload.append({
            "type": "reply",
            "reply": {
                "id": str(b_id)[:256],
                "title": str(b_titulo)[:20],
            },
        })

    cuerpo = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero_destino,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": str(texto)},
            "action": {"buttons": botones_payload},
        },
    }
    pedido = urllib.request.Request(
        f"https://graph.facebook.com/{VERSION_DE_LA_API}/{numero_id}/messages",
        data=json.dumps(cuerpo).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    pedido.add_unredirected_header("Authorization", f"Bearer {token}")
    try:
        with _ABRIDOR.open(pedido, timeout=ESPERA) as respuesta:
            respuesta.read()
        return True
    except Exception as e:
        registro.info("no salieron los botones a %s: %s", numero_destino, type(e).__name__)
        return False


def enviar_lista(
    numero_destino: str,
    texto: str,
    boton_lista: str,
    secciones: list[dict],
    token: str,
    numero_id: str,
) -> bool:
    """Envía un mensaje interactivo con lista desplegable a WhatsApp.

    boton_lista: texto del botón que abre el modal (máx 20 caracteres).
    secciones: lista de secciones [{'title': '...', 'rows': [{'id': '...', 'title': '...', 'description': '...'}]}]
    Devuelve True si Meta aceptó el envío. Nunca levanta excepciones.
    """
    numero_destino = "".join(c for c in str(numero_destino or "") if c.isdigit())
    if not (numero_destino and texto and secciones and token and numero_id) or not str(numero_id).isdigit():
        return False

    secciones_payload = []
    for s in secciones:
        filas = []
        for r in s.get("rows", []):
            fila_dict = {
                "id": str(r.get("id") or "")[:200],
                "title": str(r.get("title") or "")[:24],
            }
            desc = str(r.get("description") or "").strip()
            if desc:
                fila_dict["description"] = desc[:72]
            filas.append(fila_dict)
        secciones_payload.append({
            "title": str(s.get("title") or "Opciones")[:24],
            "rows": filas[:10],
        })

    cuerpo = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": numero_destino,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": str(texto)},
            "action": {
                "button": str(boton_lista or "Ver opciones")[:20],
                "sections": secciones_payload[:10],
            },
        },
    }
    pedido = urllib.request.Request(
        f"https://graph.facebook.com/{VERSION_DE_LA_API}/{numero_id}/messages",
        data=json.dumps(cuerpo).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    pedido.add_unredirected_header("Authorization", f"Bearer {token}")
    try:
        with _ABRIDOR.open(pedido, timeout=ESPERA) as respuesta:
            respuesta.read()
        return True
    except Exception as e:
        registro.info("no salió la lista a %s: %s", numero_destino, type(e).__name__)
        return False


def _limpiar_frases_prohibidas(texto: str) -> str:
    """Elimina frases feas o desalineadas como 'solo respóndeme con el número' o 'para orientarte mejor, dime:'."""
    if not isinstance(texto, str):
        return ""
    lineas = []
    for l in texto.splitlines():
        l_strip = l.strip()
        l_lower = l_strip.lower()
        if (
            "solo respóndeme con el número" in l_lower
            or "solo respondeme con el numero" in l_lower
            or "respóndeme con el número" in l_lower
            or "respondeme con el numero" in l_lower
            or "mándame el número" in l_lower
            or "mandame el numero" in l_lower
            or "solo responde con el número" in l_lower
            or "solo responde con el numero" in l_lower
            or "responde con el número" in l_lower
            or "responde con el numero" in l_lower
            or "para orientarte mejor, dime:" in l_lower
            or "para orientarte mejor:" in l_lower
        ):
            continue
        lineas.append(l)
    texto_res = "\n".join(lineas)
    texto_res = re.sub(
        r"(?i)para orientarte mejor,\s*dime:?",
        "Para conocer mejor tu caso y recomendarte el plan ideal para tu negocio:",
        texto_res,
    )
    texto_res = re.sub(r"\n{3,}", "\n\n", texto_res)
    return texto_res.strip()


def extraer_o_detectar_botones(texto: str) -> tuple[str, list[tuple[str, str]]]:
    """Extrae o detecta si el texto contiene opciones para botones interactivos de WhatsApp.

    Busca etiquetas explícitas [BOTONES: opt1 | opt2 | opt3], listas numeradas o
    detecta semánticamente los bloques de calificación clave (rol, sucursales,
    estaciones, dolor, acción demo).
    Limpia del texto las frases de relleno y las listas de opciones para que el
    mensaje de WhatsApp quede con prosa limpia y botones nativos.

    Devuelve (texto_limpio, lista_de_botones). Si no hay botones, devuelve (texto, []).
    Cada botón es una tupla (id, titulo), con título recortado a 20 caracteres (límite de Meta).
    """
    if not isinstance(texto, str) or not texto.strip():
        return "", []

    # 1. ¿Viene etiqueta explícita [BOTONES: ...]?
    match_tag = re.search(r"\[BOTONES?:\s*([^\]]+)\]", texto, re.IGNORECASE)
    if match_tag:
        raw_opts = match_tag.group(1).strip()
        texto_limpio = re.sub(r"\[BOTONES?:\s*[^\]]+\]", "", texto, flags=re.IGNORECASE).strip()
        partes = [p.strip() for p in raw_opts.split("|") if p.strip()]
        if len(partes) == 1 and "," in partes[0]:
            partes = [p.strip() for p in partes[0].split(",") if p.strip()]
        botones = [
            (f"btn_{i}", p[:20].strip())
            for i, p in enumerate(partes[:3], start=1)
            if p[:20].strip()
        ]
        if botones:
            texto_limpio = _limpiar_frases_prohibidas(texto_limpio)
            return texto_limpio, botones

    # 2. ¿Viene una lista de 2 o 3 opciones numeradas o con viñetas en el texto?
    patron_lineas = re.compile(
        r"^[ \t]*(?:[1-3]️⃣?|[\*•\-])[ \t\.\-\)]+([^\n\r]+)$",
        re.MULTILINE,
    )
    lineas = patron_lineas.findall(texto)
    if 2 <= len(lineas) <= 3:
        botones = [
            (f"btn_{i}", l.strip()[:20])
            for i, l in enumerate(lineas, start=1)
            if l.strip()[:20]
        ]
        texto_limpio = patron_lineas.sub("", texto)
        texto_limpio = _limpiar_frases_prohibidas(texto_limpio)
        return texto_limpio.strip(), botones

    # 3. Detección semántica de preguntas de calificación estándar
    texto_b = texto.lower()

    # Si es el saludo inicial o pregunta de identificación (Nombre / Car Wash),
    # NUNCA lleva botones: el cliente debe escribir su nombre y negocio en texto libre.
    if (
        "¿con quién tengo el gusto" in texto_b
        or "con quien tengo el gusto" in texto_b
        or "cómo se llama tu car wash" in texto_b
        or "como se llama tu car wash" in texto_b
        or "nombre de tu car wash" in texto_b
        or "¿cómo te llamas" in texto_b
        or "como te llamas" in texto_b
    ):
        return _limpiar_frases_prohibidas(texto), []

    # Bloque: Rol en el negocio
    if (
        "¿cuál es tu rol" in texto_b
        or "cual es tu rol" in texto_b
        or "¿qué rol" in texto_b
        or "que rol" in texto_b
        or "¿cuál es tu cargo" in texto_b
        or "cual es tu cargo" in texto_b
        or "tu rol en el negocio" in texto_b
        or "tu rol en el car wash" in texto_b
        or "eres el dueño" in texto_b
    ) and (
        "dueño" in texto_b or "administrador" in texto_b or "encargado" in texto_b
    ):
        botones = [
            ("rol_dueno", "👑 Dueño"),
            ("rol_admin", "💼 Administrador"),
            ("rol_encargado", "🔧 Encargado"),
        ]
        texto_limpio = _limpiar_frases_prohibidas(texto)
        return texto_limpio, botones

    # Bloque: Sucursales
    if (
        "cuántas sucursales" in texto_b
        or "cuantas sucursales" in texto_b
        or "cuántas sedes" in texto_b
        or "cuantas sedes" in texto_b
        or "cuántos locales" in texto_b
        or "cuantos locales" in texto_b
    ):
        botones = [
            ("suc_1", "1️⃣ 1 Sucursal"),
            ("suc_2_3", "🏢 2 a 3 Sedes"),
            ("suc_4_mas", "🌐 4 o más"),
        ]
        texto_limpio = _limpiar_frases_prohibidas(texto)
        return texto_limpio, botones

    # Bloque: Estaciones de lavado
    if (
        "cuántas estaciones" in texto_b
        or "cuantas estaciones" in texto_b
        or "puestos de lavado" in texto_b
        or "estaciones de lavado" in texto_b
    ):
        botones = [
            ("est_1_2", "🚗 1-2 Estaciones"),
            ("est_3_5", "🚙 3-5 Estaciones"),
            ("est_6_mas", "🚀 6 o más"),
        ]
        texto_limpio = _limpiar_frases_prohibidas(texto)
        return texto_limpio, botones

    # Bloque: Dolor principal (solo cuando formula una PREGUNTA explícita sobre el dolor o desafío)
    if (
        "¿cuál es el dolor" in texto_b
        or "cual es el dolor" in texto_b
        or "¿cuál es tu dolor" in texto_b
        or "cual es tu dolor" in texto_b
        or "¿cuál es tu mayor dolor" in texto_b
        or "cual es tu mayor dolor" in texto_b
        or "¿cuál es el mayor desafío" in texto_b
        or "cual es el mayor desafio" in texto_b
        or "dolor o desafío que más te cuesta" in texto_b
        or "dolor o desafio que mas te cuesta" in texto_b
        or "dolor que más te cuesta" in texto_b
        or "dolor que mas te cuesta" in texto_b
        or "¿qué es lo que más te cuesta" in texto_b
        or "que es lo que mas te cuesta" in texto_b
    ):
        botones = [
            ("dolor_caja", "💰 Cuadre de caja"),
            ("dolor_nomina", "👥 Comisiones"),
            ("dolor_lluvia", "☔ Días de lluvia"),
        ]
        texto_limpio = _limpiar_frases_prohibidas(texto)
        return texto_limpio, botones

    # Bloque: Cierre o propuesta de Demo / Walkthrough
    if (
        "¿te la agendo yo o" in texto_b
        or "te la agendo yo o" in texto_b
        or "cuál de esos te sirve" in texto_b
        or "cual de esos te sirve" in texto_b
        or "cuál te queda mejor" in texto_b
        or "cual te queda mejor" in texto_b
        or "videollamada de bienvenida" in texto_b
    ):
        botones = [
            ("accion_demo", "📅 Agendar Demo"),
            ("accion_trial", "🚀 Probar 7 Días"),
            ("accion_asesor", "👤 Hablar Asesor"),
        ]
        texto_limpio = _limpiar_frases_prohibidas(texto)
        return texto_limpio, botones

    # Sin botones detectados
    return _limpiar_frases_prohibidas(texto), []
