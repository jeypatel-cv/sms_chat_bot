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
- `PROPERTIES_CSV_PATH=data/LeasingSnapshot - ChatBotClient.csv`
- `PROPERTIES_SOURCE_URL=` if you have a direct CSV or JSON export URL
- `TWILIO_ALLOW_MOCK=true`
- `TWILIO_VALIDATE_REQUESTS=false`
- `CACHE_TTL_SECONDS=300`

If the demo page looks empty, hard refresh the browser after the first deploy.

After deploy, verify:
- `GET /healthz`
- `GET /demo`
- `POST /demo/message`

Live web test URL:
- `https://vp-realty-sms-pilot.onrender.com/demo`

Suggested smoke-test messages:
- `1913 Ridge Creek Ln`
- `How much is rent?`
- `Is it available?`
- `How many bedrooms and bathrooms does this property have?`
- `When is it available from?`
- `Who should I contact for details?`

## Phase 2: Production-Like Setup

After the smoke test works, switch the service to Twilio and message logging.

Before you do that:
- rotate the Twilio auth token because it was shared in chat
- store the new token only in Render environment variables

Keep `PROPERTIES_CSV_PATH` if you want a CSV fallback.
If you use a raw remote export, you can still set `PROPERTIES_SOURCE_URL`.

Add:
- `GOOGLE_SHEET_ID=18b9gxA8GoC_-cpmjr-nG9ze2wG5NAfWWxhlg5MCfM7k`
- `GOOGLE_SHEET_TAB=ChatBotClient`
- `MESSAGE_LOG_TO_CONSOLE=true`
- `MESSAGE_LOG_TO_APPS_SCRIPT=true`
- `MESSAGE_LOG_APPS_SCRIPT_URL=https://script.google.com/macros/s/.../exec`
- `MESSAGE_LOG_APPS_SCRIPT_SECRET=your-shared-secret`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID`
- `PUBLIC_BASE_URL=https://vp-realty-sms-pilot.onrender.com`
- `TWILIO_VALIDATE_REQUESTS=true`
- `TWILIO_ALLOW_MOCK=false`

Then:
1. Deploy the Apps Script web app with `Execute as: Me` and access set to `Anyone`.
2. Point Twilio's inbound SMS webhook to `https://YOUR-RENDER-URL/twilio/sms`.
3. Send one test SMS from a verified number.

Note:
- console logging is on by default
- Apps Script logging only turns on when `MESSAGE_LOG_TO_APPS_SCRIPT=true`

## Live SMS Settings

### Render
For real SMS testing, keep these in Render:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER=+12142064345`
- `PUBLIC_BASE_URL=https://vp-realty-sms-pilot.onrender.com`
- `TWILIO_VALIDATE_REQUESTS=true`
- `TWILIO_ALLOW_MOCK=false`

If you are still using CSV for now, keep:
- `PROPERTIES_CSV_PATH=data/LeasingSnapshot - ChatBotClient.csv`

If you want Google Sheets first with CSV fallback, keep both `GOOGLE_SHEET_ID` and `PROPERTIES_CSV_PATH`.

### Twilio
In the Twilio Console, on the phone number page:
- Messaging -> A Message Comes In -> `Webhook`
- URL -> `https://vp-realty-sms-pilot.onrender.com/twilio/sms`
- Method -> `POST`
- Voice -> A Call Comes In -> `Webhook`
- URL -> `https://vp-realty-sms-pilot.onrender.com/twilio/voice`
- Method -> `POST`

Use the approved sender number in `TWILIO_FROM_NUMBER`.
Do not use Voice or Studio for the inbound SMS route unless you intentionally want to change the flow.
Voice calls are logged with `in-CALL` and `out-SMS-C` directions.

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
- `PROPERTIES_CSV_PATH=data/LeasingSnapshot - ChatBotClient.csv`

If you have a raw remote export, you can use:
- `PROPERTIES_SOURCE_URL=https://...`
- `PROPERTIES_SOURCE_FORMAT=csv` or `json`

If you are switching to Google Sheets now, keep `PROPERTIES_CSV_PATH` only if you want CSV fallback.

And add:
- `GOOGLE_SHEET_ID=18b9gxA8GoC_-cpmjr-nG9ze2wG5NAfWWxhlg5MCfM7k`
- `GOOGLE_SHEET_TAB=ChatBotClient`
- `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_APPLICATION_CREDENTIALS_JSON`
- `MESSAGE_LOG_TO_CONSOLE=true`
- `MESSAGE_LOG_TO_APPS_SCRIPT=true`
- `MESSAGE_LOG_APPS_SCRIPT_URL=https://script.google.com/macros/s/.../exec`
- `MESSAGE_LOG_APPS_SCRIPT_SECRET=your-shared-secret`

### Step 3: Share the Google Sheet
- Share the sheet with your Google account, since Apps Script writes as the owner.

### Step 4: Redeploy Render
- Save the environment variables.
- Trigger a redeploy if Render does not auto-deploy immediately.

### Step 5: Update Twilio
- Open the Twilio phone number settings.
- Set the inbound SMS webhook to:
  - `POST https://vp-realty-sms-pilot.onrender.com/twilio/sms`

### Step 6: Test the live SMS flow
- Text `1913 Ridge Creek Ln`
- Text `How much is rent?`
- Text `Is it available?`
- Text `How many bedrooms and bathrooms does this property have?`
- Text `When is it available from?`
- Text `Who should I contact for details?`
- Text `Can I speak to a human?`

## What Good Looks Like

- `/healthz` returns OK
- the demo endpoints still work
- Twilio accepts the webhook
- inbound SMS gets a reply
- the reply matches the right property
