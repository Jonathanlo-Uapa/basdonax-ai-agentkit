"""Pruebas para el envío interactivo y notificaciones de WhatsApp Meta Cloud API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.canales import whatsapp_meta  # noqa: E402
from agente.canales.whatsapp_meta import (  # noqa: E402
    enviar_botones,
    enviar_lista,
    marcar_visto_y_escribiendo,
    wamid_del_evento,
)


class RespuestaFalsa:
    def __init__(self, datos=b"{\"success\": true}"):
        self._datos = datos

    def read(self):
        return self._datos

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class AbridorFalso:
    def __init__(self, error=None):
        self.error = error
        self.pedidos = []

    def open(self, pedido, timeout=None):
        self.pedidos.append(pedido)
        if self.error:
            raise self.error
        return RespuestaFalsa()


@pytest.fixture
def abridor_falso(monkeypatch):
    falso = AbridorFalso()
    monkeypatch.setattr(whatsapp_meta, "_ABRIDOR", falso)
    return falso


def test_wamid_del_evento():
    assert wamid_del_evento({"source_id": "wamid.HBgLMTgyOTMyOTIxMTQVAgASGBQz"}) == "wamid.HBgLMTgyOTMyOTIxMTQVAgASGBQz"
    assert wamid_del_evento({"source_id": "otro"}) == ""
    assert wamid_del_evento({}) == ""


def test_marcar_visto_y_escribiendo(abridor_falso):
    ok = marcar_visto_y_escribiendo("wamid.123", "token_test", "10839482910")
    assert ok is True
    assert len(abridor_falso.pedidos) == 1
    pedido = abridor_falso.pedidos[0]
    assert "10839482910/messages" in pedido.full_url
    cuerpo = json.loads(pedido.data.decode("utf-8"))
    assert cuerpo["status"] == "read"
    assert cuerpo["message_id"] == "wamid.123"


def test_enviar_botones_exitoso(abridor_falso):
    botones = [
        ("rol_dueno", "👑 Dueño"),
        ("rol_admin", "💼 Administrador"),
        ("rol_encargado", "🔧 Encargado"),
    ]
    ok = enviar_botones(
        numero_destino="+1 (829) 329-2114",
        texto="¿Cuál es tu rol en el Car Wash?",
        botones=botones,
        token="token_valido",
        numero_id="123456789",
    )
    assert ok is True
    assert len(abridor_falso.pedidos) == 1
    pedido = abridor_falso.pedidos[0]
    assert pedido.get_method() == "POST"
    assert "123456789/messages" in pedido.full_url
    assert pedido.get_header("Authorization") == "Bearer token_valido"

    cuerpo = json.loads(pedido.data.decode("utf-8"))
    assert cuerpo["messaging_product"] == "whatsapp"
    assert cuerpo["to"] == "18293292114"
    assert cuerpo["type"] == "interactive"
    inter = cuerpo["interactive"]
    assert inter["type"] == "button"
    assert inter["body"]["text"] == "¿Cuál es tu rol en el Car Wash?"
    assert len(inter["action"]["buttons"]) == 3
    assert inter["action"]["buttons"][0]["reply"]["title"] == "👑 Dueño"


def test_enviar_botones_con_datos_invalidos(abridor_falso):
    assert enviar_botones("", "texto", [("1", "btn")], "tok", "123") is False
    assert enviar_botones("18293292114", "", [("1", "btn")], "tok", "123") is False
    assert enviar_botones("18293292114", "texto", [], "tok", "123") is False
    assert enviar_botones("18293292114", "texto", [("1", "btn")], "", "123") is False
    assert enviar_botones("18293292114", "texto", [("1", "btn")], "tok", "no_digitos") is False
    assert len(abridor_falso.pedidos) == 0


def test_enviar_lista_exitosa(abridor_falso):
    secciones = [
        {
            "title": "Capacidad",
            "rows": [
                {"id": "est_1_2", "title": "1 a 2 Estaciones", "description": "Operación estándar"},
                {"id": "est_3_5", "title": "3 a 5 Estaciones", "description": "Alto volumen"},
            ],
        }
    ]
    ok = enviar_lista(
        numero_destino="18293292114",
        texto="Selecciona la cantidad de estaciones de lavado:",
        boton_lista="Elegir estaciones",
        secciones=secciones,
        token="token_valido",
        numero_id="123456789",
    )
    assert ok is True
    assert len(abridor_falso.pedidos) == 1
    pedido = abridor_falso.pedidos[0]
    cuerpo = json.loads(pedido.data.decode("utf-8"))
    assert cuerpo["type"] == "interactive"
    inter = cuerpo["interactive"]
    assert inter["type"] == "list"
    assert inter["action"]["button"] == "Elegir estaciones"
    assert len(inter["action"]["sections"]) == 1
    assert len(inter["action"]["sections"][0]["rows"]) == 2


def test_falla_de_red_no_levanta_excepcion(monkeypatch):
    monkeypatch.setattr(whatsapp_meta, "_ABRIDOR", AbridorFalso(error=ConnectionResetError("Red caída")))
    ok = enviar_botones(
        numero_destino="18293292114",
        texto="Texto",
        botones=[("1", "Btn")],
        token="tok",
        numero_id="123",
    )
    assert ok is False
