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
    extraer_o_detectar_botones,
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


def test_extraer_o_detectar_botones_con_tag():
    texto = "Para conocer mejor tu caso:\n¿Cuál es tu rol?\n[BOTONES: 👑 Dueño | 💼 Administrador | 🔧 Encargado]"
    limpio, botones = extraer_o_detectar_botones(texto)
    assert "[BOTONES" not in limpio
    assert "¿Cuál es tu rol?" in limpio
    assert len(botones) == 3
    assert botones[0] == ("btn_1", "👑 Dueño")
    assert botones[1] == ("btn_2", "💼 Administrador")
    assert botones[2] == ("btn_3", "🔧 Encargado")


def test_extraer_o_detectar_botones_limpia_numeros_y_frases_prohibidas():
    texto = (
        "Para orientarte mejor, dime:\n"
        "¿Cuál es tu rol en el negocio?\n"
        "1️⃣ Dueño\n"
        "2️⃣ Administrador\n"
        "3️⃣ Encargado\n"
        "Solo respóndeme con el número 👌"
    )
    limpio, botones = extraer_o_detectar_botones(texto)
    assert "Solo respóndeme con el número" not in limpio
    assert "Para orientarte mejor" not in limpio
    assert "1️⃣" not in limpio
    assert len(botones) == 3
    assert botones[0] == ("btn_1", "Dueño")
    assert botones[1] == ("btn_2", "Administrador")
    assert botones[2] == ("btn_3", "Encargado")


def test_extraer_o_detectar_botones_semantica_sucursales():
    texto = "¿Cuántas sucursales de Car Wash operas actualmente?"
    limpio, botones = extraer_o_detectar_botones(texto)
    assert limpio == texto
    assert len(botones) == 3
    assert botones[0][1] == "1️⃣ 1 Sucursal"
    assert botones[1][1] == "🏢 2 a 3 Sedes"
    assert botones[2][1] == "🌐 4 o más"


def test_extraer_o_detectar_botones_semantica_estaciones():
    texto = "¿Cuántas estaciones de lavado operativas manejas?"
    limpio, botones = extraer_o_detectar_botones(texto)
    assert limpio == texto
    assert len(botones) == 3
    assert botones[0][1] == "🚗 1-2 Estaciones"
    assert botones[1][1] == "🚙 3-5 Estaciones"
    assert botones[2][1] == "🚀 6 o más"


def test_extraer_o_detectar_botones_semantica_dolor():
    texto = "¿Cuál es el dolor o desafío que más te cuesta hoy en caja o comisiones?"
    limpio, botones = extraer_o_detectar_botones(texto)
    assert len(botones) == 3
    assert botones[0][1] == "💰 Cuadre de caja"
    assert botones[1][1] == "👥 Comisiones"
    assert botones[2][1] == "☔ Días de lluvia"


def test_extraer_o_detectar_botones_sin_botones():
    texto = "¡Hola! Con mucho gusto te atiendo. ¿Con quién tengo el gusto?"
    limpio, botones = extraer_o_detectar_botones(texto)
    assert limpio == texto
    assert botones == []


def test_saludo_inicial_con_pitch_nunca_produce_botones():
    texto = (
        "¡Saludos! Te habla Carlos de LavaPass 🇩🇴. Somos la plataforma #1 para Car Washes en República Dominicana.\n\n"
        "Te ayudamos a blindar tu negocio con membresías mensuales (facturas fijo el día 1, llueva o no ☔), "
        "Cierre de Caja a Ciegas (cero fugas de gaveta) y liquidación de comisiones de lavadores en 10 segundos.\n\n"
        "Para conocer mejor tu caso y recomendarte el plan ideal para tu negocio, te haré unas breves preguntas sobre tu operación:\n"
        "Primero: **¿con quién tengo el gusto y cómo se llama tu Car Wash?** 🚗"
    )
    limpio, botones = extraer_o_detectar_botones(texto)
    assert botones == [], "El saludo inicial de identificación NUNCA debe incluir botones"
    assert "¿con quién tengo el gusto" in limpio


