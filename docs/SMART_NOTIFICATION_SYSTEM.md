# EstateIQ Smart Notification System

EstateIQ SNS adds durable notifications and rule routing to the existing FastAPI, SQLite, alert, and work-order flows. It is additive: existing alert lifecycle and role authentication remain in place.

## Current implementation

- SQLite tables are added idempotently to the existing `ESTATEIQ_DB_PATH` database: rules, notifications, outbox, deliveries, rule cooldown state, Telegram link tokens, and Telegram channel links.
- A new alert publishes one `alert.created` event after the alert is created. Existing alert deduplication prevents repeat event creation for subsequent readings.
- Work-order notification calls persist to SNS while retaining the existing in-memory engine for compatibility.
- In-app notification reads and lifecycle actions are scoped to the authenticated user email. SNS endpoints require an actual Bearer token (they do not use EstateIQ's legacy anonymous demo-user fallback).
- Configurable rules support event type, JSON field conditions, AND/OR, severity, recipient roles/emails, in-app or Telegram channel, and cooldown. Notifications are deduplicated per recipient and rule/event key.
- Telegram linking uses a random single-use token with a 10-minute expiry; the database stores only its SHA-256 hash. The worker polls Telegram for `/link` commands, so local demos do not need a public webhook URL. Do not run webhook updates and polling for the same bot at the same time.
- Telegram delivery is asynchronous through the SQLite outbox. Run `python -m src.services.sns_worker` in a separate process after configuring credentials. The worker uses bounded retries and records each attempt. Tests should mock the Telegram API; they must never send real messages.
- The web dashboard has a Smart Notifications tab for notification history, summary counts, rule listing/toggles, rule creation, Telegram link state, and delivery attempts.

## API

All application routes are under `/api/v1/sns` and require a Bearer token.

- `GET /overview`
- `GET /notifications?unread_only=false&limit=50&offset=0`
- `GET /notifications/{id}`
- `POST /notifications/{id}/read`
- `POST /notifications/{id}/acknowledge`
- `POST /notifications/{id}/resolve`
- `GET|POST /rules`, `PUT|DELETE /rules/{id}`, `POST /rules/{id}/test|enable|disable`
- `GET /deliveries`, `POST /deliveries/{id}/retry`
- `GET /integrations/telegram`, `POST /integrations/telegram/link|unlink`
- `POST /integrations/telegram/webhook` (Telegram secret header required)

The built-in alert routing rule is protected from deletion and sends to operations and administrative roles. Custom rules are managed by authorized administrative roles. Role permissions are enforced in the backend.

## Telegram setup

1. Create a fresh bot token with BotFather and place it in the ignored local `.env` as `TELEGRAM_BOT_TOKEN=...`. Never commit the token.
2. Start EstateIQ and run `python -m src.services.sns_worker` in a separate terminal. Keep the worker running; it polls for account-link commands and sends queued notifications.
3. Sign into EstateIQ, open **Notifications**, select **Link Telegram**, and send `/link <one-time-token>` to your bot before the token expires.
4. Create or update an alert rule with the Telegram channel enabled. In-app notifications remain available too.

For hosted webhook mode, expose the webhook endpoint over HTTPS and register it with Telegram. Do not use webhook updates and polling simultaneously. If the bot previously had a webhook configured, remove it before starting the polling worker.

Telegram delivery is not confirmed until the Bot API accepts the send request. A queued message is not reported as delivered. A link token is shown only once to its authenticated owner.

## Known boundaries

- The initial rule engine evaluates event fields at event arrival; it does not yet implement time-window aggregation or consecutive-reading windows. The DIF and alert services remain responsible for temporal confirmation and recovery.
- The initial dashboard provides practical rule creation and enable/disable controls, not a visual multi-condition builder or recipient administration console.
- The single-campus app continues to use its existing facility and identity model. The SNS schema carries facility IDs so future multi-facility routing can be added, but full cross-facility authorization is not implemented here.
- Existing login and role-switch behavior predates SNS. SNS endpoints require bearer tokens, but any legacy weaknesses in the broader authentication flow remain a separate security task.
- Telegram webhook registration must be configured with Telegram; the application does not register itself automatically.
