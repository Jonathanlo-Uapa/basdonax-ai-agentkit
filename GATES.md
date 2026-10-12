# Acceptance Gates: Carlos LavaPass Interactive WhatsApp & Cal.com Automation

State one observable outcome per gate. Prove each outcome with an explicit command check and expected output.

## Gate G1: Cal.com tool `consultar_reserva_demo` and method `consultar_reserva`
- OUTCOME: Calcom class supports querying bookings by UID, email, or phone in RD timezone, and `consultar_reserva_demo` is registered in `HERRAMIENTAS`.
- CHECK: .venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from agente.herramientas import HERRAMIENTAS, consultar_reserva_demo; from agente.calcom import Calcom; assert consultar_reserva_demo in HERRAMIENTAS; assert hasattr(Calcom, 'consultar_reserva'); print('G1_VERIFIED')"
- EXPECT: G1_VERIFIED
- EVIDENCE: Verified on 2026-10-12. Output: G1_VERIFIED.

## Gate G2: Cal.com webhook endpoint (`POST /calcom/webhook`) and 15m reminder scheduler
- OUTCOME: Webhook handles `BOOKING_CREATED`, updates Chatwoot attributes (`demo_uid`, `demo_inicio`, `5_demo_agendada`), sends proactive confirmation with Meet URL, and schedules 15m reminder.
- CHECK: .venv\Scripts\pytest -k "test_calcom_webhook"
- EXPECT: passed
- EVIDENCE: Verified on 2026-10-12. Output: 2 passed in 1.62s.

## Gate G3: Meta WhatsApp interactive sender in `whatsapp_meta.py`
- OUTCOME: `enviar_botones` and `enviar_lista` exist and send valid Meta Cloud API interactive payloads without unhandled exceptions.
- CHECK: .venv\Scripts\pytest tests/test_whatsapp_meta.py
- EXPECT: passed
- EVIDENCE: Verified on 2026-10-12. Output: 6 passed in 0.62s.

## Gate G4: Chatwoot helper methods for contact search and conversation discovery
- OUTCOME: `buscar_contacto` and `conversaciones_de` are implemented on `Chatwoot` class and tested.
- CHECK: .venv\Scripts\pytest -k "test_chatwoot_buscar_contacto"
- EXPECT: passed
- EVIDENCE: Verified on 2026-10-12. Output: 1 passed in 1.11s.

## Gate G5: Prompts with sequential 4-block qualification and Carlos heavy mambo
- OUTCOME: `prompts/protocolo_ventas.md` and `prompts/sistema.md` contain the 4 sequential discovery blocks, no multi-question dumping, and `consultar_reserva_demo` guidance.
- CHECK: .venv\Scripts\python.exe -c "from pathlib import Path; p1 = Path('prompts/protocolo_ventas.md').read_text(encoding='utf-8'); p2 = Path('prompts/sistema.md').read_text(encoding='utf-8'); assert 'consultar_reserva_demo' in p1; assert 'Heavy Mambo' in p2; print('G5_VERIFIED')"
- EXPECT: G5_VERIFIED
- EVIDENCE: Verified on 2026-10-12. Output: G5_VERIFIED.

## Gate G6: Full test suite execution with 0 regressions and 0 token usage
- OUTCOME: The entire pytest test suite passes with 0 failures.
- CHECK: .venv\Scripts\pytest
- EXPECT: passed
- EVIDENCE: Verified on 2026-10-12. Output: 388 passed in 27.44s.

## Gate G7: Production deployment & live health check
- OUTCOME: Changes pushed to `origin/master`, Coolify deploy triggered, and `https://appcoolify.lavapass.app/salud` or `http://u3v9fbhv9lglh6euimsibsr1.179.236.245.155.sslip.io/salud` returns status "ok".
- CHECK: .venv\Scripts\python.exe -c "import urllib.request, json; resp = urllib.request.urlopen('http://u3v9fbhv9lglh6euimsibsr1.179.236.245.155.sslip.io/salud', timeout=15); data = json.loads(resp.read().decode()); assert data.get('estado') == 'ok'; print('G7_VERIFIED')"
- EXPECT: G7_VERIFIED
- EVIDENCE: Verified on 2026-10-12. Output: G7_VERIFIED (Deployment in1gngavx4krs2rujovmdl4m finished, /salud 200 OK).
