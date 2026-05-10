# VP Realty Pilot Deployment and Test Runbook

Date: 2026-04-01

## Recommended Pilot Stack

- Python backend: `production_app.py`
- SMS provider: Twilio
- Property data: Google Sheets
- Hosting: Render Free for testing, then upgrade later if needed

Local and production should use the same backend code path:
- local starts through `server.py`, which only sets safe defaults
- production starts through `production_app.py`

Recommended host shape:
- a single web service with HTTPS
- environment variables for secrets
- one public webhook endpoint for Twilio

## What I can do in the repo

- build and maintain the backend service
- keep the property matching logic
- support Google Sheets or CSV fallback
- add Twilio webhook validation
- add Twilio outbound message sending
- write runbooks and setup docs
- help you test sample SMS flows

## What you need to provision

- a Twilio account and SMS-capable number
- a Google Sheet with property data
- a Google service account or cloud identity with Sheets read access
- a cloud host with HTTPS
- the production environment variables

## Deployment Flow

### 1. Prepare Google Sheets
Create a worksheet tab named `Properties` and use the LeasingSnapshot columns in `google-sheet-template.md`.
The app is now defaulted to this sheet ID:
- `1wcw6nsvP4trX28O1l6TdMklLciUXuRvXSYPTnScb_44`

Important:
- if you are using Apps Script logging, the script writes as the sheet owner
- keep a `MessageLogs` tab in the same spreadsheet for message records

### 2. Prepare Twilio
Configure the inbound SMS webhook to:
- `POST /twilio/sms`

Set up either:
- `TWILIO_FROM_NUMBER`, or
- `TWILIO_MESSAGING_SERVICE_SID`

### 3. Deploy the Python app
Deploy `production_app.py` as a long-running web service.

If you choose Render, you can use `render.yaml` or create a free web service manually.

Use:
- `PORT` from the host environment
- `HOST=0.0.0.0`
- `PUBLIC_BASE_URL` set to the public HTTPS URL

### 4. Configure environment variables
Minimum production variables:
- `GOOGLE_SHEET_ID`
- `GOOGLE_SHEET_TAB`
- `MESSAGE_LOG_TO_CONSOLE=true`
- `MESSAGE_LOG_TO_APPS_SCRIPT=true`
- `MESSAGE_LOG_APPS_SCRIPT_URL`
- `MESSAGE_LOG_APPS_SCRIPT_SECRET`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID`
- `TWILIO_VALIDATE_REQUESTS=true`
- `PUBLIC_BASE_URL`
- `CACHE_TTL_SECONDS`

### 5. Verify health
Open:
- `GET /healthz`

Expected response:
- `{"ok": true, "service": "vp-realty-sms-production"}`

## Testing Flow

### Local testing first
Before going live:
- run the app with CSV fallback
- send messages through the `/demo/message` endpoint
- verify exact match, partial street match, and follow-up behavior

### Twilio webhook test
Once deployed:
- send a real SMS to the Twilio number
- confirm Twilio forwards the inbound webhook to the backend
- confirm the backend validates the request
- confirm the outbound reply is sent through Twilio

### Test cases
Use these in order:
1. exact address match
2. partial street match
3. follow-up question with no address repeated
4. human handoff request
5. unknown property

### Expected behavior
- exact match: give the property answer
- partial match: suggest the property and ask what detail they want
- follow-up: stay on the last property
- human request: route to handoff message
- unknown property: ask for address, unit number, or property name

## Pilot Launch Checklist

- [ ] Google Sheet filled with 5 to 10 properties
- [ ] Apps Script web app is deployed and reachable
- [ ] cloud service deployed over HTTPS
- [ ] Twilio webhook points to the deployed URL
- [ ] webhook validation is enabled
- [ ] outbound SMS sending is working
- [ ] response logs are visible
- [ ] at least five real-world test prompts were verified

## Recommended Pilot Size

Keep the first live pilot small:
- 1 official phone number
- 5 to 10 properties
- 1 leasing contact for handoff
- 1 internal tester plus 1 business reviewer

## Rollout Order

1. internal-only test
2. limited live number test
3. staff review of logs and replies
4. wider pilot once response quality is stable

## Risks To Watch

- bad spreadsheet values
- webhook misconfiguration
- Twilio signature validation mismatch behind a proxy
- duplicate replies if outbound logic is called twice
- stale sheet cache

## Best Next Step

Deploy the backend to your host of choice, connect the Twilio number, and run the five test cases above before opening it to real customers.
