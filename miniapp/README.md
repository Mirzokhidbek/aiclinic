# Mini App

Telegram Mini App for customers (and, from M6, staff). See the root [README](../README.md) for how to run it with the backend.

```bash
npm run dev        # http://localhost:5173 (needs the API on :8000)
npm run dev:link   # signed launch URL to open the app in a normal browser
npm run gen:api    # regenerate src/api/schema.d.ts from ../backend/openapi.json
npm run e2e        # Playwright against the running stack
```
