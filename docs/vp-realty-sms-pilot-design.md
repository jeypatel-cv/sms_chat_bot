# VP Realty SMS Pilot Design

Date: 2026-03-31

## 1. Purpose

This document defines the VP Realty SMS pilot as a custom proof of concept for SMS-based property conversations.

The goal is to let a customer text the official VP Realty phone number, receive AI-generated answers about property information, and continue a natural back-and-forth conversation using the same backend logic in local testing and production.

## 2. Why This Approach

This pilot is built as a custom stack because it gives us:
- full control over the matching logic
- one shared code path for local and production testing
- easy access to the property data source
- a clean path to expand into booking later

## 3. POC Scope

### In scope
- inbound SMS to the official VP Realty number
- AI-generated replies to basic property questions
- property data lookup from a trusted backend source
- conversation context across multiple SMS messages
- human handoff when the AI is uncertain
- logging of messages and key actions

### Out of scope
- full property management replacement
- lease signing
- payment processing
- unrestricted backend/database access
- free-form property negotiation
- autonomous booking without validation

## 4. POC Goal

Prove that VP Realty can use a custom pilot to:
- answer property questions quickly
- reduce manual responses for repetitive inquiries
- maintain a professional customer experience on SMS
- create a path toward booking viewings later

## 5. Assumptions

This design assumes:
- VP Realty has or can obtain a business SMS number
- VP Realty has a property source of truth in a tabular source such as Google Sheets or a CSV export
- the backend service can read the source and apply business rules consistently
- a small number of property records will be enough for the first test

## 6. Target POC Experience

### Example conversation
Customer: "Is the apartment at 123 Main St available?"

Assistant: "Yes, it is currently available. It has 2 bedrooms, 2 bathrooms, and rent starts at $1,850. Would you like the available-from date too?"

Customer: "Yes"

Assistant: "It is available from April 15. If you'd like, I can also help with a showing request."

This POC should feel:
- fast
- accurate
- friendly
- short enough for SMS
- helpful enough to reduce human back-and-forth

## 7. Proposed Architecture

### Custom pilot
Use Twilio for the official SMS number, a Python backend for the conversation logic, and a tabular property source for the initial property data.

### Logical flow
1. Customer sends SMS to the official number.
2. Twilio forwards the message to the backend webhook.
3. The backend loads the property data from the configured data source.
4. The backend matches the property and intent.
5. The backend generates the reply.
6. Twilio sends the reply back by SMS.
7. Conversation state is retained for follow-up questions.
8. If needed, the conversation is escalated to a human.

### Design principle
The backend should be the conversation and workflow layer.
VP Realty backend data should remain the source of truth.

## 8. Data Model for the POC

The POC only needs a small, clean property dataset.

### Minimum property fields
- property ID
- property name
- full address
- unit number or unit ID
- rent
- bedroom count
- bathroom count
- availability status
- available-from date
- short description
- contact or handoff owner

### Optional fields
- pet policy
- parking
- square footage
- deposit
- application link
- showing link

## 9. Conversation Design

### Supported intents for POC
- check availability
- ask rent or pricing
- ask bedroom/bathroom count
- ask move-in date
- ask for more property details
- ask whether the listing is still active

### Conversation rules
- one question at a time when possible
- keep replies concise for SMS
- do not guess when data is missing
- clarify the property if the customer is ambiguous
- escalate if the request is not confidently answerable

### Example clarification
If a customer says "Is it available?" and no property is referenced:
- ask for the address, unit number, or property name

## 10. Human Handoff

The POC should include a simple human escalation path.

Escalate when:
- the property cannot be identified
- the data is missing or inconsistent
- the customer asks for a policy or situation outside the POC
- the model confidence is low
- the customer explicitly asks for a human

Escalation options:
- notify a leasing team member
- send the conversation to an inbox
- tag the conversation for follow-up

## 11. Integration Design

### What must be integrated
- SMS provider or phone-number layer
- backend property source

### Integration approach
Start with a small tabular source and keep the backend logic responsible for property lookup, response generation, and handoff.

### Recommended integration order
1. confirm the source of truth for property data
2. map the fields required for the POC
3. load a small test set
4. validate the reply accuracy
5. test human handoff
6. extend to more properties after success

## 12. POC Setup Steps

### Step 1: Define the test dataset
Choose 5 to 10 properties for the first POC.

### Step 2: Prepare the source data
Make sure the test data contains:
- address
- rent
- rooms
- availability
- available-from date

### Step 3: Configure the backend behavior
Set up the assistant behavior for:
- SMS channel
- conversation tone
- approved property fields
- escalation path
- basic FAQ handling

### Step 4: Connect data
Connect the backend to the chosen tabular source of truth.

### Step 5: Test common questions
Run scripted SMS tests for:
- availability
- pricing
- room count
- availability date
- follow-up clarification

### Step 6: Review and tune
Adjust response wording, escalation rules, and data mappings.

## 13. Testing Plan

### Functional tests
- customer texts official number
- assistant answers availability correctly
- assistant answers rent correctly
- assistant answers room count correctly
- assistant asks for clarification when needed
- assistant escalates when uncertain

### Quality checks
- response accuracy
- response speed
- SMS length
- conversation clarity
- handoff behavior

### Success threshold
The POC is acceptable if the assistant can answer the core property questions with consistent accuracy and a human can step in cleanly when needed.

## 14. Success Metrics

Measure the POC by:
- percentage of questions answered correctly
- number of conversations resolved without human intervention
- average response time
- number of successful clarifications
- number of successful handoffs

## 15. Risks

- data quality issues in the source system
- ambiguity when customers do not mention an address, unit number, or property name
- over-automation if escalation is not tuned well
- Twilio webhook configuration mistakes
- Google Sheets formatting or permission issues

## 16. Recommended MVP Decision

For the quickest and least risky POC:
- use the custom Twilio + Google Sheets stack
- keep the first dataset small
- start with read-only property questions only
- add viewings only after the answer quality is proven

## 17. Phase 2 Expansion

After the POC works, expand into:
- available viewing slot discovery
- showing requests
- booking confirmation
- reminder messages
- booking changes or cancellations
- lead qualification

## 18. Open Questions

- Which property system is the source of truth?
- Should the property data stay in Google Sheets or move to a database later?
- Who receives human handoff alerts?
- What is the exact SMS number and sending setup?
- What properties will be used in the first test set?

## 19. Current Working Data Set

For the current pilot, the working local test data is the LeasingSnapshot CSV:
- `data/LeasingSnapshot - ChatBotClient.csv`

That file is used to keep local testing aligned with server-side testing.
