"""Pruebas del cliente de Cal.com. No salen a internet: el abridor es de mentira.

Lo que se prueba es lo que armamos nosotros (el rango en UTC, la reserva sin
email, las cabeceras) y cómo se lee lo que vuelve, que cambia de forma según
la versión del pedido.

    pytest tests/test_calcom.py
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.parse
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente import calcom  # noqa: E402
from agente.calcom import HORA_RD, Calcom, ErrorDeCalcom, _SinRedirecciones  # noqa: E402
from agente.config import ErrorDeConfiguracion, datos_de_calcom  # noqa: E402


class Respuesta:
    def __init__(self, datos):
        self._cuerpo = json.dumps(datos).encode("utf-8")

    def read(self):
        return self._cuerpo

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class AbridorFalso:
    """Anota cada pedido y contesta lo que se le diga (o levanta el error)."""

    def __init__(self, datos=None, error=None):
        self.datos = datos if datos is not None else {"status": "success", "data": {}}
        self.error = error
        self.pedidos: list = []

    def open(self, pedido, timeout=None):
        self.pedidos.append(pedido)
        if self.error is not None:
            raise self.error
        return Respuesta(self.datos)


def agenda(monkeypatch, **opciones) -> tuple[Calcom, AbridorFalso]:
    abridor = AbridorFalso(**opciones)
    monkeypatch.setattr(calcom, "_ABRIDOR", abridor)
    return Calcom("https://api.cal.com/", "cal_clave_falsa", "123"), abridor


def cabecera(pedido, nombre: str) -> str:
    # urllib guarda los nombres de las cabeceras con la primera letra en mayúscula.
    return dict(pedido.header_items())[nombre.capitalize()]


def test_calcom_pide_los_horarios_del_dia_de_rd_en_utc(monkeypatch):
    a, abridor = agenda(monkeypatch)

    a.horarios(date(2026, 10, 10), date(2026, 10, 10))

    pedido = abridor.pedidos[0]
    partes = urllib.parse.urlsplit(pedido.full_url)
    consulta = dict(urllib.parse.parse_qsl(partes.query))
    assert partes.path == "/v2/slots", "la barra final de la URL no se duplica"
    assert consulta["eventTypeId"] == "123"
    # El día en RD (UTC-4) va de las 04:00 UTC a las 03:59:59 UTC del siguiente.
    assert consulta["start"] == "2026-10-10T04:00:00Z"
    assert consulta["end"] == "2026-10-11T03:59:59Z"
    assert consulta["timeZone"] == "America/Santo_Domingo"
    assert cabecera(pedido, "cal-api-version") == "2024-09-04"
    assert cabecera(pedido, "authorization") == "Bearer cal_clave_falsa"
    assert pedido.get_method() == "GET"


def test_calcom_entiende_los_horarios_como_texto_o_como_objeto(monkeypatch):
    a, _ = agenda(
        monkeypatch,
        datos={
            "status": "success",
            "data": {
                "2026-10-10": [
                    {"start": "2026-10-10T09:15:00.000-04:00"},
                    "2026-10-10T13:00:00Z",  # 09:00 en RD
                    {"start": "2026-10-10T09:15:00.000-04:00"},  # repetido
                    {"start": "no es una fecha"},
                    {"start": "2026-10-10T09:30:00"},  # sin zona: no se adivina
                    42,
                ],
                "2026-10-12": [{"start": "2026-10-12T18:00:00.000-04:00"}],  # fuera del rango
            },
        },
    )

    horarios = a.horarios(date(2026, 10, 10), date(2026, 10, 10))

    assert horarios == [
        datetime(2026, 10, 10, 9, 0, tzinfo=HORA_RD),
        datetime(2026, 10, 10, 9, 15, tzinfo=HORA_RD),
    ]
    assert all(h.utcoffset() == HORA_RD.utcoffset(None) for h in horarios)


def test_calcom_con_una_respuesta_rara_no_hay_horarios(monkeypatch):
    for datos in ({"data": []}, {"data": {"2026-10-10": "x"}}, ["no", "es", "objeto"], {}):
        a, _ = agenda(monkeypatch, datos=datos)
        assert a.horarios(date(2026, 10, 10), date(2026, 10, 10)) == []


def test_calcom_reserva_en_utc_sin_email_y_con_el_telefono(monkeypatch):
    a, abridor = agenda(
        monkeypatch,
        datos={
            "status": "success",
            "data": {
                "uid": "reserva-1",
                "start": "2026-10-10T13:00:00.000Z",
                "meetingUrl": "https://meet.google.com/abc-defg-hij",
            },
        },
    )

    reserva = a.reservar(
        datetime(2026, 10, 10, 9, 0, tzinfo=HORA_RD),
        "Ana Pérez",
        "+18095551234",
        {"conversacion_chatwoot": "55", "x" * 60: "y" * 900},
    )

    pedido = abridor.pedidos[0]
    cuerpo = json.loads(pedido.data)
    assert pedido.get_method() == "POST"
    assert pedido.full_url == "https://api.cal.com/v2/bookings"
    assert cabecera(pedido, "cal-api-version") == "2026-02-25"
    assert cuerpo["start"] == "2026-10-10T13:00:00Z", "Cal.com pide UTC"
    assert cuerpo["eventTypeId"] == 123
    assert cuerpo["attendee"] == {
        "name": "Ana Pérez",
        "timeZone": "America/Santo_Domingo",
        "phoneNumber": "+18095551234",
        "language": "es",
    }
    assert "email" not in json.dumps(cuerpo["attendee"])
    assert all(len(k) <= 40 and len(v) <= 500 for k, v in cuerpo["metadata"].items())
    assert reserva == {
        "uid": "reserva-1",
        "comienzo": datetime(2026, 10, 10, 9, 0, tzinfo=HORA_RD),
        "enlace": "https://meet.google.com/abc-defg-hij",
    }


def test_calcom_sin_uid_no_hay_reserva(monkeypatch):
    a, _ = agenda(monkeypatch, datos={"status": "success", "data": {}})
    with pytest.raises(ErrorDeCalcom, match="no devolvió la reserva"):
        a.reservar(datetime(2026, 10, 10, 9, 0, tzinfo=HORA_RD), "Ana", "+18095551234")


def test_calcom_un_evento_recurrente_vuelve_en_lista(monkeypatch):
    a, _ = agenda(monkeypatch, datos={"data": [{"uid": "r-1", "start": "2026-10-10T13:00:00Z"}]})
    assert a.reservar(datetime(2026, 10, 10, 9, 0, tzinfo=HORA_RD), "Ana", "+1")["uid"] == "r-1"


def test_calcom_el_error_trae_lo_que_dijo_cal_com(monkeypatch):
    error = urllib.error.HTTPError(
        "https://api.cal.com/v2/bookings",
        400,
        "Bad Request",
        {},
        io.BytesIO(b'{"status":"error","error":{"message":"User either already has booking at this time or is not available"}}'),
    )
    a, _ = agenda(monkeypatch, error=error)

    with pytest.raises(ErrorDeCalcom) as falla:
        a.reservar(datetime(2026, 10, 10, 9, 0, tzinfo=HORA_RD), "Ana", "+18095551234")

    assert falla.value.codigo == 400
    assert "already has booking" in str(falla.value)
    assert "cal_clave_falsa" not in str(falla.value)


def test_calcom_sin_red_tambien_es_un_error_de_calcom(monkeypatch):
    a, _ = agenda(monkeypatch, error=urllib.error.URLError("sin conexión"))
    with pytest.raises(ErrorDeCalcom, match="No se pudo hablar con Cal.com"):
        a.horarios(date(2026, 10, 10), date(2026, 10, 10))


def test_calcom_no_sigue_redirecciones():
    """Seguirla le mandaría la clave a otro servidor."""
    with pytest.raises(ErrorDeCalcom, match="redirección"):
        _SinRedirecciones().redirect_request(None, None, 302, "Found", {}, "https://otro.com")


def test_calcom_sin_datos_avisa_que_faltan():
    with pytest.raises(ValueError, match="CALCOM_API_KEY"):
        Calcom("https://api.cal.com", "", "123")
    with pytest.raises(ValueError, match="CALCOM_EVENT_TYPE_ID"):
        Calcom("https://api.cal.com", "cal_x", "")


@pytest.mark.parametrize(
    "comienzo, afuera",
    [
        (datetime(2026, 10, 12, 9, 0, tzinfo=HORA_RD), False),    # lunes 9:00
        (datetime(2026, 10, 12, 20, 45, tzinfo=HORA_RD), False),  # lunes, termina 21:00
        (datetime(2026, 10, 12, 21, 0, tzinfo=HORA_RD), True),    # lunes 21:00: ya cerró
        (datetime(2026, 10, 13, 10, 0, tzinfo=HORA_RD), False),   # martes 10:00: abierto
        (datetime(2026, 10, 14, 20, 45, tzinfo=HORA_RD), False),  # miércoles, termina 21:00
        (datetime(2026, 10, 16, 8, 45, tzinfo=HORA_RD), True),    # viernes antes de las 9:00
        (datetime(2026, 10, 17, 9, 0, tzinfo=HORA_RD), False),    # sábado 9:00
        (datetime(2026, 10, 18, 13, 45, tzinfo=HORA_RD), True),   # domingo antes de las 14:00
        (datetime(2026, 10, 18, 17, 45, tzinfo=HORA_RD), False),  # domingo, termina 18:00
        (datetime(2026, 10, 18, 18, 0, tzinfo=HORA_RD), True),    # domingo 18:00: ya cerró
    ],
)
def test_calcom_probar_calcom_conoce_el_horario_acordado(comienzo, afuera):
    import importlib.util

    ruta = Path(__file__).resolve().parents[1] / "probar_calcom.py"
    especificacion = importlib.util.spec_from_file_location("probar_calcom", ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)

    assert modulo.fuera_del_horario(comienzo) is afuera


def test_calcom_el_tipo_de_evento_tiene_que_ser_un_numero(monkeypatch):
    monkeypatch.setenv("CALCOM_EVENT_TYPE_ID", "demo-15-min")
    with pytest.raises(ErrorDeConfiguracion, match="solo dígitos"):
        datos_de_calcom()

    monkeypatch.setenv("CALCOM_EVENT_TYPE_ID", "4567")
    monkeypatch.setenv("CALCOM_URL", "https://cal.ejemplo.com/")
    assert datos_de_calcom()["evento"] == "4567"
    assert datos_de_calcom()["url"] == "https://cal.ejemplo.com"
