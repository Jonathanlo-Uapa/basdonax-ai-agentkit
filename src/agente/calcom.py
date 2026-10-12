"""Las demos con Adonis: los horarios libres y la reserva, en Cal.com.

Cal.com es el dueño de la agenda. Los días y horas en que se puede agendar
(lunes de 18 a 20, martes nada, de miércoles a viernes de 18 a 21, sábados y
domingos de 9 a 21) se configuran allá, en el horario del tipo de evento, y
acá no están escritos en ningún lado: si mañana cambian, se cambian en Cal.com
y el agente ni se entera. Lo único que hace este módulo es preguntar y pedir.

Y Cal.com es también el que decide si un horario se puede tomar: si dos
personas piden el mismo, la segunda reserva la rechaza él. Por eso no hace
falta un candado de base de datos acá: el candado es Cal.com.

Son dos pedidos, con `urllib` de la biblioteca estándar como el resto del
proyecto:

    GET  /v2/slots      los horarios libres de un tipo de evento
    POST /v2/bookings   la reserva

Cada uno pide su propia versión en la cabecera `cal-api-version`. Sin ella,
Cal.com contesta con una versión vieja del mismo pedido y otra forma de datos.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

# En Windows o redes donde el proveedor tiene IPv6 sin salida activa a Cloudflare,
# resolver IPv6 primero provoca que la conexión TLS se reinicie ([WinError 10054]).
# Priorizar AF_INET (IPv4) asegura conexión inmediata sin tocar librerías externas.
_getaddrinfo_original = socket.getaddrinfo


def _getaddrinfo_ipv4_primero(host, port, family=0, type=0, proto=0, flags=0):
    respuestas = _getaddrinfo_original(host, port, family, type, proto, flags)
    return sorted(respuestas, key=lambda r: 0 if r[0] == socket.AF_INET else 1)


socket.getaddrinfo = _getaddrinfo_ipv4_primero

ZONA = "America/Santo_Domingo"

# La hora de República Dominicana como un desfase fijo y no con zoneinfo, a
# propósito: allá no hay horario de verano (es UTC-4 todo el año), y en
# Windows zoneinfo no trae los husos horarios sin instalar el paquete tzdata.
HORA_RD = timezone(timedelta(hours=-4), "RD")

VERSION_HORARIOS = "2024-09-04"
VERSION_RESERVAS = "2026-02-25"
VERSION_CONSULTA_RESERVAS = "2024-08-13"

# Si Cal.com no contesta en este tiempo, cortamos: la persona está esperando.
ESPERA = 15


class ErrorDeCalcom(Exception):
    """Cal.com dijo que no, o no contestó. El mensaje dice qué pasó."""

    def __init__(self, mensaje: str, codigo: int = 0) -> None:
        super().__init__(mensaje)
        self.codigo = codigo


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    """Una redirección se corta: urllib le reenviaría la clave a otro servidor."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ErrorDeCalcom(
            f"Cal.com contestó con una redirección ({code}). No la sigo, para no "
            "mandarle la clave a otro lado: revisá CALCOM_URL."
        )


_ABRIDOR = urllib.request.build_opener(_SinRedirecciones)


