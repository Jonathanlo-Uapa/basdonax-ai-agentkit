# Gates: Cal.com Deployment & 24/7 Slack Notifications for LavaPass

OWNS: src/agente/slack.py, src/agente/config.py, src/agente/web/webhook.py, src/agente/herramientas.py, tests/test_slack.py, .env.example, README.md, AGENTS.md

Scope: Deploy self-hosted Cal.com in Coolify and equip 24/7 AI Agent with executive Slack notification cards for demos, free trials, DGII alerts, and escalations.

- [ ] G1: Slack Notifier module implemented using standard library urllib and passes unit tests.
  CHECK: .venv\Scripts\pytest.exe tests/test_slack.py
  EXPECT: 1 passed
  EVIDENCE: pending

- [ ] G2: Full test suite passes with zero regressions across agent, sales funnel, and webhooks.
  CHECK: .venv\Scripts\pytest.exe
  EXPECT: passed
  EVIDENCE: pending

- [ ] G3: Cal.com Docker Compose stack deployed and healthy in Coolify project Cal.com.
  EVIDENCE: pending

- [ ] G4: Slack Incoming Webhook configured in production container and verified delivering rich alert cards to #lavapass-ai-notifications.
  EVIDENCE: pending
