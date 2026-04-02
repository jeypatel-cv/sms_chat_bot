# Render Checklist

This is the quickest path to get the VP Realty SMS pilot running on Render.

## Phase 1: Smoke Test

Use this first to prove the app deploys on Render before you connect Twilio or Google Sheets.

In the Render dashboard:
- Create a new **Web Service**
- Connect the GitHub repo: `jeypatel-cv/sms_chat_bot`
- Use the free plan
- Let Render read the repo root `render.yaml`

If you set the fields manually, use:
- Environment: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python production_app.py`
- Health Check Path: `/healthz`

Set these environment variables:
- `PYTHON_VERSION=3.13.5`
- `HOST=0.0.0.0`
- `PROPERTIES_CSV_PATH=data/properties.example.10.csv`
- `TWILIO_ALLOW_MOCK=true`
- `TWILIO_VALIDATE_REQUESTS=false`
- `CACHE_TTL_SECONDS=300`

After deploy, verify:
- `GET /healthz`
- `GET /demo`
- `POST /demo/message`

Suggested smoke-test messages:
- `123 Main St`
- `45 Cedar Park`
- `How much is rent?`

## Phase 2: Production-Like Setup

After the smoke test works, switch the service to Google Sheets and Twilio.

Before you do that:
- rotate the Twilio auth token because it was shared in chat
- store the new token only in Render environment variables

Remove:
- `PROPERTIES_CSV_PATH`

Add:
- `GOOGLE_SHEET_ID=1wcw6nsvP4trX28O1l6TdMklLciUXuRvXSYPTnScb_44`
- `GOOGLE_SHEET_TAB=Properties`
- `GOOGLE_SHEET_LOG_TAB=MessageLogs`
- `MESSAGE_LOG_TO_CONSOLE=true`
- `MESSAGE_LOG_TO_GOOGLE_SHEETS=false`
- `GOOGLE_APPLICATION_CREDENTIALS` if using a mounted JSON file
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` if you paste the service account JSON into Render secrets
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID`
- `PUBLIC_BASE_URL=https://YOUR-RENDER-URL`
- `TWILIO_VALIDATE_REQUESTS=true`
- `TWILIO_ALLOW_MOCK=false`

Then:
1. Share the Google Sheet with the service account email.
2. Point Twilio's inbound SMS webhook to `https://YOUR-RENDER-URL/twilio/sms`.
3. Send one test SMS from a verified number.

Note:
- console logging is on by default
- Google Sheets logging only turns on when `MESSAGE_LOG_TO_GOOGLE_SHEETS=true`

## Phase 3: Exact Production Setup Order

Use this order when you are ready to connect live SMS and live property data.

### Step 1: Rotate the Twilio token
- Log into Twilio.
- Generate a new auth token.
- Treat the old token as invalid.

### Step 2: Update Render secrets
In Render, add or update:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER=+12142064345`
- `PUBLIC_BASE_URL=https://vp-realty-sms-pilot.onrender.com`
- `TWILIO_VALIDATE_REQUESTS=true`
- `TWILIO_ALLOW_MOCK=false`

If you are staying on CSV for one more test round, keep:
- `PROPERTIES_CSV_PATH=data/properties.example.10.csv`

If you are switching to Google Sheets now, remove:
- `PROPERTIES_CSV_PATH`

And add:
- `GOOGLE_SHEET_ID=1wcw6nsvP4trX28O1l6TdMklLciUXuRvXSYPTnScb_44`
- `GOOGLE_SHEET_TAB=Properties`
- `GOOGLE_SHEET_LOG_TAB=MessageLogs`
- `MESSAGE_LOG_TO_CONSOLE=true`
- `MESSAGE_LOG_TO_GOOGLE_SHEETS=false`
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` or `GOOGLE_APPLICATION_CREDENTIALS`

### Step 3: Share the Google Sheet
- Share the sheet with the Google service account email that Render will use.
- Give it Viewer access.

### Step 4: Redeploy Render
- Save the environment variables.
- Trigger a redeploy if Render does not auto-deploy immediately.

### Step 5: Update Twilio
- Open the Twilio phone number settings.
- Set the inbound SMS webhook to:
  - `POST https://vp-realty-sms-pilot.onrender.com/twilio/sms`

### Step 6: Test the live SMS flow
- Text `123 Main St`
- Text `45 Cedar Park`
- Text `How much is rent?`
- Text `Can I speak to a human?`

## What Good Looks Like

- `/healthz` returns OK
- the demo endpoints still work
- Twilio accepts the webhook
- inbound SMS gets a reply
- the reply matches the right property
