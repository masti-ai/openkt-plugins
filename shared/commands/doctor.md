---
description: Diagnose the OpenKT install + auth + project binding
---

Run `kt doctor --json` and interpret the output for the user.

Format:

1. List every check with PASS/FAIL + detail
2. For each FAIL, suggest the fix (see memory-doctor skill for the
   troubleshooting matrix)
3. List harness detection: for each, show which signals passed/failed
   and the verdict
4. If everything passes, just say "all checks pass" — don't pad

If doctor returns exit code 2, the system is fundamentally not okay
(network / server). Surface that to the user — don't try to "fix" it.