class Calcom:
    """La agenda de las demos."""

    def __init__(self, url: str, clave: str, tipo_de_evento: str | int) -> None:
        if not clave or not str(tipo_de_evento or "").isdigit():
            raise ValueError(
                "Faltan datos de Cal.com. Abrí el .env y completá "
                "CALCOM_API_KEY y CALCOM_EVENT_TYPE_ID."
            )
        self.url = (url or "https://api.cal.com").rstrip("/")
        self.clave = clave
        self.tipo_de_evento = int(tipo_de_evento)

    def horarios(self, desde: date, hasta: date) -> list[datetime]:
        """Los comienzos libres entre esos dos días (incluidos), en hora de RD.

        Cal.com pide el rango en UTC. El día en RD empieza a las 04:00 UTC, así
        que se corre el rango para no perder la mañana ni sumar la del día
        siguiente.
        """
        inicio = datetime(desde.year, desde.month, desde.day, tzinfo=HORA_RD)
        fin = datetime(hasta.year, hasta.month, hasta.day, tzinfo=HORA_RD) + timedelta(days=1)
        parametros = {
            "eventTypeId": self.tipo_de_evento,
            "start": _utc(inicio),
            "end": _utc(fin - timedelta(seconds=1)),
            "timeZone": ZONA,
        }
        datos = self._pedir("GET", f"/v2/slots?{urllib.parse.urlencode(parametros)}", VERSION_HORARIOS)

        comienzos: list[datetime] = []
        por_dia = datos.get("data") if isinstance(datos, dict) else None
        for lista in (por_dia or {}).values() if isinstance(por_dia, dict) else ():
            for horario in lista if isinstance(lista, list) else ():
                # Según la versión, cada horario viene como texto o como
                # {"start": ...}: se aceptan los dos.
                crudo = horario.get("start") if isinstance(horario, dict) else horario
                momento = _leer_fecha(crudo)
                if momento is not None and inicio <= momento < fin:
                    comienzos.append(momento)
        return sorted(set(comienzos))

    def reservar(
        self,
        comienzo: datetime,
        nombre: str,
        telefono: str,
        metadatos: dict[str, str] | None = None,
    ) -> dict:
        """Reserva ese horario. Devuelve {"uid", "comienzo", "enlace"}.

        Sin email, a propósito: por WhatsApp casi nadie lo da, y Cal.com lo
        acepta si el tipo de evento tiene el teléfono como dato obligatorio y
        el email opcional (ver el README). El teléfono va en formato
        internacional, que es como lo guarda Chatwoot.
        """
        cuerpo = {
            "start": _utc(comienzo),
            "eventTypeId": self.tipo_de_evento,
            "attendee": {
                "name": nombre,
                "timeZone": ZONA,
                "phoneNumber": telefono,
                "language": "es",
            },
            # Cal.com pide textos de hasta 500 caracteres, y 50 claves como mucho.
            "metadata": {
                str(k)[:40]: str(v)[:500] for k, v in list((metadatos or {}).items())[:50]
            },
        }
        datos = self._pedir("POST", "/v2/bookings", VERSION_RESERVAS, cuerpo)
        reserva = datos.get("data") if isinstance(datos, dict) else None
        if isinstance(reserva, list):  # los eventos recurrentes vuelven en lista
            reserva = reserva[0] if reserva else None
        if not isinstance(reserva, dict) or not reserva.get("uid"):
            raise ErrorDeCalcom(f"Cal.com no devolvió la reserva: {str(datos)[:300]}")

        return {
            "uid": str(reserva["uid"]),
            "comienzo": _leer_fecha(reserva.get("start")) or comienzo.astimezone(HORA_RD),
            "enlace": str(reserva.get("meetingUrl") or reserva.get("location") or ""),
        }

    def consultar_reserva(
        self,
        uid: str = "",
        email: str = "",
        telefono: str = "",
    ) -> dict | None:
        """Busca una reserva existente en Cal.com por su UID, correo o teléfono.

        Devuelve un diccionario con los datos normalizados de la reserva o None.
        """
        uid = str(uid or "").strip()
        if uid:
            try:
                datos = self._pedir("GET", f"/v2/bookings/{uid}", VERSION_CONSULTA_RESERVAS)
                reserva = datos.get("data") if isinstance(datos, dict) else None
                if isinstance(reserva, dict) and reserva.get("uid"):
                    return self._armar_ficha_reserva(reserva)
            except Exception:
                pass

        email_buscado = str(email or "").strip().lower()
        tel_limpio = "".join(c for c in str(telefono or "") if c.isdigit())
        if not email_buscado and not tel_limpio:
            return None

        try:
            datos = self._pedir("GET", "/v2/bookings", VERSION_CONSULTA_RESERVAS)
            lista = datos.get("data") if isinstance(datos, dict) else []
            if not isinstance(lista, list):
                lista = []
        except Exception:
            return None

        for b in lista:
            if not isinstance(b, dict):
                continue
            if str(b.get("status") or "").lower() == "cancelled":
                continue

            attendees = b.get("attendees") or []
            for att in attendees if isinstance(attendees, list) else []:
                if not isinstance(att, dict):
                    continue
                att_email = str(att.get("email") or "").strip().lower()
                att_tel = "".join(c for c in str(att.get("phoneNumber") or "") if c.isdigit())

                coincide_email = bool(email_buscado and email_buscado in att_email)
                coincide_tel = False
                if tel_limpio and att_tel:
                    min_len = min(len(tel_limpio), len(att_tel))
                    if min_len >= 7:
                        coincide_tel = tel_limpio.endswith(att_tel[-7:]) or att_tel.endswith(tel_limpio[-7:])

                if coincide_email or coincide_tel:
                    return self._armar_ficha_reserva(b)

        return None

    def _armar_ficha_reserva(self, reserva: dict) -> dict:
        attendees = reserva.get("attendees") or [{}]
        primer_att = attendees[0] if attendees else {}
        return {
            "uid": str(reserva.get("uid") or ""),
            "comienzo": _leer_fecha(reserva.get("start")),
            "fin": _leer_fecha(reserva.get("end")),
            "enlace": str(reserva.get("meetingUrl") or reserva.get("location") or ""),
            "titulo": str(reserva.get("title") or ""),
            "asistente": str(primer_att.get("name") or ""),
            "email": str(primer_att.get("email") or ""),
            "telefono": str(primer_att.get("phoneNumber") or ""),
            "estado": str(reserva.get("status") or ""),
        }

    def _pedir(self, metodo: str, camino: str, version: str, datos: dict | None = None) -> dict:
        pedido = urllib.request.Request(
            self.url + camino,
            data=json.dumps(datos).encode("utf-8") if datos is not None else None,
            method=metodo,
            headers={
                "Authorization": f"Bearer {self.clave}",
                "cal-api-version": version,
                "Content-Type": "application/json",
                # Sin un nombre propio, algunos cortafuegos frenan a urllib.
                "User-Agent": "basdonax-agentkit",
            },
        )
        try:
            with _ABRIDOR.open(pedido, timeout=ESPERA) as respuesta:
                cuerpo = respuesta.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            # El cuerpo es lo único que dice qué pasó (clave vencida, tipo de
            # evento equivocado, horario ocupado).
            detalle = e.read().decode("utf-8", "replace")[:300]
            raise ErrorDeCalcom(
                f"Cal.com devolvió {e.code} en {metodo} {camino.split('?')[0]}: {detalle}",
                e.code,
            ) from None
        except urllib.error.URLError as e:
            raise ErrorDeCalcom(f"No se pudo hablar con Cal.com: {e.reason}") from None
        return json.loads(cuerpo) if cuerpo else {}


# -- Ayudantes ----------------------------------------------------------------


def _utc(momento: datetime) -> str:
    """Como lo pide Cal.com: en UTC, con Z y sin milisegundos."""
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _leer_fecha(crudo) -> datetime | None:
    """Una fecha ISO de Cal.com, pasada a hora de RD. None si no se entiende."""
    if not isinstance(crudo, str) or not crudo:
        return None
    try:
        momento = datetime.fromisoformat(crudo.replace("Z", "+00:00"))
    except ValueError:
        return None
    if momento.tzinfo is None:
        return None
    return momento.astimezone(HORA_RD)


def ahora_en_rd() -> datetime:
    """La hora de ahora en RD. Aparte, para que los tests la puedan fijar."""
    return datetime.now(HORA_RD)
