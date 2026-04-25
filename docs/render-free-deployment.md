# Render Free Deployment - VP Realty SMS Pilot

This is the recommended free-hosting path for testing the pilot.

## Why Render Free

- simple Python web service support
- public HTTPS URL
- easy webhook integration for Twilio
- good enough for a testing pilot

Important limitation:
- free web services spin down after 15 minutes of inactivity
- this is fine for testing, but not ideal for a real production rollout

## What to upload to Render

Use the repository with:
- `production_app.py`
- `requirements.txt`
- `render.yaml`

## Render service settings

If you create the service manually, use:
- Environment: Python
- Plan: Free
- Build Command: `pip install -r requirements.txt`
- Start Command: `python production_app.py`
- Health Check Path: `/healthz`
- Python Version: `3.13.5`

## Environment Variables

Set these in the Render dashboard:

- `GOOGLE_SHEET_ID=1wcw6nsvP4trX28O1l6TdMklLciUXuRvXSYPTnScb_44`
- `GOOGLE_SHEET_TAB=Properties`
- `PYTHON_VERSION=3.13.5`
- `MESSAGE_LOG_TO_CONSOLE=true`
- `MESSAGE_LOG_TO_APPS_SCRIPT=true`
- `MESSAGE_LOG_APPS_SCRIPT_URL`
- `MESSAGE_LOG_APPS_SCRIPT_SECRET`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID`
- `PUBLIC_BASE_URL`
- `TWILIO_VALIDATE_REQUESTS=true`
- `TWILIO_ALLOW_MOCK=false`

## Google Sheets Access

The backend reads property data from Google Sheets.
For message logging, it posts to the Apps Script web app.

## Twilio Webhook

Point your Twilio inbound SMS webhook to:

- `https://<your-render-url>/twilio/sms`

## Test Sequence

1. Open `https://<your-render-url>/healthz`
2. Send an exact property question
3. Send a partial street match
4. Send a follow-up question without the address
5. Send a human handoff request

## Recommendation

Use Render Free for internal testing and pilot validation only.
If the pilot gains traction, move to a paid service or a more stable host.
