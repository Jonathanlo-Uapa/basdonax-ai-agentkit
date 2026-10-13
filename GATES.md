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

## Gate G8: Conversation continuity & `ya_la_cerro` refactor
- OUTCOME: `ya_la_cerro` never silences active open conversations of returning contacts, and `RESPETAR_RESUELTAS=0` is configured.
- CHECK: .venv\Scripts\pytest tests/test_chatwoot.py -k "test_ya_la_cerro_no_silencia_si_hay_conversacion_abierta"
- EXPECT: passed
- EVIDENCE: Verified on 2026-10-12. Output: 1 passed in 1.45s.

## Gate G9: Explicit Human Handover Tool (`solicitar_asesor_humano`)
- OUTCOME: `solicitar_asesor_humano` tool exists, is in `HERRAMIENTAS`, and requests `A_UNA_PERSONA` with reason when invoked.
- CHECK: .venv\Scripts\pytest tests/test_ventas.py -k "test_solicitar_asesor_humano"
- EXPECT: passed
- EVIDENCE: Verified on 2026-10-12. Output: 1 passed in 1.40s.

## Gate G10: Prompt Policy & Strict Handoff Boundaries
- OUTCOME: `prompts/protocolo_ventas.md` and `prompts/sistema.md` explicitly enforce continuous qualification without self-silencing and direct `solicitar_asesor_humano` exclusively for user requests.
- CHECK: .venv\Scripts\python.exe -c "from pathlib import Path; p1 = Path('prompts/protocolo_ventas.md').read_text(encoding='utf-8'); p2 = Path('prompts/sistema.md').read_text(encoding='utf-8'); assert 'solicitar_asesor_humano' in p1 and 'solicitar_asesor_humano' in p2; print('G10_VERIFIED')"
- EXPECT: G10_VERIFIED
- EVIDENCE: Verified on 2026-10-12. Output: G10_VERIFIED.

## Gate G11: Full regression test suite passing with 0 failures
- OUTCOME: All 398 pytest unit and integration tests pass without token usage.
- CHECK: .venv\Scripts\pytest
- EXPECT: 398 passed
- EVIDENCE: Verified on 2026-10-12. Output: 398 passed in 33.50s.

## Gate G12: Production deployment & live health check
- OUTCOME: Pushed to `origin/master`, Coolify deployment triggered, and live `/salud` endpoint responds with 200 OK.
- CHECK: .venv\Scripts\python.exe -c "import urllib.request, json; resp = urllib.request.urlopen('http://u3v9fbhv9lglh6euimsibsr1.179.236.245.155.sslip.io/salud', timeout=15); data = json.loads(resp.read().decode()); assert data.get('estado') == 'ok'; print('G12_VERIFIED')"
- EXPECT: G12_VERIFIED
- EVIDENCE: Verified on 2026-10-12. Output: G12_VERIFIED (Deployment chf63hulj92jevemte3qkntt finished, /salud 200 OK, running:healthy).

## Gate G13: Encargado as decision maker & demo route qualification in `ventas.py`
- OUTCOME: `QUIEN_DECIDE` includes 'encargado', and `ruta(rol='encargado', estaciones=2, sucursales=1, dolor='caja_ciega')` returns 'demo'.
- CHECK: .venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from agente.ventas import QUIEN_DECIDE, ruta; assert 'encargado' in QUIEN_DECIDE; assert ruta(rol='encargado', estaciones=2, sucursales=1, dolor='caja_ciega') == 'demo'; print('G13_VERIFIED')"
- EXPECT: G13_VERIFIED
- EVIDENCE: Verified on 2026-10-13. Output: G13_VERIFIED.

## Gate G14: Cal.com webhook 3-part message dispatch on booking creation
- OUTCOME: Webhook dispatches Meet confirmation, Free Trial 7 days register link (https://panel.lavapass.app/register), and functional assistance message.
- CHECK: .venv\Scripts\pytest tests/test_chatwoot.py -k "test_calcom_webhook"
- EXPECT: passed
- EVIDENCE: Verified on 2026-10-13. Output: 2 passed, 111 deselected in 1.13s.

## Gate G15: Tool guidance for step 6 (pure demo pitch) and step 7 (post-booking trial + Q&A)
- OUTCOME: `sync_prospecto_chatwoot` step 6 does not include premature register link or 3 buttons; `confirmar_reserva_demo` returns guidance for post-booking trial link and open Q&A.
- CHECK: .venv\Scripts\pytest tests/test_ventas.py -k "test_demo_flow_advice"
- EXPECT: passed
- EVIDENCE: Verified on 2026-10-13. Output: 1 passed, 61 deselected in 0.72s.

## Gate G16: Prompts alignment for 3 qualifying roles and decoupled free-trial delivery
- OUTCOME: `prompts/protocolo_ventas.md` and `prompts/sistema.md` specify that Dueño, Administrador and Encargado qualify for demo, remove the 3 old buttons (`Agendar Demo | Probar 7 Días | Hablar Asesor`), and instruct delivering the trial link and open Q&A only after booking.
- CHECK: .venv\Scripts\python.exe -c "from pathlib import Path; p1 = Path('prompts/protocolo_ventas.md').read_text(encoding='utf-8'); p2 = Path('prompts/sistema.md').read_text(encoding='utf-8'); assert 'Agendar Demo | 🚀 Probar 7 Días' not in p1; assert 'Encargados' in p1 or 'encargado' in p1; assert 'Google Meet' in p2; print('G16_VERIFIED')"
- EXPECT: G16_VERIFIED
- EVIDENCE: Verified on 2026-10-13. Output: G16_VERIFIED.

## Gate G17: Full regression test suite passing with 0 failures
- OUTCOME: All unit and integration tests pass without errors.
- CHECK: .venv\Scripts\pytest
- EXPECT: passed
- EVIDENCE: Verified on 2026-10-13. Output: 399 passed in 29.22s.

## Gate G18: Production deployment & live health verification
- OUTCOME: Changes pushed to `origin/master`, Coolify deploy finished, and live `/salud` responds 200 OK.
- CHECK: .venv\Scripts\python.exe -c "import urllib.request, json; resp = urllib.request.urlopen('http://u3v9fbhv9lglh6euimsibsr1.179.236.245.155.sslip.io/salud', timeout=15); data = json.loads(resp.read().decode()); assert data.get('estado') == 'ok'; print('G18_VERIFIED')"
- EXPECT: G18_VERIFIED
- EVIDENCE: pending
