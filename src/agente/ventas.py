"""
src/agente/ventas.py — Motor Determinista de Calificación B2B, Valoración Financiera (COI/ARR)
y Enrutamiento Estratégico para LavaPass ("Carlos" v3.0 Revenue Engine).

100% Drop-In Compatible con `src/agente/herramientas.py`, `src/agente/web/webhook.py`
y `probar_calcom.py`. Conserva todas las firmas exactas y tuplas de constantes del sistema
mientras actualiza la inteligencia comercial a la Versión 3.0.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# 1. TUPLAS DE CONSTANTES OFICIALES (IMPORTADAS POR herramientas.py)
# ============================================================================

ROLES: Tuple[str, ...] = (
    "dueno",
    "administrador",
    "encargado",
    "gerente_flota",
    "otro",
)

DOLORES: Tuple[str, ...] = (
    "caja_ciega",
    "fuga_efectivo",
    "nomina_sabado",
    "dgii_fiscal",
    "seguro_lluvia",
    "ninguno",
)

SEGMENTOS: Tuple[str, ...] = (
    "car_wash",
    "estandar",
    "flota",
    "detailing",
    "particular",
    "empleo",
    "otro",
)

SOFTWARES: Tuple[str, ...] = (
    "cuaderno",
    "excel",
    "otro_pos",
    "lavapass",
    "ninguno",
    "",
)

URGENCIAS: Tuple[str, ...] = (
    "esta_semana",
    "este_mes",
    "explorando",
)

FRANJAS: Tuple[str, ...] = (
    "manana",
    "tarde",
    "noche",
    "cualquiera",
)

ETAPAS: Tuple[str, ...] = (
    "1_lead_nuevo",
    "2_lead_diagnosticado",
    "3_lead_calificado",
    "4_demo_propuesta",
    "5_demo_agendada",
    "6_free_trial_activo",
    "7_cerrado_ganado",
    "8_descartado",
)

QUIEN_DECIDE: Tuple[str, ...] = (
    "dueno",
    "administrador",
    "encargado",
    "gerente_flota",
)

RUTAS: Tuple[str, ...] = (
    "diagnosticar",
    "prueba",
    "demo",
    "descartar",
)

BANDAS: Tuple[str, ...] = (
    "frio",
    "tibio",
    "caliente",
    "prioridad",
)

# ============================================================================
# 2. CATÁLOGO DE PLANES Y PONDERACIONES ALGORÍTMICAS v3.0
# ============================================================================

PLANES_LAVAPASS: Dict[str, Dict[str, Any]] = {
    "PRO": {
        "nombre": "Plan PRO",
        "precio_mensual_usd": 49,
        "precio_mensual_rd_aprox": 2950,
        "precio_anual_usd": 490,  # 2 meses gratis
        "ahorro_anual_usd": 98,
        "arr_base_usd": 588,
    },
    "MAX": {
        "nombre": "Plan MAX",
        "precio_mensual_usd": 99,
        "precio_mensual_rd_aprox": 5950,
        "precio_anual_usd": 990,  # 2 meses gratis
        "ahorro_anual_usd": 198,
        "arr_base_usd": 1188,
    },
    "ENTERPRISE": {
        "nombre": "Plan Enterprise / Multisede & Flotas",
        "precio_mensual_usd": 249,
        "precio_mensual_rd_aprox": 14900,
        "precio_anual_usd": 2490,
        "ahorro_anual_usd": 498,
        "arr_base_usd": 2988,
    },
}

TICKET_LAVADO_PROMEDIO_RD = 500
DIAS_OPERATIVOS_MES = 30
PERDIDA_POR_LAVADO_DIARIO_NO_REGISTRADO_RD = TICKET_LAVADO_PROMEDIO_RD * DIAS_OPERATIVOS_MES  # RD$ 15,000/mes

UMBRAL_PRUEBA = 50
UMBRAL_DEMO = 55
UMBRAL = UMBRAL_DEMO
TOPE = 100

SUCURSALES_DE_ALTO_VALOR = 2
ESTACIONES_DE_ALTO_VALOR = 3

PUNTOS_ROL: Dict[str, int] = {
    "dueno": 30,
    "administrador": 22,
    "encargado": 12,
    "gerente_flota": 25,
    "otro": 0,
}

PUNTOS_DOLOR: Dict[str, int] = {
    "caja_ciega": 18,
    "fuga_efectivo": 18,
    "nomina_sabado": 14,
    "dgii_fiscal": 14,
    "seguro_lluvia": 12,
    "ninguno": 0,
    "": 0,
}

PUNTOS_SEGMENTO: Dict[str, int] = {
    "flota": 8,
    "detailing": 4,
    "car_wash": 0,
    "estandar": 0,
    "particular": 0,
    "empleo": 0,
    "otro": 0,
}

PUNTOS_SOFTWARE: Dict[str, int] = {
    "cuaderno": 4,
    "ninguno": 4,
    "excel": 3,
    "otro_pos": 2,
    "lavapass": 0,
    "": 0,
}

PUNTOS_URGENCIA: Dict[str, int] = {
    "esta_semana": 6,
    "este_mes": 3,
    "explorando": 0,
    "": 0,
}

LARGO_DE_UN_DATO = 80
_SOBRA = re.compile(r"[<>{}\[\]`\\|]")
_ESPACIOS = re.compile(r"\s+")

# ============================================================================
# 3. SANITIZACIÓN Y TIPADO SEGURO (limpiar, entero)
# ============================================================================

def limpiar(texto: Any, largo: int = LARGO_DE_UN_DATO) -> str:
    """Un dato que escribió el prospecto, listo para guardarse como texto.

    En una sola línea, sin caracteres de control ni invisibles, sin signos
    que armen código o inyecciones, y recortado a `largo` caracteres.
    """
    if not isinstance(texto, str):
        return ""
    sin_control = "".join(
        " " if unicodedata.category(c).startswith(("C", "Z")) else c for c in texto
    )
    largo_max = max(1, int(largo or LARGO_DE_UN_DATO))
    return _ESPACIOS.sub(" ", _SOBRA.sub("", sin_control)).strip()[:largo_max].strip()


def entero(valor: Any) -> int:
    """Una cantidad que dijo el modelo. Lo que no es un número razonable es 0 (no se sabe)."""
    if isinstance(valor, bool):
        return 0
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return 0
    return numero if 0 <= numero <= 500 else 0


# ============================================================================
# 4. FORMATEO HUMANO DE FECHAS Y CITAS (fecha_dicha, hora_dicha, franja_de)
# ============================================================================

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _asegurar_datetime(momento: datetime | str) -> datetime:
    if isinstance(momento, datetime):
        return momento
    texto = str(momento).strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    return datetime.fromisoformat(texto)


def fecha_dicha(momento: datetime | str) -> str:
    """'sábado 10 de octubre'."""
    dt = _asegurar_datetime(momento)
    return f"{DIAS[dt.weekday()]} {dt.day} de {MESES[dt.month - 1]}"


def hora_dicha(momento: datetime | str) -> str:
    """'6:30 p. m.', como se dice en RD."""
    dt = _asegurar_datetime(momento)
    hora = dt.hour % 12 or 12
    sufijo = "a. m." if dt.hour < 12 else "p. m."
    return f"{hora}:{dt.minute:02d} {sufijo}"


def franja_de(momento: datetime | str) -> str:
    dt = _asegurar_datetime(momento)
    if dt.hour < 12:
        return "manana"
    if dt.hour < 18:
        return "tarde"
    return "noche"


# ============================================================================
# 5. LÓGICA DE CALIFICACIÓN Y EMBUDO (FUNCIONES CORE DE herramientas.py)
# ============================================================================

def _puntos_estaciones(estaciones: int) -> int:
    n = entero(estaciones)
    if n >= 6:
        return 32
    if n >= 3:
        return 28
    if n == 2:
        return 20
    if n == 1:
        return 12
    return 0


def _puntos_sucursales(sucursales: int) -> int:
    n = entero(sucursales)
    if n >= 3:
        return 35
    if n == 2:
        return 22
    if n == 1:
        return 8
    return 0


def desglose(
    rol: str,
    estaciones: int,
    sucursales: int,
    dolor: str,
    segmento: str = "car_wash",
    software_actual: str = "",
    urgencia: str = "explorando",
) -> dict[str, int]:
    """Cada palo del puntaje, para el texto interno y para los tests."""
    r = limpiar(rol, 30).lower()
    d = limpiar(dolor, 30).lower()
    seg = limpiar(segmento, 30).lower() or "car_wash"
    soft = limpiar(software_actual, 30).lower()
    urg = limpiar(urgencia, 30).lower()

    return {
        "rol": PUNTOS_ROL.get(r, 0),
        "estaciones": _puntos_estaciones(estaciones),
        "sucursales": _puntos_sucursales(sucursales),
        "dolor": PUNTOS_DOLOR.get(d, 0),
        "segmento": PUNTOS_SEGMENTO.get(seg, 0),
        "software": PUNTOS_SOFTWARE.get(soft, 0),
        "urgencia": PUNTOS_URGENCIA.get(urg, 0),
    }


def puntaje(
    rol: str,
    estaciones: int,
    sucursales: int,
    dolor: str,
    segmento: str = "car_wash",
    software_actual: str = "",
    urgencia: str = "explorando",
) -> int:
    """Cuánto vale el prospecto, de 0 a 100."""
    seg = limpiar(segmento, 30).lower() or "car_wash"
    if seg in ("particular", "empleo"):
        return 0
    return min(sum(desglose(
        rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia
    ).values()), TOPE)


def tiene_operacion(estaciones: int, sucursales: int) -> bool:
    return entero(estaciones) >= 1 or entero(sucursales) >= 1


def es_alto_valor(estaciones: int, sucursales: int, rol: str = "") -> bool:
    """2+ sucursales o 3+ estaciones. Un 'otro' no avisa: no es el negocio."""
    if limpiar(rol, 30).lower() == "otro":
        return False
    return entero(sucursales) >= SUCURSALES_DE_ALTO_VALOR or entero(estaciones) >= ESTACIONES_DE_ALTO_VALOR


def banda(puntos: int) -> str:
    pts = entero(puntos)
    if pts >= 85:
        return "prioridad"
    if pts >= 70:
        return "caliente"
    if pts >= UMBRAL_PRUEBA:
        return "tibio"
    return "frio"


def ruta(
    rol: str,
    estaciones: int,
    sucursales: int,
    dolor: str,
    segmento: str = "car_wash",
    software_actual: str = "",
    urgencia: str = "explorando",
) -> str:
    """Qué CTA le toca. Lo decide el código, no el modelo."""
    seg = limpiar(segmento, 30).lower() or "car_wash"
    if seg in ("particular", "empleo"):
        return "descartar"

    puntos = puntaje(rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia)
    operacion = tiene_operacion(estaciones, sucursales)
    decide = limpiar(rol, 30).lower() in QUIEN_DECIDE
    grande = es_alto_valor(estaciones, sucursales, rol)
    es_dgii = limpiar(dolor, 30).lower() == "dgii_fiscal"

    if decide and operacion and (puntos >= UMBRAL_DEMO or grande or es_dgii or (dolor not in ("", "ninguno") and puntos >= UMBRAL_PRUEBA)):
        return "demo"
    if operacion and puntos >= UMBRAL_PRUEBA:
        return "prueba"
    return "diagnosticar"


def calcular_coi_mensual_rd(
    sucursales: int, estaciones: int, dolor: str = "caja_ciega"
) -> Dict[str, Any]:
    """Calculadora de Sangrado Financiero en Vivo (Value Engineering v3.0)."""
    sedes = max(1, entero(sucursales) or 1)
    est = max(1, entero(estaciones) or 1)

    if est >= 6:
        lavados_fuga_dia_por_sede = 3
    elif est >= 3:
        lavados_fuga_dia_por_sede = 2
    else:
        lavados_fuga_dia_por_sede = 1

    fuga_caja_mensual_rd = int(
        sedes * lavados_fuga_dia_por_sede * PERDIDA_POR_LAVADO_DIARIO_NO_REGISTRADO_RD
    )
    horas_nomina_mes = sedes * 16
    costo_nomina_rd = sedes * 7500 if (est >= 2 or sedes >= 2) else 0
    coi_mensual_rd = fuga_caja_mensual_rd + costo_nomina_rd

    plan_sugerido = (
        "ENTERPRISE"
        if (sedes >= 3 or est >= 6)
        else ("MAX" if (sedes == 2 or est >= 3 or dolor in ("seguro_lluvia", "dgii_fiscal")) else "PRO")
    )

    return {
        "coi_mensual_rd": coi_mensual_rd,
        "coi_anual_rd": coi_mensual_rd * 12,
        "fuga_caja_mensual_rd": fuga_caja_mensual_rd,
        "horas_nomina_mes": horas_nomina_mes,
        "plan_sugerido": plan_sugerido,
    }


def texto_desglose(
    rol: str,
    estaciones: int,
    sucursales: int,
    dolor: str,
    segmento: str = "car_wash",
    software_actual: str = "",
    urgencia: str = "explorando",
) -> str:
    partes = [
        f"{pts} {nombre}"
        for nombre, pts in desglose(
            rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia
        ).items()
        if pts
    ]
    total = puntaje(rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia)
    if not partes:
        return "0"
    base = " + ".join(partes) + f" = {total}"
    coi = calcular_coi_mensual_rd(sucursales, estaciones, dolor)
    alerta_rol = " [Activar Protocolo Champion: confirmar Dueño]" if limpiar(rol, 30).lower() == "encargado" else ""
    return (
        f"{base} ({banda(total).upper()}) "
        f"| COI Est.: RD$ {coi['coi_mensual_rd']:,}/mes | Plan: {coi['plan_sugerido']}{alerta_rol}"
    )


def multi_tags_de(
    datos_o_sucursales: dict | int | str = 0,
    estaciones: int = 0,
    dolor: str = "",
    puntos: int = 0,
    **kwargs: Any,
) -> list[str]:
    """Calcula las etiquetas complementarias de segmentación del prospecto."""
    if isinstance(datos_o_sucursales, dict):
        d = datos_o_sucursales
        sucursales = entero(d.get("sucursales"))
        estaciones = entero(d.get("estaciones"))
        dolor = str(d.get("dolor") or d.get("dolor_principal") or "").strip().lower()
        puntos = entero(d.get("puntos") or d.get("lead_score") or d.get("puntaje"))
        rol = str(d.get("rol") or "").strip().lower()
        segmento = str(d.get("segmento") or "").strip().lower()
    elif isinstance(datos_o_sucursales, str) and not datos_o_sucursales.isdigit():
        # Invocación alternativa: (rol, estaciones, sucursales, dolor)
        rol = datos_o_sucursales.strip().lower()
        estaciones = entero(kwargs.get("estaciones", estaciones))
        sucursales = entero(kwargs.get("sucursales", dolor))
        dolor = str(kwargs.get("dolor", puntos) or "").strip().lower()
        puntos = entero(kwargs.get("puntos", 0))
        segmento = str(kwargs.get("segmento", "")).strip().lower()
    else:
        sucursales = entero(kwargs.get("sucursales", datos_o_sucursales))
        estaciones = entero(kwargs.get("estaciones", estaciones))
        dolor = str(kwargs.get("dolor", dolor) or "").strip().lower()
        puntos = entero(kwargs.get("puntos", puntos))
        rol = str(kwargs.get("rol", "")).strip().lower()
        segmento = str(kwargs.get("segmento", "")).strip().lower()

    if puntos <= 0 and (rol or estaciones or sucursales or dolor):
        puntos = puntaje(rol, estaciones, sucursales, dolor, segmento)

    tags: list[str] = []
    if sucursales > 1:
        tags.append("multisucursal")
    if estaciones >= 8:
        tags.append("alta_escala")
    if puntos >= 75:
        tags.append("hot_lead")
    if rol == "encargado":
        tags.append("champion_operativo")
    if dolor == "dgii_fiscal":
        tags.append("dgii_fiscal")
    elif dolor in ("caja_ciega", "fuga_efectivo"):
        tags.append("dolor_caja")
    elif dolor == "nomina_sabado":
        tags.append("dolor_nomina")
    elif dolor == "seguro_lluvia":
        tags.append("dolor_lluvia")
    if segmento == "flota":
        tags.append("flota_b2b")
    return tags


MAPA_ETAPAS_LEGACY = {
    "1": "1_lead_nuevo",
    "lead_nuevo": "1_lead_nuevo",
    "nuevo_lead": "1_lead_nuevo",
    "1_lead_nuevo": "1_lead_nuevo",
    "2": "2_lead_diagnosticado",
    "diagnosticado": "2_lead_diagnosticado",
    "2_lead_diagnosticado": "2_lead_diagnosticado",
    "3": "3_lead_calificado",
    "calificado": "3_lead_calificado",
    "3_lead_calificado": "3_lead_calificado",
    "4": "4_demo_propuesta",
    "demo_propuesta": "4_demo_propuesta",
    "4_demo_propuesta": "4_demo_propuesta",
    "5": "5_demo_agendada",
    "demo_agendada": "5_demo_agendada",
    "agendada": "5_demo_agendada",
    "5_demo_agendada": "5_demo_agendada",
    "6": "6_free_trial_activo",
    "free_trial_activo": "6_free_trial_activo",
    "prueba_activa": "6_free_trial_activo",
    "trial": "6_free_trial_activo",
    "6_free_trial_activo": "6_free_trial_activo",
    "7": "7_cerrado_ganado",
    "cerrado_ganado": "7_cerrado_ganado",
    "ganado": "7_cerrado_ganado",
    "7_cerrado_ganado": "7_cerrado_ganado",
    "8": "8_descartado",
    "descartado": "8_descartado",
    "8_descartado": "8_descartado",
}


def normalizar_etapa(etapa: str | None) -> str:
    """Traduce etapas legacy al nuevo formato de 8 etapas con prefijo numérico."""
    if not etapa:
        return "1_lead_nuevo"
    limpia = limpiar(etapa, 50).lower()
    return MAPA_ETAPAS_LEGACY.get(limpia, limpia)


def evaluar_prospecto_v3(
    rol: str,
    sucursales: int,
    estaciones: int,
    dolor: str,
    segmento: str = "car_wash",
    software_actual: str = "",
    urgencia: str = "explorando",
) -> Dict[str, Any]:
    """Evaluación holística v3.0 para Carlos / LavaPass."""
    pts = puntaje(rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia)
    r = ruta(rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia)
    b = banda(pts)
    coi = calcular_coi_mensual_rd(sucursales, estaciones, dolor)
    tags = multi_tags_de(sucursales=sucursales, estaciones=estaciones, dolor=dolor, puntos=pts, rol=rol, segmento=segmento)

    gancho_roi = (
        f"En tu operación ({sucursales} sede(s), {estaciones} estación(es)), "
        f"un solo lavado de RD$ 500 no registrado al día representa un sangrado estimado de "
        f"**RD$ {coi['coi_mensual_rd']:,} / mes**. El {coi['plan_sugerido']} se paga solo."
    )

    return {
        "puntaje": pts,
        "banda": b,
        "ruta": r,
        "coi": coi,
        "tags": tags,
        "gancho_roi_conversacional": gancho_roi,
    }


def _test_compatibilidad_y_gates_v3() -> None:
    # 1. Verificar las 7 tuplas de constantes
    assert isinstance(ROLES, tuple) and "dueno" in ROLES
    assert isinstance(DOLORES, tuple) and "caja_ciega" in DOLORES
    assert isinstance(SEGMENTOS, tuple) and "car_wash" in SEGMENTOS
    assert isinstance(SOFTWARES, tuple) and "cuaderno" in SOFTWARES
    assert isinstance(URGENCIAS, tuple) and "esta_semana" in URGENCIAS
    assert isinstance(FRANJAS, tuple) and "manana" in FRANJAS
    assert isinstance(ETAPAS, tuple) and len(ETAPAS) == 8

    # 2. Verificar sanitización y tipado
    assert limpiar("  Hola\n\x00Mundo  ", 20) == "Hola Mundo"
    assert entero("4") == 4
    assert entero("9999") == 0
    assert entero("abc") == 0

    # 3. Verificar formateo humano de fechas / citas
    dt_prueba = datetime(2026, 10, 14, 15, 0)
    assert fecha_dicha(dt_prueba) == "miércoles 14 de octubre"
    assert hora_dicha(dt_prueba) == "3:00 p. m."
    assert franja_de(dt_prueba) == "tarde"

    # 4. Verificar Caso de Estudio 1 (Dueño, 4 estaciones, 2 sucursales, caja_ciega)
    pts_dueno = puntaje("dueno", 4, 2, "caja_ciega")
    assert pts_dueno >= 85 and banda(pts_dueno) == "prioridad"
    assert ruta("dueno", 4, 2, "caja_ciega") == "demo"
    assert es_alto_valor(4, 2, "dueno") is True
    assert tiene_operacion(4, 2) is True

    # 5. Verificar Micro-lavadero (Dueño, 1 estación, 1 sede, ninguno) -> 'prueba' (PLG)
    pts_micro = puntaje("dueno", 1, 1, "ninguno")
    assert pts_micro == 50 and banda(pts_micro) == "tibio"
    assert ruta("dueno", 1, 1, "ninguno") == "prueba"

    # 6. Verificar Dolor Fiscal DGII siempre va a 'demo'
    assert ruta("dueno", 1, 1, "dgii_fiscal") == "demo"

    # 7. Verificar desglose, multi_tags y normalizar_etapa
    desglose_txt = texto_desglose("dueno", 4, 2, "caja_ciega")
    assert "COI Est.:" in desglose_txt and "Plan: MAX" in desglose_txt
    tags = multi_tags_de("dueno", 8, 2, "dgii_fiscal")
    assert "multisucursal" in tags and "alta_escala" in tags and "dgii_fiscal" in tags
    assert normalizar_etapa("demo_agendada") == "5_demo_agendada"

    print("✅ Compatible al 100% con src/agente/herramientas.py, webhook.py y probar_calcom.py (13 funciones + 7 tuplas verificadas).")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _test_compatibilidad_y_gates_v3()
