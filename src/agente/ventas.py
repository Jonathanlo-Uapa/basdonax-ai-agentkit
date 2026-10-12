"""Las reglas del embudo de ventas, sin red ni modelo: se prueban solas.

El puntaje del prospecto se calcula acá y no lo pone el modelo, a propósito.
Un modelo que suma puntos se equivoca de cuenta, y uno al que le escriben
"poneme 100" puede obedecer. Con la cuenta en el código, el modelo solo
cuenta lo que entendió (el rol, las estaciones, el dolor) y la decisión de
ofrecer la demo, la prueba o seguir preguntando sale siempre igual.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

ROLES = ("dueno", "administrador", "encargado", "otro")
DOLORES = (
    "caja_ciega",
    "fuga_efectivo",
    "nomina_sabado",
    "seguro_lluvia",
    "dgii_fiscal",
    "ninguno",
)
SEGMENTOS = ("car_wash", "detailing", "flota", "particular", "otro")
SOFTWARES = ("cuaderno", "excel", "otro_pos", "lavapass", "ninguno")
URGENCIAS = ("esta_semana", "este_mes", "explorando")
RUTAS = ("diagnosticar", "prueba", "demo", "descartar")
BANDAS = ("frio", "tibio", "caliente", "prioridad")
ETAPAS = (
    "nuevo_lead",
    "diagnosticado",
    "calificado",
    "demo_propuesta",
    "demo_agendada",
    "descartado",
)
FRANJAS = ("manana", "tarde", "noche", "cualquiera")
QUIEN_DECIDE = ("dueno", "administrador")

# Prueba de 7 días (PRO). La demo y walkthrough con Jonathan pide 55 o tamaño MAX/Enterprise o dolor DGII.
UMBRAL_PRUEBA = 50
UMBRAL_DEMO = 55
UMBRAL = UMBRAL_DEMO
TOPE = 100

# El prospecto grande: lo toma una persona del equipo en caliente.
# Un "otro" no avisa: no sabemos si es el negocio.
SUCURSALES_DE_ALTO_VALOR = 2
ESTACIONES_DE_ALTO_VALOR = 3

PUNTOS_ROL = {
    "dueno": 30,
    "administrador": 22,
    "encargado": 12,
    "otro": 0,
}
PUNTOS_DOLOR = {
    "caja_ciega": 18,
    "fuga_efectivo": 18,
    "nomina_sabado": 14,
    "dgii_fiscal": 14,
    "seguro_lluvia": 12,
    "ninguno": 0,
}
PUNTOS_SEGMENTO = {
    "flota": 8,
    "detailing": 4,
    "car_wash": 0,
    "particular": 0,
    "otro": 0,
}
PUNTOS_SOFTWARE = {
    "cuaderno": 4,
    "ninguno": 4,
    "excel": 3,
    "otro_pos": 2,
    "lavapass": 0,
}
PUNTOS_URGENCIA = {
    "esta_semana": 6,
    "este_mes": 3,
    "explorando": 0,
}

LARGO_DE_UN_DATO = 80

# Lo que no tiene por qué estar en el nombre de un negocio y sí aparece en un
# intento de colar instrucciones o código: marcas de bloque, etiquetas HTML,
# llaves de plantillas.
_SOBRA = re.compile(r"[<>{}\[\]`\\|]")
_ESPACIOS = re.compile(r"\s+")


def _puntos_estaciones(estaciones: int) -> int:
    if estaciones >= 6:
        return 32
    if estaciones >= 3:
        return 28
    if estaciones >= 2:
        return 20
    if estaciones == 1:
        return 12
    return 0


def _puntos_sucursales(sucursales: int) -> int:
    if sucursales >= 3:
        return 35
    if sucursales == 2:
        return 22
    if sucursales == 1:
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
    return {
        "rol": PUNTOS_ROL.get(rol, 0),
        "estaciones": _puntos_estaciones(estaciones),
        "sucursales": _puntos_sucursales(sucursales),
        "dolor": PUNTOS_DOLOR.get(dolor, 0),
        "segmento": PUNTOS_SEGMENTO.get(segmento, 0),
        "software": PUNTOS_SOFTWARE.get(software_actual, 0),
        "urgencia": PUNTOS_URGENCIA.get(urgencia, 0),
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
    """Cuánto vale el prospecto, de 0 a 100.

    Dueño +30 · administrador +22 · encargado +12. Una estación +12, dos +20,
    tres a cinco +28, seis o más +32. Una sucursal +8, dos +22, tres o más +35.
    Caja ciega o fuga +18, nómina o DGII +14, lluvia +12. Flota, software y
    urgencia solo suman si el prospecto los dijo. El tope es 100.
    """
    return min(sum(desglose(
        rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia
    ).values()), TOPE)


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
        f"{puntos} {nombre}"
        for nombre, puntos in desglose(
            rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia
        ).items()
        if puntos
    ]
    total = puntaje(rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia)
    return " + ".join(partes) + f" = {total}" if partes else "0"


def tiene_operacion(estaciones: int, sucursales: int) -> bool:
    return estaciones >= 1 or sucursales >= 1


def es_alto_valor(estaciones: int, sucursales: int, rol: str = "") -> bool:
    """2+ sucursales o 3+ estaciones. Un 'otro' no avisa: no es el negocio."""
    if rol == "otro":
        return False
    return sucursales >= SUCURSALES_DE_ALTO_VALOR or estaciones >= ESTACIONES_DE_ALTO_VALOR


def banda(puntos: int) -> str:
    if puntos >= 85:
        return "prioridad"
    if puntos >= 70:
        return "caliente"
    if puntos >= UMBRAL_PRUEBA:
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
    if segmento == "particular":
        return "descartar"

    puntos = puntaje(rol, estaciones, sucursales, dolor, segmento, software_actual, urgencia)
    operacion = tiene_operacion(estaciones, sucursales)
    decide = rol in QUIEN_DECIDE
    grande = es_alto_valor(estaciones, sucursales, rol)
    es_dgii = dolor == "dgii_fiscal"

    if decide and operacion and (puntos >= UMBRAL_DEMO or grande or es_dgii):
        return "demo"
    if operacion and puntos >= UMBRAL_PRUEBA:
        return "prueba"
    return "diagnosticar"


def limpiar(texto, largo: int = LARGO_DE_UN_DATO) -> str:
    """Un dato que escribió el prospecto, listo para guardarse como texto.

    En una sola línea (un salto de línea podría inventar un renglón nuevo en
    lo que lee el modelo o el equipo), sin caracteres de control ni
    invisibles, sin los signos que arman código, y corto.
    """
    if not isinstance(texto, str):
        return ""
    sin_control = "".join(
        " " if unicodedata.category(c).startswith(("C", "Z")) else c for c in texto
    )
    return _ESPACIOS.sub(" ", _SOBRA.sub("", sin_control)).strip()[:largo].strip()


def entero(valor) -> int:
    """Una cantidad que dijo el modelo. Lo que no es un número razonable es 0 (no se sabe)."""
    if isinstance(valor, bool):
        return 0
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return 0
    return numero if 0 <= numero <= 500 else 0


# -- Las fechas como las dice una persona -------------------------------------

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def fecha_dicha(momento: datetime) -> str:
    """'sábado 10 de octubre'."""
    return f"{DIAS[momento.weekday()]} {momento.day} de {MESES[momento.month - 1]}"


def hora_dicha(momento: datetime) -> str:
    """'6:30 p. m.', como se dice en RD."""
    hora = momento.hour % 12 or 12
    sufijo = "a. m." if momento.hour < 12 else "p. m."
    return f"{hora}:{momento.minute:02d} {sufijo}"


def franja_de(momento: datetime) -> str:
    if momento.hour < 12:
        return "manana"
    if momento.hour < 18:
        return "tarde"
    return "noche"
