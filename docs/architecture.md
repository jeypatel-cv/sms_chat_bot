# VP Realty Production Architecture - Twilio + Google Sheets

Date: 2026-04-01

## 1. Goal

This document describes a production-ready path for the VP Realty SMS assistant using:
- `server.py` as the backend service
- Twilio for the official SMS phone number
- Google Sheets as the initial property data source

This is the practical next step after the local POC. The purpose is to keep the system simple enough to ship quickly, while giving the team a familiar place to edit property details.

## 2. High-Level Decision

Use Google Sheets as the editable source of truth for property data during the first production phase.

Use a cloud-hosted Python service to:
- receive Twilio webhooks
- read property rows from Google Sheets
- match the customer message to the right property
- generate the reply
- send the response back through Twilio

This keeps the business workflow simple and avoids forcing the team to edit JSON files or manage a full database too early.

## 3. Where `server.py` Runs

`server.py` should run in a cloud-hosted environment, not on a local laptop.

Good hosting choices:
- Render
- Railway
- Fly.io
- Google Cloud Run
- AWS ECS or App Runner
- Azure App Service

The best fit for a small Python service is usually a container-based host or a managed app platform.

## 4. System Components

### Twilio
- owns the official SMS number
- receives inbound SMS messages
- sends webhook requests to the Python backend
- sends outbound SMS replies using the Twilio API

### Python backend
- receives webhook requests from Twilio
- loads or refreshes property data from Google Sheets
- manages conversation state
- decides whether the message is an exact match, partial match, or follow-up
- creates the outgoing SMS response

### Google Sheets
- stores the editable property list
- allows business users to update rent, availability, dates, and other fields
- acts as the first production data source

### Optional cache
- keeps a short-lived local copy of sheet data
- reduces repeated API calls to Google Sheets
- improves response time

## 5. Request Flow

1. A customer texts the VP Realty phone number.
2. Twilio receives the SMS.
3. Twilio sends a webhook request to `server.py`.
4. `server.py` loads the latest property data from Google Sheets or from cache.
5. The backend matches the property and intent.
6. The backend generates the reply.
7. The backend sends the reply back to Twilio.
8. Twilio delivers the SMS to the customer.

## 6. Data Flow

### Property data flow
Google Sheet row -> Google Sheets API -> backend cache -> message matching -> SMS response

### Conversation data flow
Twilio inbound SMS -> backend session store -> reply generation -> Twilio outbound SMS

## 7. Google Sheets Structure

Recommended columns:
- property_id
- property_name
- street_address
- city
- state
- zip
- rent
- bedrooms
- bathrooms
- availability_status
- available_from
- description
- listing_id
- contact_owner
- notes

Optional columns:
- pet_policy
- parking
- square_feet
- deposit
- application_link
- showing_link

## 8. How the Backend Should Read Sheets

The backend should use the Google Sheets API with a service account.

Recommended pattern:
- store the sheet ID in an environment variable
- store the service account credentials securely
- fetch the full sheet on a schedule or cache refresh
- validate the rows before using them
- convert rows into internal property objects

Do not:
- expose the spreadsheet directly to the AI
- let the AI edit the sheet
- rely on manual copy-paste in production

## 9. Matching Logic

The backend should handle following cases:

### Exact match
Customer gives a full address, listing ID, or property name.

### Partial match
Customer gives a similar street address or partial street name.
In this case, the backend should reply:
- "I found this property: [name]. Do you want rent, availability, or bedroom details?"

### Follow-up match
Customer says "yes" or asks a follow-up question without repeating the address.
The backend should continue using the previously matched property.

### Next property question
If customer ask about another property, then backend should switch the context to another property, but still keep the previous property questions in the context.

## 10. Conversation State

Store minimal session state per phone number:
- last matched property ID
- last match type
- handoff flag
- timestamp of last message

For the first production version, this can be held in memory if the service is simple, but a shared store is better if multiple instances are deployed.

Recommended long-term options:
- Redis
- Postgres
- a lightweight session table in the database

## 11. AI Layer

For the production path, the AI layer can be:
- simple rule-based response generation at first
- an LLM-backed response layer later

Recommendation:
- keep the property lookup and business rules in backend code
- let the model generate only the final wording if needed
- never let the model directly decide what data source to trust

## 12. Security Requirements

- keep Twilio credentials in environment variables
- keep Google service account credentials secret
- validate incoming Twilio webhooks
- rate limit requests
- log every inbound and outbound message
- keep authorization and business rules in backend code
- never expose raw spreadsheet credentials to the browser or customer

## 13. Reliability Requirements

- cache Google Sheets data for a short period
- handle API failures gracefully
- fall back to the last known good copy if Sheets is temporarily unavailable
- return a short apology or human handoff message if data cannot be loaded
- keep response times low enough for SMS

## 14. Recommended Deployment Layout

### Service 1: SMS backend
- hosts `server.py`
- receives Twilio webhooks
- queries Google Sheets
- returns responses

### Service 2: Data source
- Google Sheets used by the team
- optionally mirrored into a database later

### Service 3: Logging and monitoring
- cloud logs
- Twilio message logs
- optional error tracking

## 15. Suggested Implementation Plan

### Phase 1
- move property data from JSON into Google Sheets
- update `server.py` to read from the Sheets API
- deploy `server.py` to a cloud host
- connect Twilio inbound SMS to the backend webhook

### Phase 2
- add caching
- add session persistence
- add admin validation for sheet rows
- add human handoff routing

### Phase 3
- migrate from Sheets to a database if needed
- keep Sheets as a friendly editing layer if the business wants it

## 16. Why This Is Better Than JSON

Google Sheets is better for production operations because:
- multiple team members can update it
- the business does not need to edit code
- it is easier to review and correct data
- it supports a fast operational workflow for leasing staff

JSON is still useful for local testing, but it is not ideal as the live source of truth.

## 17. Risks

- sheet formatting mistakes
- slow API responses if the backend reads Sheets on every message
- authentication mistakes with service account credentials
- duplicate or conflicting property rows
- multiple backend instances without shared session state

## 18. Best Next Step

Build a small production adapter for `server.py` that:
- reads from Google Sheets
- caches property rows
- receives Twilio webhooks
- sends SMS replies through Twilio

That gives VP Realty a clean bridge from POC to a real production pilot.
