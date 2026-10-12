"""Revisa la agenda de las demos en Cal.com, sin reservar nada.

    python probar_calcom.py

Pide los horarios libres de los próximos 14 días con CALCOM_API_KEY y
CALCOM_EVENT_TYPE_ID, y se fija que todos caigan adentro de la ventana
acordada para las demos y walkthroughs con Jonathan Lopez (COO). Si alguno
cae afuera o en madrugada, avisa para revisar la zona horaria (America/Santo_Domingo).

Se corre donde corre el agente (o en local): así prueba también que se
llega a Cal.com. Solo lee lo de Cal.com: no hace falta la clave del
modelo.

El agente le cree a Cal.com. La disponibilidad se configura directamente
en la cuenta de Cal.com (Availability).
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agente.consola import preparar  # noqa: E402

preparar()  # antes de imprimir nada, para que las tildes no rompan Windows

from agente.calcom import Calcom, ErrorDeCalcom, ahora_en_rd  # noqa: E402
from agente.config import ErrorDeConfiguracion, datos_de_calcom  # noqa: E402
from agente.ventas import fecha_dicha, hora_dicha  # noqa: E402

VERDE = "\033[92m"
GRIS = "\033[90m"
ROJO = "\033[91m"
FIN = "\033[0m"

DURACION = timedelta(minutes=15)
DIAS = 14

# Hora de RD. lunes=0 … domingo=6. (desde, hasta) en horas; None = cerrado.
HORARIO_ACORDADO = {
    0: (18, 20),
    1: None,
    2: (18, 21),
    3: (18, 21),
    4: (18, 21),
    5: (9, 21),
    6: (9, 21),
}


def fuera_del_horario(comienzo: datetime) -> bool:
    """Si una demo que empieza ahí (y dura 15 minutos) se sale de lo acordado."""
    ventana = HORARIO_ACORDADO[comienzo.weekday()]
    if ventana is None:
        return True
    desde = comienzo.replace(hour=ventana[0], minute=0, second=0, microsecond=0)
    hasta = comienzo.replace(hour=ventana[1], minute=0, second=0, microsecond=0)
    return not (desde <= comienzo and comienzo + DURACION <= hasta)


def main() -> int:
    try:
        datos = datos_de_calcom()
        agenda = Calcom(datos["url"], datos["clave"], datos["evento"])
    except (ErrorDeConfiguracion, ValueError) as e:
        print(f"{ROJO}{e}{FIN}")
        return 1

    hoy = ahora_en_rd().date()
    print(f"\nPidiendo a Cal.com los horarios del tipo de evento {agenda.tipo_de_evento}")
    print(f"{GRIS}   del {hoy} al {hoy + timedelta(days=DIAS)}, en hora de RD{FIN}\n")

    try:
        horarios = agenda.horarios(hoy, hoy + timedelta(days=DIAS))
    except ErrorDeCalcom as e:
        print(f"{ROJO}{e}{FIN}")
        if e.codigo == 401:
            print("Revisá CALCOM_API_KEY: la clave está mal copiada o la borraron.")
        elif e.codigo == 404:
            print("Revisá CALCOM_EVENT_TYPE_ID: ese tipo de evento no existe en esta cuenta.")
        return 1

    if not horarios:
        print(f"{ROJO}Cal.com no devolvió ningún horario libre en {DIAS} días.{FIN}")
        print("Revisá el horario (Availability) del tipo de evento y que no esté oculto.")
        return 1

    por_dia: dict = {}
    for h in horarios:
        por_dia.setdefault(h.date(), []).append(h)
    for dia, lista in por_dia.items():
        print(f"   {fecha_dicha(lista[0])}: {len(lista)} horarios, "
              f"de {hora_dicha(lista[0])} a {hora_dicha(lista[-1])}")

    afuera = [h for h in horarios if fuera_del_horario(h)]
    if afuera:
        print(f"\n{ROJO}{len(afuera)} horario(s) caen fuera de lo acordado:{FIN}")
        for h in afuera[:10]:
            print(f"   {fecha_dicha(h)} a las {hora_dicha(h)}")
        print("Revisá en Cal.com el horario del tipo de evento y su zona horaria "
              "(America/Santo_Domingo).")
        return 1

    print(f"\n{VERDE}Agenda OK.{FIN} {len(horarios)} horarios libres, todos dentro de lo acordado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
