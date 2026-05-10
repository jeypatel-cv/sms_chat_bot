# Problem Logs

Last updated: 2026-04-29

## Open Problems

- None known right now.

## Open Improvements

### Weekly message log rotation in Apps Script
- Goal: automatically archive the current `MessageLog` tab every Sunday night in `America/Chicago`, rename it to `MessageLogYY-MM-DD`, and create a fresh `MessageLog` tab for the next week.
- Preferred place to implement: the Google Apps Script project bound to the spreadsheet.
- Impact: no Render app changes should be needed if the rotation happens in Apps Script.
- Benefit: removes manual log cleanup and keeps weekly logs organized in one spreadsheet.

### Rename local launcher file
- Current name: `server.py`
- Future name to consider: `local_app.py`
- Reason: the current name is too generic for a local testing launcher and is easy to confuse with the production server.

## Fixed Problems

### 1. Unrelated property questions could inherit the previous session property
- Symptom: a follow-up like `How much is rent for Maple Ridge Apartments?` could get answered from the last property in the conversation even when that property was not explicitly mentioned in the current message.
- Cause: the session fallback in `find_property()` reused `session["property_id"]` too broadly after no fresh match was found.
- Fix: narrowed the session fallback so it only applies to clear follow-up questions, not explicit property mentions.
- Status: fixed in `production_app.py`.

### 2. Complaint-like replies were not routed to human handoff
- Symptom: messages like `I have called a number of times now` and `the return messages seem automated` still got the area/budget clarification prompt.
- Cause: the handoff detector only recognized a few exact words such as `human` and `agent`.
- Fix: broadened the existing handoff keyword check to catch complaint and callback language.
- Status: fixed in `production_app.py`.

### 3. LeasingSnapshot contact info needed parsing
- Symptom: if the sheet exported contact information as a single combined field, the bot could lose the contact name, email, or phone fallback.
- Cause: `google-sheet-template.md` originally reflected the older split-contact layout rather than the new `contact_info` field.
- Fix: updated the template and parser to accept `contact_info` and split it into manager name, email, and phone when present.
- Status: fixed in `docs/google-sheet-template.md`.

### 4. City plus budget queries could ignore the budget
- Symptom: messages like `under 2000 in Plano` could return the city list without filtering by budget.
- Cause: the reply flow checked city matches before combining city and budget filters.
- Fix: added a combined city-plus-budget branch so those requests return the correct filtered list.
- Status: fixed in `production_app.py`.

### 5. Numeric follow-ups could be misread as a new property reference
- Symptom: short SMS replies containing numbers, such as `2 bed` or `2 bath`, could be treated as a fresh property reference instead of a follow-up to the current property.
- Cause: `looks_like_new_property_reference()` treated any 2+ digit text as a new address-like reference.
- Fix: narrowed the rule so it only fires for address-like patterns or unit/suite references.
- Status: fixed in `production_app.py`.

### 6. Unsupported property questions were answered like they were known facts
- Symptom: messages such as `What is the application fee?` were routed to a manager contact reply instead of a clear "not in data yet" or handoff response.
- Evidence: local runtime log in `tmp-server.out.txt` showed `What is the application fee?` returning a contact-style reply for the matched property.
- Cause: `answer_property_question()` fell through to a generic contact reply for any unrecognized question.
- Fix: changed the fallback to say the current property data does not contain that detail and offer leasing handoff instead.
- Status: fixed in `production_app.py`.

## Debug Notes

- If a wrong reply appears again, check whether the message was routed through `property_qna`, `area_list`, `budget_list`, or `clarify_property`.
- If you need a full trace, inspect the last entries in `self.history` and the Render logs together.
