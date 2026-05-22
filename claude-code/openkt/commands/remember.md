---
description: Save a memory to the current project's OpenKT store
argument-hint: <text to remember>
---

Save `$ARGUMENTS` as a memory in the current OpenKT project.

Steps:

1. Determine the right `--kind` based on the content:
   - "we chose X" / "we decided to..." → `decision`
   - "never do X; it broke Y" / "always avoid..." → `anti-pattern`
   - "X failed because Y; the fix is Z" → `incident`
   - "the way to do X is Y" → `pattern`
   - environment / config / domain facts → `context`

2. Run `kt remember "$ARGUMENTS" --kind=<chosen>`.

3. Confirm to the user with the assigned memory ID + a one-line summary
   of what kind you picked and why. If you guessed wrong, they can
   re-save with a different `--kind` or `kt forget <id>` and retry.
