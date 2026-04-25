# Production Setup - Twilio + Google Sheets

For a step-by-step launch plan, see [pilot-deployment-runbook.md](pilot-deployment-runbook.md).

## What I can do

- build and maintain the Python backend code
- wire SMS webhook handling
- implement matching logic for exact, partial, and follow-up property lookup
- add cache behavior and health checks
- create the deployment-ready configuration files
- help you validate sample messages before launch

## What you need to do

### 1. Create the Google Sheet
Use the columns described in [google-sheet-template.md](google-sheet-template.md).
The current pilot sheet ID is already wired as the default in the app:
- `1wcw6nsvP4trX28O1l6TdMklLciUXuRvXSYPTnScb_44`

### 2. Create the message log endpoint
Create a Google Apps Script web app bound to the Sheet.
Set it to execute as you and allow access to `Anyone`.
Use it as the message log sink instead of the Google Sheets API.

### 3. Choose a cloud host
Deploy the Python app to a cloud environment such as Render, Fly.io, Railway, Cloud Run, or App Service.
For the free testing pilot, Render Free is a good fit.

See [render-free-deployment.md](render-free-deployment.md) and [render.yaml](render.yaml).

### 4. Configure environment variables
Set:
- `GOOGLE_SHEET_ID` if you want to override the default sheet ID
- `GOOGLE_SHEET_TAB`
- `PYTHON_VERSION=3.13.5` if you want to pin the runtime on Render
- `MESSAGE_LOG_TO_CONSOLE=true`
- `MESSAGE_LOG_TO_APPS_SCRIPT=true`
- `MESSAGE_LOG_APPS_SCRIPT_URL`
- `MESSAGE_LOG_APPS_SCRIPT_SECRET`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID`
- `PUBLIC_BASE_URL`
- `TWILIO_VALIDATE_REQUESTS=true`
- `PORT`

### 5. Connect Twilio
Point Twilio's inbound SMS webhook to:
- `POST /twilio/sms`

The backend validates incoming Twilio requests using the `X-Twilio-Signature` header and then sends the reply through the Twilio REST API.

### 6. Install dependencies
Run:

```powershell
pip install -r requirements.txt
```

### 7. Verify with a test message
Send a text and confirm the webhook returns a TwiML response.

If credentials are configured, the backend will send the outgoing SMS through Twilio. If not, the app can still run in mock mode for local testing.

## Local fallback for testing

If you do not have Sheets ready yet, you can use:
- `PROPERTIES_CSV_PATH=...`

That lets you test the production app against a CSV file first.
