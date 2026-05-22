---
description: Recall memories from the current project's OpenKT store
argument-hint: <query>
---

Run `kt recall "$ARGUMENTS"` and show the top matches to the user.

If no matches: tell the user the project has no memories matching the
query, and suggest they `/openkt:remember` with an example.

If matches: format each as a bullet with the kind tag in brackets:
  - [decision] chose drizzle over prisma (2026-05-15)
  - [anti-pattern] don't force-push to main
  - ...

Don't paraphrase the memories — quote them verbatim. The user wrote
them for a reason.
