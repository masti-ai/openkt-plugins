---
description: Sign in to OpenKT (or start the device-code flow)
---

Run `kt login --non-interactive --json`. The output is a JSON envelope
with:

  - `device_code` — opaque code the agent doesn't need to display
  - `verification_url` — print this to the user; they should open it in
    a browser
  - `expires_in` — seconds until the code expires (typically 300-600)
  - `poll_interval_seconds` — recommended poll cadence

Steps:

1. Print the verification_url to the user prominently. Tell them to
   open it in any browser, complete sign-in, and come back.

2. Poll `kt login --poll-device-code=<device_code> --non-interactive --json`
   every `poll_interval_seconds`. Responses:

   - `{"status": "pending"}` — keep polling
   - `{"status": "approved", "email": "...", "orgs": [...]}` — success;
     congratulate the user and tell them what's wired
   - `{"status": "expired"}` — restart with a fresh `/openkt:login`

3. Once approved, also surface what was wired: shell rc patched, MCP
   registered with whichever harnesses, hooks installed. The login
   path runs all of those automatically.

Stop polling after `expires_in` seconds. If the user takes longer,
they can just `/openkt:login` again.
