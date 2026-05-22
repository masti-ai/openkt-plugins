# Skill evaluation methodology — openkt-plugins

How to validate a new skill in `openkt-plugins/shared/skills/<name>/` before shipping it to the per-harness plugin bundles. Reusable across every skill we add to OpenKT.

This is the recipe followed for `direction-tracker` (iteration 1 at `shared/skills/direction-tracker-workspace/iteration-1/`).

## Why this exists

Anthropic ships `mcp-server-dev` + a separate `skill-creator` plugin with strong opinions on how to validate skills (red-green-refactor with subagent comparison, quantitative benchmarks, side-by-side outputs). We follow that framework but adapt it to our monorepo so:

- All skill source lives in `shared/skills/<name>/` (single source of truth)
- All eval workspaces live as siblings in `shared/skills/<name>-workspace/iteration-N/`
- Benchmark + viewer artifacts stay in-repo, browseable on GitHub

## File layout for a skill

```
shared/skills/<name>/
├── SKILL.md                 # YAML frontmatter + body, <500 lines
├── references/              # Deeper docs Claude reads as needed
│   ├── *.md
├── templates/               # Files Claude may copy verbatim
└── evals/
    └── evals.json           # 2-4 realistic test prompts
```

## File layout for an eval workspace

```
shared/skills/<name>-workspace/
└── iteration-N/                            # one per round of revisions
    ├── <eval-name>/                        # one directory per eval
    │   ├── eval_metadata.json              # prompt + assertions
    │   ├── input/                          # optional starting files
    │   ├── with_skill/
    │   │   ├── outputs/                    # what the agent produced
    │   │   │   ├── reply.md
    │   │   │   └── <any-other-output>
    │   │   ├── timing.json                 # tokens + duration_ms
    │   │   ├── grading.json                # summary + expectations
    │   │   └── run-1/                      # symlink/copy for aggregator
    │   │       ├── grading.json
    │   │       └── timing.json
    │   └── without_skill/                  # same shape as with_skill
    ├── eval-1 -> <eval-name>/              # symlink for aggregator
    ├── eval-2 -> <other-eval-name>/
    ├── grade.py                            # the grader script
    ├── benchmark.json                      # output of aggregate_benchmark.py
    ├── benchmark.md                        # human-readable benchmark
    └── review.html                         # static eval-viewer
```

## The loop, end to end

### 1. Author the skill

Write `SKILL.md` + references. The description must be **pushy** per skill-creator guidance — it's the primary triggering mechanism. Include both what the skill does AND specific contexts for when to use it ("Make sure to use this whenever X, even if the user doesn't name the skill").

### 2. Write 2-4 evals

In `evals/evals.json`, write realistic test prompts — what a real user would actually type. Mix:
- Happy path (skill should fire and produce the canonical output)
- Negative case (skill should NOT fire / should NOT do something)
- Edge case (one prompt that exercises multiple skill dimensions at once)
- Explicit invocation (user names the skill or its slash command)

Don't write assertions yet. You'll draft them in step 4 while runs are in flight.

### 3. Set up the workspace

```bash
WS=openkt-plugins/shared/skills/<name>-workspace/iteration-1
mkdir -p $WS/{<eval-1-name>,<eval-2-name>,...}/{with_skill/outputs,without_skill/outputs,input}
```

Write `eval_metadata.json` in each eval directory (assertions can be empty for now). Write any starting files (like a pre-existing DIRECTIONS.md) into `input/`.

### 4. Spawn 2N subagents in ONE turn

For each of N evals, spawn TWO subagents in the same turn:

**with_skill** — prompt mentions the skill path and tells the agent to read it:

```
You're simulating Claude Code receiving a user prompt mid-conversation.
The `<skill-name>` skill is loaded — apply it.

READ first:
1. /path/to/SKILL.md
2. /path/to/references/<each>.md

Setup: <any starting context>
User prompt: <the eval prompt>

Apply the skill. Save outputs to:
- <workspace>/<eval>/with_skill/outputs/reply.md
- <workspace>/<eval>/with_skill/outputs/<other-files>
```

**without_skill** — same prompt, no skill access:

```
You're simulating Claude Code mid-conversation. NO skills are loaded.

Setup: <any starting context>
User prompt: <the eval prompt>

Respond as you naturally would. Save outputs to:
- <workspace>/<eval>/without_skill/outputs/reply.md
- <workspace>/<eval>/without_skill/outputs/<other-files>
```

Spawn in background to avoid blocking. Total agents = `2 × N` (e.g., 8 for 4 evals).

### 5. While runs are in flight, draft assertions

Each assertion has:
- `text` — human-readable, descriptive (will appear in the viewer)
- Logic that the grader can check programmatically (regex/substring/byte-diff)

Good assertions are objectively verifiable. Subjective qualities (writing style, design quality) belong in qualitative review, not assertions.

