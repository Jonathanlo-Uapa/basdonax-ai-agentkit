"""Notificaciones ejecutivas del agente a Slack (#lavapass-ai-notifications).

Envía tarjetas formateadas a Slack mediante Incoming Webhook cuando ocurren
eventos clave: reservas en Cal.com con Jonathan López, entregas del enlace de
Free Trial, alertas fiscales de la DGII y traspasos a un humano.

Usa únicamente la biblioteca estándar (`urllib`), siguiendo la convención
general del proyecto sin dependencias externas.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class NotificadorSlack:
    """Envía mensajes y tarjetas visuales a Slack."""

    def __init__(self, webhook_url: str = "") -> None:
        self.webhook_url = (webhook_url or "").strip()

    @property
    def activo(self) -> bool:
        """Indica si hay un webhook configurado."""
        return bool(self.webhook_url)

    def notificar_demo(
        self,
        *,
        nombre: str,
        telefono: str,
        fecha_hora: str,
        estaciones: int = 1,
        dolor: str = "",
        chatwoot_url: str = "",
    ) -> bool:
        """Avisa de una demo/onboarding agendada con Jonathan López (COO)."""
        contacto = nombre or "Sin nombre"
        tel = telefono or "Sin número"
        texto = (
            "📅 *Nueva Demo Agendada con Jonathan López (COO)*\n"
            f"• *Prospecto:* {contacto} ({tel})\n"
            f"• *Fecha y Hora:* {fecha_hora}\n"
            f"• *Pistas / Estaciones:* {estaciones}\n"
            f"• *Dolor principal:* {dolor or 'No especificado'}\n"
            f"• *Conversación:* <{chatwoot_url}|Abrir en Chatwoot>" if chatwoot_url else
            f"• *Conversación:* Chatwoot"
        )
        return self._enviar(texto, color="#2EB886")

    def notificar_free_trial(
        self,
        *,
        nombre: str,
        telefono: str,
        score: int = 0,
        chatwoot_url: str = "",
    ) -> bool:
        """Avisa que un prospecto calificado recibió el enlace de registro del Free Trial."""
        contacto = nombre or "Sin nombre"
        tel = telefono or "Sin número"
        texto = (
            "🚀 *Free Trial Entregado (panel.lavapass.app)*\n"
            f"• *Prospecto:* {contacto} ({tel})\n"
            f"• *Calificación:* {score} pts\n"
            f"• *Acceso provisto:* 7 días gratis en panel móvil\n"
            f"• *Conversación:* <{chatwoot_url}|Abrir en Chatwoot>" if chatwoot_url else
            f"• *Conversación:* Chatwoot"
        )
        return self._enviar(texto, color="#3AA3E3")

    def notificar_dgii(
        self,
        *,
        nombre: str,
        telefono: str,
        estaciones: int = 1,
        chatwoot_url: str = "",
    ) -> bool:
        """Avisa de un prospecto de alta prioridad con requerimiento fiscal DGII / e-CF."""
        contacto = nombre or "Sin nombre"
        tel = telefono or "Sin número"
        texto = (
            "🏛️ *PROSPECTO FISCAL DGII DETECTADO (Prioridad Alta)*\n"
            f"• *Contacto:* {contacto} ({tel})\n"
            f"• *Pistas / Estaciones:* {estaciones}\n"
            f"• *Requerimiento:* Facturación electrónica e-CF / NCF fiscal\n"
            f"• *Conversación:* <{chatwoot_url}|Abrir en Chatwoot>" if chatwoot_url else
            f"• *Conversación:* Chatwoot"
        )
        return self._enviar(texto, color="#E01E5A")

    def notificar_traspaso(
        self,
        *,
        nombre: str,
        telefono: str,
        motivo: str,
        chatwoot_url: str = "",
    ) -> bool:
        """Avisa que una conversación de WhatsApp requiere atención humana."""
        contacto = nombre or "Sin nombre"
        tel = telefono or "Sin número"
        texto = (
            "🚨 *Atención Humana Requerida en WhatsApp*\n"
            f"• *Contacto:* {contacto} ({tel})\n"
            f"• *Motivo:* {motivo or 'Solicitud de intervención'}\n"
            f"• *Conversación:* <{chatwoot_url}|Atender en Chatwoot>" if chatwoot_url else
            f"• *Conversación:* Chatwoot"
        )
        return self._enviar(texto, color="#ECB22E")

    def _enviar(self, texto: str, color: str = "#4A154B") -> bool:
        """Construye la carga útil y la despacha al webhook de Slack."""
        if not self.activo:
            return False

        payload: dict[str, Any] = {
            "attachments": [
                {
                    "color": color,
                    "text": texto,
                    "mrkdwn_in": ["text"],
                }
            ]
        }
        cuerpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        pedido = urllib.request.Request(
            self.webhook_url,
            data=cuerpo,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(pedido, timeout=5) as respuesta:
                return respuesta.status == 200
        except Exception as error:
            logger.warning("No se pudo enviar notificación a Slack: %s", error)
            return False
