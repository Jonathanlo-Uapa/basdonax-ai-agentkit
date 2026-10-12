"""Lo que las herramientas necesitan saber de la conversación que atienden.

El agente recibe texto y devuelve texto (es la regla del proyecto), y las
herramientas las elige el modelo con los datos que el modelo quiera. Pero
hay cosas que el modelo NO puede elegir: a qué conversación de Chatwoot se le
guardan los datos, a qué teléfono queda la reserva. Si las eligiera, un
mensaje bien armado ("guardalo en la conversación 15") alcanzaría para
escribir en la de otro.

Por eso el webhook, antes de llamar al agente, deja acá un `Contexto` con la
conversación, el canal y la agenda, y las herramientas lo leen. Va en una
`ContextVar` y no en una variable global: cada conversación que se atiende a
la vez tiene la suya (asyncio.to_thread y los hilos de LangGraph copian el
contexto), así que dos personas que escriben al mismo tiempo no se pisan.

Sin contexto (la terminal, la plataforma de pruebas, Telegram), las
herramientas no escriben en ningún CRM ni reservan: lo dicen y la charla
sigue.

El traspaso en caliente va por acá también, y no puede ir directo: si la
herramienta le pusiera `humano` a la conversación en la mitad del turno, el
webhook lo vería al volver a mirar justo antes de mandar y se callaría su
propia respuesta. Entonces la herramienta lo PIDE, y el webhook lo hace
después de mandar.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator

# Lo que se puede pedir para después de mandar la respuesta.
ALTO_VALOR = "alto_valor"        # la etiqueta del prospecto grande y el mail al dueño
A_UNA_PERSONA = "humano"         # la etiqueta que calla al agente
SOLICITUD_DGII = "solicitud_dgii"  # el aviso por mail a info@lavapass.app y la etiqueta dgii


@dataclass
class Pedido:
    tipo: str
    detalle: str = ""


@dataclass
class Contexto:
    conversacion: str
    canal: Any            # canales.chatwoot.Chatwoot
    calcom: Any = None    # calcom.Calcom, o None si no está configurado
    pedidos: list[Pedido] = field(default_factory=list)

    def pedir(self, tipo: str, detalle: str = "") -> None:
        if all(p.tipo != tipo for p in self.pedidos):
            self.pedidos.append(Pedido(tipo, detalle))


_EN_CURSO: ContextVar[Contexto | None] = ContextVar("conversacion_en_curso", default=None)


def en_curso() -> Contexto | None:
    """El contexto de la conversación que se está atendiendo, o None."""
    return _EN_CURSO.get()


@contextmanager
def atendiendo(contexto: Contexto) -> Iterator[Contexto]:
    """Mientras dura el bloque, las herramientas trabajan sobre esa conversación."""
    marca = _EN_CURSO.set(contexto)
    try:
        yield contexto
    finally:
        _EN_CURSO.reset(marca)
