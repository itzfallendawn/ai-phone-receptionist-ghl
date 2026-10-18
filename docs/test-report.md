# Test report

**Date:** October 18, 2026 · **n8n:** 2.19.5 (self-hosted, Docker) · **Script:** [`tests/e2e_mock_test.py`](../tests/e2e_mock_test.py)

The workflow ran end to end against a mock GoHighLevel API, so no real account was used. All names, phone numbers and IDs below are made up.

## Results

| # | Scenario | Expected | Result |
|---|---|---|---|
| 1 | Unknown tool name | Hand-off reply | Pass |
| 2 | Check calendar, GoHighLevel rejects the request | Polite calendar-trouble reply | Pass |
| 3 | Book, GoHighLevel rejects the request | Polite booking-failed reply | Pass |
| 4 | Check calendar | Up to 5 slots in the business time zone (America/New_York) | Pass: 10:00 AM, 11:00 AM, 2:30 PM, 9:00 AM |
| 5 | Book, new caller | Contact created, appointment booked with a 60-minute end time, note logged | Pass |
| 6 | Book, returning caller | Existing contact reused, no new contact created | Pass |

## Raw output

```
REPLIES
- Unknown tool name: "I am not sure how to handle that request. Let me transfer you to our team."
- Check calendar, GoHighLevel rejects: "I am sorry, I am having trouble checking the calendar right now. Could you try again in a moment, or I can have our team call you back?"
- Book, GoHighLevel rejects: "I am sorry, something went wrong with the booking. Please call us back or try a different time."
- Check calendar: "I have these openings available: Tue, Jan 15, 10:00 AM, Tue, Jan 15, 11:00 AM, Tue, Jan 15, 2:30 PM, Wed, Jan 16, 9:00 AM. Which works best for you?"
- Book, new caller: "You are all set. Your appointment has been booked. Is there anything else I can help you with?"
- Book, returning caller: "You are all set. Your appointment has been booked. Is there anything else I can help you with?"

REQUESTS TO THE MOCK GOHIGHLEVEL API (normal cases)
- GET /calendars/mock-calendar/free-slots?startDate=1894698000000&endDate=1895043600000&timezone=America%2FNew_York
- GET /contacts/?locationId=mock-location&query=%2B15553334444
- POST /contacts/
  {"firstName": "Jamie", "lastName": "Rivera", "phone": "+15553334444", "locationId": "mock-location", "source": "VAPI Inbound Call"}
- POST /calendars/events/appointments
  {"calendarId": "mock-calendar", "locationId": "mock-location", "contactId": "new-contact-1", "startTime": "2030-01-15T15:00:00.000Z", "endTime": "2030-01-15T16:00:00.000Z", "title": "Jamie Rivera | Roof inspection"}
- POST /contacts/new-contact-1/notes/
  {"body": "VAPI call: appointment booked by the AI receptionist\nCaller: Jamie Rivera\nPhone: +15553334444\nTime: 2030-01-15T15:00:00.000Z\nReason: Roof inspection"}
- GET /contacts/?locationId=mock-location&query=%2B15551112222
- POST /calendars/events/appointments
  {"calendarId": "mock-calendar", "locationId": "mock-location", "contactId": "existing-contact-1", "startTime": "2030-01-16T14:00:00.000Z", "endTime": "2030-01-16T15:00:00.000Z", "title": "Pat Lee | Follow-up"}
- POST /contacts/existing-contact-1/notes/
  {"body": "VAPI call: appointment booked by the AI receptionist\nCaller: Pat Lee\nPhone: +15551112222\nTime: 2030-01-16T14:00:00.000Z\nReason: Follow-up"}
```

In case 6, the workflow went straight from the contact search to the booking with no `POST /contacts/`. That is the fix for returning callers being duplicated (see the [changelog](../CHANGELOG.md)).
