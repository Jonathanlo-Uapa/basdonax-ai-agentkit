"""Inicializa las definiciones de atributos personalizados y las etiquetas en Chatwoot.

Crea los campos del CRM para la ficha del contacto y de la conversación,
así como las etiquetas del embudo de ventas y multi-tagging. Es seguro
re-ejecutarlo: si un atributo o etiqueta ya existe, lo respeta y continúa.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Raíz del proyecto
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from dotenv import load_dotenv

load_dotenv(RAIZ / ".env")

CHATWOOT_URL = (os.getenv("CHATWOOT_URL") or "").rstrip("/")
CHATWOOT_TOKEN = os.getenv("CHATWOOT_TOKEN") or ""
CHATWOOT_CUENTA_ID = os.getenv("CHATWOOT_CUENTA_ID") or "1"


def _api(metodo: str, camino: str, datos: dict | None = None) -> tuple[int, dict]:
    url = f"{CHATWOOT_URL}/api/v1/accounts/{CHATWOOT_CUENTA_ID}/{camino}"
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
    pedido = urllib.request.Request(
        url,
        data=cuerpo,
        method=metodo,
        headers={
            "Content-Type": "application/json",
            "api_access_token": CHATWOOT_TOKEN,
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw_error = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw_error)
        except Exception:
            parsed = {"error": raw_error}
        return e.code, parsed


# Definiciones de atributos: model 1 = Contact, 0 = Conversation
# attribute_display_type: text, number, list, checkbox, date, etc.
ATRIBUTOS_CONTACTO = [
    {
        "attribute_display_name": "Nombre del Car Wash",
        "attribute_key": "negocio_nombre",
        "attribute_display_type": "text",
        "attribute_model": 1,
        "attribute_description": "Nombre comercial del Car Wash",
    },
    {
        "attribute_display_name": "Cargo / Rol",
        "attribute_key": "cargo",
        "attribute_display_type": "text",
        "attribute_model": 1,
        "attribute_description": "Cargo de la persona (Dueño, Administrador, etc.)",
    },
    {
        "attribute_display_name": "Sucursales",
        "attribute_key": "sucursales_count",
        "attribute_display_type": "number",
        "attribute_model": 1,
        "attribute_description": "Cantidad de sucursales que opera",
    },
    {
        "attribute_display_name": "Estaciones de Lavado",
        "attribute_key": "estaciones_count",
        "attribute_display_type": "number",
        "attribute_model": 1,
        "attribute_description": "Cantidad total de bahías/estaciones",
    },
    {
        "attribute_display_name": "Dolor Principal",
        "attribute_key": "dolor_principal",
        "attribute_display_type": "text",
        "attribute_model": 1,
        "attribute_description": "Principal dolor operativo o financiero",
    },
    {
        "attribute_display_name": "Software Actual",
        "attribute_key": "software_actual",
        "attribute_display_type": "text",
        "attribute_model": 1,
        "attribute_description": "Herramienta o sistema que usa actualmente",
    },
    {
        "attribute_display_name": "Urgencia",
        "attribute_key": "urgencia",
        "attribute_display_type": "text",
        "attribute_model": 1,
        "attribute_description": "Nivel de urgencia para implementar",
    },
    {
        "attribute_display_name": "Lead Score",
        "attribute_key": "lead_score",
        "attribute_display_type": "number",
        "attribute_model": 1,
        "attribute_description": "Puntaje de calificación (0-100)",
    },
    {
        "attribute_display_name": "Etapa del Embudo",
        "attribute_key": "etapa_embudo",
        "attribute_display_type": "text",
        "attribute_model": 1,
        "attribute_description": "Etapa actual en el pipeline comercial",
    },
]

ATRIBUTOS_CONVERSACION = [
    {
        "attribute_display_name": "Lead Score",
        "attribute_key": "lead_score",
        "attribute_display_type": "number",
        "attribute_model": 0,
        "attribute_description": "Puntaje de calificación de la conversación",
    },
    {
        "attribute_display_name": "Etapa del Embudo",
        "attribute_key": "etapa_embudo",
        "attribute_display_type": "text",
        "attribute_model": 0,
        "attribute_description": "Etapa actual en el pipeline",
    },
    {
        "attribute_display_name": "Cal.com Booking UID",
        "attribute_key": "demo_uid",
        "attribute_display_type": "text",
        "attribute_model": 0,
        "attribute_description": "Identificador de la reserva en Cal.com",
    },
    {
        "attribute_display_name": "Cal.com Fecha/Hora Inicio",
        "attribute_key": "demo_inicio",
        "attribute_display_type": "text",
        "attribute_model": 0,
        "attribute_description": "Fecha y hora pactada para la demo",
    },
]

ETIQUETAS = [
    # Etapas del Embudo (progresivas)
    {
        "title": "1_lead_nuevo",
        "color": "#94a3b8",
        "description": "Lead recién ingresado al sistema",
        "show_on_sidebar": True,
    },
    {
        "title": "2_lead_diagnosticado",
        "color": "#60a5fa",
        "description": "Lead con diagnóstico preliminar",
        "show_on_sidebar": True,
    },
    {
        "title": "3_lead_calificado",
        "color": "#2563eb",
        "description": "Lead calificado para demo y prueba",
        "show_on_sidebar": True,
    },
    {
        "title": "4_demo_propuesta",
        "color": "#9333ea",
        "description": "Horarios de demo presentados",
        "show_on_sidebar": True,
    },
    {
        "title": "5_demo_agendada",
        "color": "#10b981",
        "description": "Demo confirmada en Cal.com",
        "show_on_sidebar": True,
    },
    {
        "title": "6_free_trial_activo",
        "color": "#06b6d4",
        "description": "Prueba gratuita de 7 días activa",
        "show_on_sidebar": True,
    },
    {
        "title": "7_cerrado_ganado",
        "color": "#15803d",
        "description": "Cliente cerrado / suscripción activa",
        "show_on_sidebar": True,
    },
    {
        "title": "8_descartado",
        "color": "#6b7280",
        "description": "Lead descartado o no calificado",
        "show_on_sidebar": True,
    },
    # Multi-tags de segmentación (acumulativos)
    {
        "title": "multisucursal",
        "color": "#f59e0b",
        "description": "Operación con más de 1 sucursal",
        "show_on_sidebar": True,
    },
    {
        "title": "alta_escala",
        "color": "#d97706",
        "description": "Car Wash grande (8+ estaciones)",
        "show_on_sidebar": True,
    },
    {
        "title": "hot_lead",
        "color": "#ef4444",
        "description": "Lead de alta prioridad (score >= 75)",
        "show_on_sidebar": True,
    },
    {
        "title": "dgii_fiscal",
        "color": "#dc2626",
        "description": "Interés en facturación DGII / NCF",
        "show_on_sidebar": True,
    },
    {
        "title": "dolor_caja",
        "color": "#ec4899",
        "description": "Dolor en gaveta / cierre a ciegas",
        "show_on_sidebar": True,
    },
    {
        "title": "dolor_nomina",
        "color": "#8b5cf6",
        "description": "Dolor en nómina y comisiones de lavadores",
        "show_on_sidebar": True,
    },
    {
        "title": "dolor_lluvia",
        "color": "#3b82f6",
        "description": "Dolor por días de lluvia y falta de membresías",
        "show_on_sidebar": True,
    },
    {
        "title": "demo_realizada",
        "color": "#059669",
        "description": "Llamada de demo/walkthrough completada",
        "show_on_sidebar": True,
    },
]


def inicializar():
    if not CHATWOOT_URL or not CHATWOOT_TOKEN:
        print("[ERROR] Falta CHATWOOT_URL o CHATWOOT_TOKEN en el .env")
        sys.exit(1)

    print(f"[*] Conectando a Chatwoot en {CHATWOOT_URL} (Cuenta {CHATWOOT_CUENTA_ID})...")

    # 1. Obtener definiciones actuales de atributos
    code, defs = _api("GET", "custom_attribute_definitions")
    existentes = set()
    if code == 200 and isinstance(defs, list):
        for item in defs:
            # key + model (0 o 1)
            existentes.add((item.get("attribute_key"), item.get("attribute_model")))
    print(f"[*] Atributos existentes en Chatwoot: {len(existentes)}")

    todos_atributos = ATRIBUTOS_CONTACTO + ATRIBUTOS_CONVERSACION
    creados_attr = 0
    for attr in todos_atributos:
        par = (attr["attribute_key"], attr["attribute_model"])
        if par in existentes:
            print(f"  - Atributo ya existe: {attr['attribute_key']} (modelo {attr['attribute_model']})")
            continue

        code, resp = _api("POST", "custom_attribute_definitions", attr)
        if code in (200, 201):
            print(f"  + Creado atributo: {attr['attribute_display_name']} ({attr['attribute_key']}) [Modelo {attr['attribute_model']}]")
            creados_attr += 1
        else:
            print(f"  ! Error creando {attr['attribute_key']}: {code} -> {resp}")

    print(f"[OK] Total atributos nuevos creados: {creados_attr}")

    # 2. Obtener etiquetas actuales
    code, labels_resp = _api("GET", "labels")
    existentes_labels = set()
    payload = labels_resp.get("payload") if isinstance(labels_resp, dict) else labels_resp
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                existentes_labels.add(item.get("title", "").strip().lower())
            elif isinstance(item, str):
                existentes_labels.add(item.strip().lower())

    print(f"[*] Etiquetas existentes en Chatwoot: {len(existentes_labels)}")

    creadas_labels = 0
    for label in ETIQUETAS:
        if label["title"].strip().lower() in existentes_labels:
            print(f"  - Etiqueta ya existe: {label['title']}")
            continue

        code, resp = _api("POST", "labels", label)
        if code in (200, 201):
            print(f"  + Creada etiqueta: {label['title']} ({label['color']})")
            creadas_labels += 1
        else:
            print(f"  ! Error creando etiqueta {label['title']}: {code} -> {resp}")

    print(f"[OK] Total etiquetas nuevas creadas: {creadas_labels}")
    print("[FINALIZADO] Inicialización de Chatwoot completada con éxito.")


if __name__ == "__main__":
    inicializar()
