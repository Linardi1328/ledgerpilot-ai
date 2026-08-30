from __future__ import annotations

from ledgerpilot.api.app import create_app

# Vercel imports this module-level ASGI application. Configuration stays environment-driven;
# migrations and synthetic feature-test seeding are explicit deployment steps and never run here.
app = create_app()
