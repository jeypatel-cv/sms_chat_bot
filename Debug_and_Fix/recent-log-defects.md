# VP Realty SMS Pilot - Recent Log Defects

Source analyzed:
- `data/VPRealty_Property_List  - MessageLogs_2026_06_12.csv`

Window analyzed:
- Last 14 days in the file, ending `2026-06-13T16:14:14+00:00`

## Summary

The recent logs show the bot is mostly stable on standard property Q&A, but there are still three recurring failure classes:
- wrong property reuse from session state
- address-like messages falling into area/clarify fallback
- partial address matching selecting the wrong listing

## Defect 1: Wrong property reused from session

Example:
- In: `Is 359 Timber Creek Lane Frisco still available for lease?`
- Out: `Yes, 2016 Highland Dr Wylie TX is currently Vacant-Unrented. For more details, call the leasing team at 972-591-8075.`

Why it is wrong:
- The user asked about a Frisco property, but the bot answered using a Wylie property from a prior session.

Likely cause:
- session `property_id` is leaking into a new property question

Impact:
- high

## Defect 2: Address-like messages fall back to area/clarify

Examples:
- In: `4304 placer mine rd`
- Out: `Which area are you looking to rent, like Allen, Frisco, or Plano? Or send your max budget or the property address.`

- In: `For 3603 Barberry Dr, do you know the owner's ballpark sale price, the home's current condition/any major repairs, and what timeline they'd want to close if they sold?`
- Out: `Which area are you looking to rent, like Allen, Frisco, or Plano? Or send your max budget or the property address.`

Why it is wrong:
- the message clearly contains an address, but the bot does not attempt a property answer

Likely cause:
- address parsing is too weak before the city/area fallback runs

Impact:
- high

## Defect 3: Partial address matching selects the wrong property

Example:
- In: `Thanks, Niketu-appreciate the 1736 Hickory Chase Cir address.`
- Out: `I found 3603 Barberry Drive ... Do you want rent, availability, or bedroom details for this property?`

Why it is wrong:
- the bot matched a completely different property

Likely cause:
- partial match scoring is too loose

Impact:
- high

## Defect 4: Code / lockbox requests need stricter routing

Examples:
- In: `You have the wrong code for 1001 Marigold listing. I have the appointment set, but I cannot access the home. Can you please provide the correct code?`
- Out: `I found 1001 Marigold Street ... Do you want rent, availability, or bedroom details for this property?`

- In: `Need code`
- Out: `Which area are you looking to rent, like Allen, Frisco, or Plano? Or send your max budget or the property address.`

Why it is wrong:
- code/lockbox requests should go directly to manager handoff when an address is present

Likely cause:
- code intent is not strong enough at the top of the routing tree

Impact:
- high

## Defect 5: Some availability questions answer the wrong property

Example:
- In: `Good morning, I requested a showing for 1009 Riverstone Trail in Princeton for tomorrow at 1130 am. Is there a better time for tomorrow I can show it?`
- Out: `Princeton options: 1001 Marigold Street - $2,350; 1526 Forever Way - $2,995 ...`

Why it is wrong:
- the user asked about one specific property, but the bot answered with area options

Likely cause:
- property matching did not win before city fallback

Impact:
- high

## Fix Order

1. Stop stale session property reuse from overriding a new address-like message.
2. Tighten address matching before area fallback.
3. Improve partial-match scoring so it does not choose the wrong listing.
4. Keep a dedicated code/lockbox manager-handoff path.
5. Add regression tests for the examples above.
