# VAPI setup

The workflow is one webhook that VAPI calls as a tool server. You add two tools to your VAPI assistant, and both point at the same URL.

## 1. Server URL

After you activate the workflow in n8n, its production URL looks like this:

```
https://YOUR-N8N-DOMAIN/webhook/vapi-ghl-setter
```

VAPI needs to reach this URL from the internet, so a local n8n needs a tunnel (for example Cloudflare Tunnel or ngrok) or a hosted instance.

## 2. Tools

Create two **Function** tools in VAPI, each with the server URL above.

**check_calendar**

```json
{
  "name": "check_calendar",
  "description": "Check which appointment times are available near the time the caller asked for.",
  "parameters": {
    "type": "object",
    "properties": {
      "requested_time": {
        "type": "string",
        "description": "The caller's preferred date and time in ISO 8601 with the time zone offset, for example 2026-11-03T10:00:00-05:00"
      }
    },
    "required": ["requested_time"]
  }
}
```

**book_calendar**

```json
{
  "name": "book_calendar",
  "description": "Book the appointment once the caller has confirmed their name and a time from the available slots.",
  "parameters": {
    "type": "object",
    "properties": {
      "name": { "type": "string", "description": "The caller's full name" },
      "requested_time": { "type": "string", "description": "The confirmed slot in ISO 8601 with the time zone offset" },
      "reason": { "type": "string", "description": "A short reason for the appointment" }
    },
    "required": ["name", "requested_time"]
  }
}
```

The workflow routes on the tool name: anything containing "check" goes to availability, and anything containing "book" goes to booking. Any other tool name gets a polite hand-off reply.

The caller's phone number comes from the call itself (`call.customer.number`), so the assistant doesn't need to ask for it.

## 3. A starter prompt

```
You are the friendly receptionist for {Business Name}. Your job is to book appointments.

1. Ask what the appointment is for and when the caller would like to come in.
2. Always call check_calendar before offering any times, and only offer times it returns.
3. Confirm the caller's full name and the exact time back to them.
4. Then call book_calendar with the name, the confirmed time and the reason.
5. Send times in ISO 8601 with the time zone offset.
6. If a tool says something went wrong, apologise and offer to have the team call them back.

Keep answers short and natural. Never invent availability.
```

## 4. Reply format

Each tool call gets back the format VAPI expects:

```json
{ "results": [ { "toolCallId": "call_abc123", "result": "I have these openings available: ..." } ] }
```
