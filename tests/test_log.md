# Test Log

Use this file to keep a short record of local test runs and notable bot-answer checks.

## 2026-06-14

- Command: `python -m unittest discover -s tests -v`
- Result: `PASS`
- Total tests: `21`
- Notable coverage:
  - exact property lookup
  - budget routing
  - area typo and alias matching
  - contact and code flows
  - real log-derived message cases
  - 200-case regression matrix
- Notes:
  - `contact` / `contact_info` alias parsing is covered
  - budget-only queries clear stale property context in the test suite
  - the browser smoke test now runs 15 real-life prompts only

## Bot Output Log

These replies were generated from isolated local runs against the checked-in snapshot.

- Question: `1009 Riverstone Trail Princeton, TX 75407`
  - Intent: `property_qna`
  - Property: `373`
  - Reply: `1009 Riverstone Trail, Princeton, TX 75407 at 1009 Riverstone Trail Princeton, TX 75407 is Vacant-Rented. It has 5 bedrooms, 2.0 bathrooms, rent $2,195 per month, and is available from Jun 10, 2026. For more details, call 972-591-8075.`

- Question: `I am looking for property under 2300 in frisco`
  - Intent: `budget_list`
  - Property: `none`
  - Reply: `Frisco under $2,300 options: 12873 Kiltartan Drive Frisco, TX 75035 - $2,050 Send your budget or the address to narrow it down. For more details, call the leasing team at 972-591-8075.`

- Question: `Good morning, I requested a showing for 1009 Riverstone Trail in Princeton for tomorrow at 1130 am. Is there a better time for tomorrow I can show it?`
  - Intent: `property_qna`
  - Property: `373`
  - Reply: `1009 Riverstone Trail, Princeton, TX 75407 at 1009 Riverstone Trail Princeton, TX 75407 is Vacant-Rented. It has 5 bedrooms, 2.0 bathrooms, rent $2,195 per month, and is available from Jun 10, 2026. For more details, call 972-591-8075.`

- Question: `Who should I contact for details? 100 Stovall Lane Caddo Mills, TX 75135`
  - Intent: `property_qna`
  - Property: `1811`
  - Reply: `For more details, call 903-213-3818 (#6) or email nishant@vprealtyservices.com.`

- Question: `What is the entry code for this property? 100 Stovall Lane Caddo Mills, TX 75135`
  - Intent: `property_qna`
  - Property: `1811`
  - Reply: `The entry code is 1975. If that does not work, please contact the property manager at 903-213-3818 (#6).`

- Question: `Princton`
  - Intent: `area_list`
  - Property: `none`
  - Reply: `Princeton options: 201 Ardsley Lane Princeton, TX 75407 - $1,795; 2021 Meadow Park Dr Princeton, TX 75407 - $1,795; 1033 Sourgum St Princeton, TX 75407 - $1,850. And 9 more. Send your budget or the address to narrow it down. For more details, call the leasing team at 972-591-8075.`

- Question: `Hi Niketu, thanks. We're looking to buy (not rent) in Allen/Frisco/Plano-ideally a fixer that needs work. Do you have anything like that available or coming up soon? If so, what's the address?`
  - Intent: `area_list`
  - Property: `none`
  - Reply: `Frisco options: 12873 Kiltartan Drive Frisco, TX 75035 - $2,050; 12475 Cajun Dr Frisco, TX 75035 - $2,495; 1665 Princess Lane ( HOA Reg Must ) Frisco, TX 75036 - $2,695. And 16 more. Send your budget or the address to narrow it down. For more details, call the leasing team at 972-591-8075.`

- Question: `Can you please give me a call about this property?`
  - Intent: `area_list`
  - Property: `none`
  - Reply: `Prosper options: 1650 Chisholm Trail Prosper, TX 75078 - $3,750 Send your budget or the address to narrow it down. For more details, call the leasing team at 972-591-8075.`

- Question: `This link says property is not listed on any platform. Can you update me on status?`
  - Intent: `area_list`
  - Property: `none`
  - Reply: `Prosper options: 1650 Chisholm Trail Prosper, TX 75078 - $3,750 Send your budget or the address to narrow it down. For more details, call the leasing team at 972-591-8075.`

- Question: `Hi, I am interested in touring a property you have listed at 635 Beltrand Ln, in Fate TX. I have tried to contact someone several times and have not heard back. May I please have more information on the property and when I can tour please and thank you!`
  - Intent: `property_qna`
  - Property: `1508`
  - Reply: `For more details, call 972-591-8075 or email anjali@vprealtyservices.com.`

- Question: `I called a number of times now, but have gotten no response :-(`
  - Intent: `human_handoff`
  - Property: `none`
  - Reply: `No problem. I can connect you with a leasing specialist. Please share the property area or address if you have it. For more details, call the leasing team at 972-591-8075.`

- Question: `What is the application fee?`
  - Intent: `clarify_property`
  - Property: `none`
  - Reply: `Which area are you looking to rent, like Allen, Frisco, or Plano? Or send your max budget or the property address. For more details, call the leasing team at 972-591-8075.`

- Question: `Is 1009 Riverstone Trail Princeton, TX 75407 still available for lease?`
  - Intent: `property_qna`
  - Property: `373`
  - Reply: `Yes, 1009 Riverstone Trail, Princeton, TX 75407 is currently Vacant-Rented. For more details, call 972-591-8075.`

- Question: `How much is rent? 1009 Riverstone Trail Princeton, TX 75407`
  - Intent: `property_qna`
  - Property: `373`
  - Reply: `The rent for 1009 Riverstone Trail, Princeton, TX 75407 is $2,195 per month. For more details, call 972-591-8075.`

- Question: `Thanks, Niketu-I appreciate the 1736 Hickory Chase Cir address.`
  - Intent: `property_qna`
  - Property: `280`
  - Reply: `1736 Hickory Chase circle Keller, TX 76248 at 1736 Hickory Chase circle Keller, TX 76248 is Vacant-Unrented. It has 4 bedrooms, 3.0 bathrooms, rent $3,495 per month, and is available from Apr 10, 2026. For more details, call 972-591-8075.`

- Question: `How much is rent?`
  - Intent: `area_list`
  - Property: `none`
  - Reply: `Howe options: 1810 Clegg Howe, TX 75459 - $1,595 Send your budget or the address to narrow it down. For more details, call the leasing team at 972-591-8075.`

## Suggested format for future entries

- Date:
- Command:
- Result:
- Coverage:
- Notes:
