# Changelog

## v3 (October 2026)

Every change below came out of testing the workflow end to end against a mock GoHighLevel API.

**Bugs fixed**

1. **Config dropped the call data.** The Config node used an older settings format that current n8n ignores, so nothing reached the next step and every call fell through to "I am not sure how to handle that request." Config is rebuilt in the current format and passes the VAPI request through.
2. **Returning callers were duplicated.** The "Contact Exists?" check looked for a top-level `total` field that the contact search response doesn't return, so every caller was treated as new. It now counts the contacts that come back.
3. **Wrong times were read out.** Slots were formatted in the server's time zone, so a 10:00 AM New York slot was spoken as 3:00 PM on a UTC server. Times now use `GHL_TIMEZONE`.
4. **A failed booking could still sound successful.** The booking step used the legacy "continue on fail" setting, which sends errors down the success path, so the caller could hear "You are all set" when GoHighLevel had rejected the booking. It now uses a real error output that goes to the "Book Failed" reply.
5. **The call note sent the wrong ID.** The note put the contact's ID in `userId`, a field GoHighLevel expects to hold a staff user ID. The field is removed.

**Hardening**

- Error outputs on every GoHighLevel call that happens before the caller gets an answer: free slots, contact search, contact creation and booking.
- New "Slots Failed" reply, so a calendar outage still gets a polite answer.
- Free-slot parsing reads the date keys in the GoHighLevel response directly, and still accepts a `_dates_` wrapper.
- Optional companion workflow (`error-alert-slack.json`) that posts any failure to Slack.
- Cleaner node names and a tidier canvas.

## v2 (May 2026)

- Added `endTime` to bookings (start time plus the appointment length, 60 minutes by default). Without it, GoHighLevel rejects every booking.
- Turned the requested time into a valid ISO date before use, falling back to tomorrow at 9 AM when the value can't be read.
- Added a fallback reply for unknown tool names, so VAPI never waits on a call that has no answer.
- The confirmation goes back to the caller before the call note is written, so the caller never waits on the note.
- Capped the slots read out to five.

## v1

- First version: VAPI tool calls into n8n, with free-slot lookup and booking in GoHighLevel.