Write assertions into each `eval_metadata.json` and into the grader script (see step 7).

### 6. As notifications arrive, capture timing

Every Agent completion notification gives you `total_tokens` and `duration_ms`. Save immediately to `<eval>/<arm>/timing.json`:

```json
{"total_tokens": 41320, "duration_ms": 49296, "total_duration_seconds": 49.3}
```

This is the only time this data is available — capture it before context shifts.

### 7. Write a Python grader

One script grades all 2N runs. For each run:

1. Read `outputs/reply.md` and any other artifacts
2. Read the input files (if any) for diff-style assertions
3. For each assertion in `eval_metadata.json`, return `{text, passed, evidence}`
4. Write `<eval>/<arm>/grading.json` with `summary` block + `expectations` array
5. Also write to `<eval>/<arm>/run-1/grading.json` for the aggregator

```json
{
  "summary": {
    "passed": 7,
    "failed": 0,
    "total": 7,
    "pass_rate": 1.0
  },
  "expectations": [
    {"text": "...", "passed": true, "evidence": "..."}
  ]
}
```

Common assertion patterns:
- "File X was created" — `len(read(out_dir / "X")) > 0`
- "File X was NOT modified" — byte-equal diff against input
- "Reply contains drift flag" — regex search in reply, **strip negation patterns first** (e.g., "no drift flag" should NOT count as a drift marker)
- "Reply answers the underlying question" — substring search for keywords from the prompt
- "DIRECTIONS.md has at least N pools" — count `## Pool` headings

### 8. Add `eval-N` symlinks for the aggregator

`aggregate_benchmark.py` looks for directories matching `eval-N`. Use descriptive directory names, then symlink:

```bash
cd $WS
ln -sfn <descriptive-name-1> eval-1
ln -sfn <descriptive-name-2> eval-2
```

### 9. Aggregate + generate viewer

```bash
SC=/path/to/skill-creator
python3 -m scripts.aggregate_benchmark $WS --skill-name <name>
python3 $SC/eval-viewer/generate_review.py $WS \
  --skill-name "<name>" \
  --benchmark $WS/benchmark.json \
  --static $WS/review.html
```

`--static` writes a standalone HTML file (no server). Works in headless/Cowork environments. The user opens it in a browser, clicks through evals, writes feedback per eval, exports `feedback.json`.

### 10. Read benchmark.md, present to user

Headline numbers to communicate:
- Pass rate (with vs without)
- Delta
- Time + token cost
- Variance (high stddev in baseline = the skill is normalizing behavior, a strong signal)

### 11. Iterate

Read `feedback.json` (the user's per-eval comments after they review). Find patterns:
- Did a specific assertion always fail with-skill? Fix the SKILL.md.
- Did the user complain about over/under-flagging? Adjust the calibration section.
- Did multiple subagents write similar helper code? Bundle it into `scripts/`.

Repeat steps 4-10 in a new `iteration-2/` workspace. Pass `--previous-workspace iteration-1` to `generate_review.py` to show side-by-side.

Stop when:
- Pass rate is acceptable (>90% with-skill is the bar)
- User reports satisfaction
- No clear next improvement remains

### 12. Wire into per-harness plugin bundles

Once the skill is validated, copy or symlink it into each harness's plugin folder:

```bash
cp -r shared/skills/<name> claude-code/openkt/skills/<name>
cp -r shared/skills/<name> codex/openkt/skills/<name>     # if applicable
# Hermes skills go in the Hermes adapter's plugin config, not as SKILL.md
```

Commit + push. Users on `kt plugins install openkt --for=claude-code` get the skill automatically on their next install.

## Anti-patterns

- **Skipping the baseline.** Without a control run, you can't separate skill value from natural agent behavior. ALWAYS run with-skill AND without-skill in parallel.
- **Vague assertions.** "Reply is good" can't be machine-checked. Decompose into objective checks.
- **Over-fitting the grader.** If you tweak the grader to make the skill pass instead of fixing the skill, you've broken the loop.
- **One-shot evals.** For high-variance behavioral skills, run 3+ runs per configuration and look at mean + stddev. Single runs hide flakiness.
- **No negation handling.** "Reply mentions X" — but did it mention "X was not done"? Strip negation patterns before substring-matching, or use semantic checks.

## Reference implementation

`direction-tracker` iteration-1 is the worked example. See:
- `shared/skills/direction-tracker/` — the skill source
- `shared/skills/direction-tracker-workspace/iteration-1/grade.py` — the grader
- `shared/skills/direction-tracker-workspace/iteration-1/benchmark.md` — the headline numbers
- `shared/skills/direction-tracker-workspace/iteration-1/review.html` — the static viewer

Result on first iteration: 100% pass-rate with-skill vs 54.8% baseline, +45pp delta.
