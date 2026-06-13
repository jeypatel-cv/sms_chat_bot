# Human Reply Upgrades

Date: 2026-06-13

This note captures places where the bot is technically answering, but the reply can sound more natural, contextual, and useful.

## 1. Separate buyer requests from rental requests

Example inbound:
- `We're looking to buy (not rent) in Allen/Frisco/Plano-ideally a fixer that needs work. Do you have anything like that available or coming up soon? If so, what's the address?`

Current behavior:
- The bot returns a rental area list, which ignores the buyer intent.

Better reply shape:
- `Thanks. This sounds like a buying request, not a rental search. I can connect you with the right team if you want to share the area or address.`

Why this helps:
- It acknowledges the mismatch instead of pretending the request was about rentals.

## 2. Make commercial / off-market requests get a different fallback

Example inbound:
- `I have off market Commercial lot available at 1530 E Lamar Street, Sherman, TX 75090 ... want more details?`

Current behavior:
- The bot falls back to the standard rental clarification line.

Better reply shape:
- `Thanks. This looks like a commercial or off-market request, not a rental listing. Send the address and I can route it to the right person.`

Why this helps:
- It avoids a generic rental-only question when the user is clearly outside rental intent.

## 3. Make tour and appointment messages feel aware of the ask

Example inbound:
- `Hi, my name is Sydney Gilliam and I'm interested in touring 2825 Dawn Springs Dr house. I've reached out twice to setup a tour but haven't heard back`

Current behavior:
- The bot often jumps straight to a property summary or a property mismatch.

Better reply shape:
- `Thanks for the tour request. I’m checking that home now. If you want, I can also connect you with the leasing team for the fastest follow-up.`

Why this helps:
- It sounds like a person responding to a tour request, not a lookup engine.

## 4. Answer availability with a direct yes/no first

Example inbound:
- `Is 359 Timber Creek Lane Frisco still available for lease?`

Better reply shape:
- `Yes, 359 Timber Creek Lane is still available. It’s listed at $3,545. If you want, I can also share bed/bath details or the leasing contact.`

Why this helps:
- Users asking `is it available?` want the answer immediately.
- A direct first sentence reduces friction.

## 5. Make on-site code requests more urgent and direct

Example inbound:
- `I'm at 5928 mustang creek dr waiting on a code to view the property`

Current behavior:
- The bot gives the manager handoff, but it can feel too generic.

Better reply shape:
- `I can’t provide the entry code by text. Since you’re at the property, please contact the manager for this home right away.`

Why this helps:
- It matches the urgency of someone standing at the door.

## 6. Be smarter when the user says only `Is this available`

Example inbound:
- `Is this available`

Current behavior:
- The bot falls back to the broad area clarification line.

Better reply shape:
- `Which property are you asking about? If you already sent the address earlier, send it again and I’ll check it right away.`

Why this helps:
- It keeps the conversation moving without sounding like a canned support script.

## 7. Reduce repetitive footer language

Current pattern:
- `For more details, call the leasing team at 972-591-8075.`

Why it feels robotic:
- It appears on nearly every response, even when the answer is already sufficient.

Better pattern:
- Keep the footer when the bot is handing off or missing detail.
- Skip it when the bot already gave a complete direct answer.

Suggested rewrite:
- `If you want more details, I can connect you with the leasing team.`

## 8. When a property is found, lead with the useful fact

Example inbound:
- `1001 Marigold Street Princeton, TX 75407`

Current behavior:
- The bot may ask a menu-style follow-up like `Do you want rent, availability, or bedroom details?`

Better reply shape:
- `I found 1001 Marigold Street in Princeton. It’s currently available. If you want, I can share rent, bed/bath count, or manager contact.`

Why this helps:
- It feels more concierge-like and less like a form response.

## Recommended Next Pass

If we want the bot to sound more human without making routing risky, the best sequence is:

1. Add buyer-vs-rental intent handling.
2. Add commercial/off-market intent handling.
3. Make availability answers direct.
4. Make tour/appointment replies acknowledge the request first.
5. Reduce repeated footer wording when the answer is already complete.

## Implementation Plan

### Phase 1: Low-risk wording improvements

These changes improve tone without changing core routing.

1. Shorten the generic fallback language.
- Replace repeated wording like `Which area are you looking to rent...` with a more flexible line such as `Which property or area are you asking about?`
- Keep the leasing contact footer only when the bot truly needs a handoff.

2. Make direct answers less template-like.
- When availability, rent, or bed/bath data is known, answer in one sentence first.
- Add the contact footer only after the useful fact.

3. Improve the `Is this available` response.
- If there is a session property, answer from that property.
- If there is no session property, ask for the address or area in a shorter, more conversational way.

### Phase 2: Intent-aware routing

These changes improve the bot’s ability to choose the right response path.

1. Add a buyer-intent branch.
- Detect phrases like `buy`, `purchase`, `sale`, `seller`, `owner would take`, and `closing timeline`.
- Route those messages away from rental area lists.

2. Add a commercial / off-market branch.
- Detect phrases like `commercial`, `lot`, `off market`, `investment`, and `development`.
- Respond that the bot is tuned for rental listings and offer a human handoff.

3. Make tour and appointment requests explicit.
- Detect words like `tour`, `showing`, `appointment`, `viewing`, and `schedule`.
- Reply with a confirmation-style line before any property detail.

### Phase 3: Response polish

These changes make the conversation sound more human when the property is found.

1. Property found reply.
- Lead with the matched property name and one useful fact.
- Follow with optional next steps, not a menu-style interrogation.

2. Entry-code request reply.
- Keep the manager handoff.
- Add urgency when the message indicates the person is already at the property.

3. Reduce footer repetition.
- If the reply already gives a complete answer, omit the extra footer.
- If the reply is partial or a handoff, keep the footer.

### Phase 4: Regression checks

Add smoke-test cases or log-based checks for:

1. Buyer request example.
- `We're looking to buy (not rent) in Allen/Frisco/Plano...`

2. Commercial/off-market example.
- `I have off market Commercial lot available...`

3. Tour request example.
- `I'm interested in touring 2825 Dawn Springs Dr...`

4. Availability example.
- `Is 359 Timber Creek Lane Frisco still available for lease?`

5. On-site code example.
- `I'm at 5928 mustang creek dr waiting on a code...`

### Suggested order of execution

1. Wording cleanup.
2. Buyer/commercial intent detection.
3. Tour and availability response polish.
4. Entry-code urgency handling.
5. Add or update regression tests.
