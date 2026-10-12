"""Pruebas del notificador a Slack (#lavapass-ai-notifications).

Verifica que el notificador arme las tarjetas correctas y maneje errores de red
sin tirar excepciones ni consumir tokens.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agente.slack import NotificadorSlack


def test_slack_inactivo_sin_url():
    slack = NotificadorSlack("")
    assert not slack.activo
    # Si está inactivo, no manda nada y devuelve False
    assert not slack.notificar_demo(
        nombre="Test",
        telefono="+18090000000",
        fecha_hora="2026-10-15 10:00 AM",
    )


def test_slack_notificar_demo():
    slack = NotificadorSlack("https://hooks.slack.com/services/FAKE/TEST/123")
    assert slack.activo

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ok = slack.notificar_demo(
            nombre="Juan Perez",
            telefono="+18091234567",
            fecha_hora="Jueves 15 de octubre a las 10:00 AM",
            estaciones=4,
            dolor="caja_ciega",
            chatwoot_url="https://appchatwoot.lavapass.app/app/accounts/1/conversations/10",
        )
        assert ok is True
        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        cuerpo = req.data.decode("utf-8")
        assert "Juan Perez" in cuerpo
        assert "Jonathan López" in cuerpo
        assert "caja_ciega" in cuerpo
        assert "#2EB886" in cuerpo


def test_slack_notificar_free_trial():
    slack = NotificadorSlack("https://hooks.slack.com/services/FAKE/TEST/123")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ok = slack.notificar_free_trial(
            nombre="Car Wash El Sol",
            telefono="+18095551234",
            score=68,
            chatwoot_url="https://appchatwoot.lavapass.app/app/accounts/1/conversations/11",
        )
        assert ok is True
        req = mock_urlopen.call_args[0][0]
        cuerpo = req.data.decode("utf-8")
        assert "Free Trial Entregado" in cuerpo
        assert "68 pts" in cuerpo


def test_slack_notificar_dgii():
    slack = NotificadorSlack("https://hooks.slack.com/services/FAKE/TEST/123")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ok = slack.notificar_dgii(
            nombre="Centro de Lavado Real",
            telefono="+18098889999",
            estaciones=6,
            chatwoot_url="https://appchatwoot.lavapass.app/app/accounts/1/conversations/12",
        )
        assert ok is True
        req = mock_urlopen.call_args[0][0]
        cuerpo = req.data.decode("utf-8")
        assert "PROSPECTO FISCAL DGII DETECTADO" in cuerpo
        assert "e-CF" in cuerpo
        assert "#E01E5A" in cuerpo


def test_slack_notificar_traspaso():
    slack = NotificadorSlack("https://hooks.slack.com/services/FAKE/TEST/123")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ok = slack.notificar_traspaso(
            nombre="Cliente",
            telefono="+18097776655",
            motivo="Quiso hablar con un operador humano",
            chatwoot_url="https://appchatwoot.lavapass.app/app/accounts/1/conversations/13",
        )
        assert ok is True
        req = mock_urlopen.call_args[0][0]
        cuerpo = req.data.decode("utf-8")
        assert "Atención Humana Requerida" in cuerpo
        assert "operador humano" in cuerpo


def test_slack_error_de_red_no_rompe():
    slack = NotificadorSlack("https://hooks.slack.com/services/FAKE/TEST/123")

    with patch("urllib.request.urlopen", side_effect=Exception("Timeout en Slack")):
        ok = slack.notificar_demo(
            nombre="Juan",
            telefono="+18090000000",
            fecha_hora="2026-10-15 10:00 AM",
        )
        assert ok is False
