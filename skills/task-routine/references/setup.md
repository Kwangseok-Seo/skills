# setup — first run, config, capability probe

> Read on the first run (no config anywhere) or when invoked as `task-routine setup`. Never read it again once config exists.

## The wizard

Four questions, then write. **Ask nothing that can be detected** — show the detected value as the default and let the user press through it.

What happens next depends on **why** the wizard ran: invoked explicitly as `setup`, writing the config is the end of the invocation. Triggered automatically because no config existed, the run **continues** into the probe and Phase 1 with the answers just given — the user asked for a task run and answering four questions is not a reason to make them ask twice.

| # | Question | Default offered |
|---|---|---|
| 1 | Where do tasks come from? | a `TODO.md` in the repo if one exists, else ask |
| 2 | How is a change verified? | the repo fingerprint (`BUILD-LOOP.md` §2c) — pressing through it **is** the approval that command needs. When the fingerprint matches nothing there is no default to press through: ask outright, and the typed answer is rung 3, approved by the typing |
| 3 | How much should run unattended? | `assisted` |
| 4 | How many tasks may one unattended run process? | `5` |

Question 3 is the one to explain rather than just ask, because its cost is invisible up front:

```
manual     every decision is yours
assisted   choices that come with a recommendation run on their own; the rest come to you
auto       everything auto-eligible runs on its own — not the default, and never sticky:
           --auto applies to one invocation and is not written here
```

## Config

Two files. Project wins over global, **key by key** — a project that sets only `verify.command` still inherits the global autonomy level. It inherits it whether it likes it or not: the trust split in `SKILL.md` decides which side of the table below a key may come from, and no repo can renegotiate it.

```
~/.claude/task-routine/config.json     global — written by the wizard
<repo>/.claude/task-routine.json       project — optional, committed, shared with the team
```

```json
{
  "version": 1,
  "source": { "adapter": "markdown", "path": "TODO.md" },
  "verify": { "command": "npm test" },
  "autonomy": { "level": "assisted" },
  "auto": { "max_tasks": 5, "consecutive_failures": 2 },
  "design_loop": { "rounds": 3, "reviewer": "auto" },
  "build_loop": { "iterations": 3 },
  "execution": { "timeout_minutes": 20,
                 "executor": { "command": "herdr", "session_env": "HERDR_ENV" } },
  "capabilities": { "probed_at": "2026-08-16T09:14:00+09:00",
                    "present": ["git", "gh", "node"], "absent": ["herdr", "tdd"] }
}
```

Every key is optional; missing keys take the defaults above. A `version` this build does not recognise is reported and the file is read on a best-effort basis for the keys it does know — never rejected outright, since a newer config on an older skill is a normal state of the world. `reviewer: "auto"` means "highest available rung" — pin it to a specific tool only when you have a reason.

`execution.executor` is the only thing that makes rung 1 of the executor ladder reachable, and it has no default: **written by nobody, rung 1 does not exist.** Both fields are required — `command` is what the probe looks for on `PATH`, `session_env` names the variable whose being set and non-empty means a live session — and a `command` with no `session_env` leaves liveness with no input, so the run stays at rung 2 and says why. That is not a formality: rung 1's whole justification is *the user set one up and is watching*, and a tool that offers no signal of a live session cannot evidence the second half. It is a global-file key because a repository must not name the binary this run launches its workers with — a different question from naming its own test command, which `verify.command` answers under the approval `BUILD-LOOP.md` §2c requires.

| Key | May come from |
|---|---|
| `version` · `source` · `verify.command` | global **or** project — facts about the project |
| `autonomy.level` | global, or `--level` / `--auto` for one invocation |
| `auto.*` · `design_loop.*` · `build_loop.*` · `execution.*` | the **global file only** — there is no flag for these, and a project cannot raise its own caps |
| `capabilities` | the probe, in the global file only — it describes this machine, which is not a project fact |

The wizard writes the global file, so it may write both sides. A project file carrying a right-hand key is reported and ignored, not merged. A project file that cannot be parsed at all is reported and ignored **entirely** — dropping project config can only narrow what runs unattended, never widen it, so failing that way is safe in a way that guessing is not.

## Secrets never live in config

Store the **name** of an environment variable, never its value:

```json
{ "source": { "adapter": "github", "repo": "owner/name", "token_env": "GITHUB_TOKEN" } }
```

The project config is meant to be committed and shared. That is only safe if it holds nothing secret — so if a config file is found containing something shaped like a credential (a long opaque string under a key named `token`, `key`, `secret`, `password`), **say so and stop.** Continuing would mean reading it every run and eventually printing it in a report.

## Capability probe

Runs **every** run, not just at setup.

| Layer | How | Notes |
|---|---|---|
| External CLIs | `command -v <name>` · PowerShell `Get-Command <name> -ErrorAction SilentlyContinue` | `git`, `gh`, plus `execution.executor.command` when set |
| Skills and agents | list `~/.claude/skills/*/`, `~/.claude/agents/*.md`, and the project's `.claude/` | how `tdd`, review, and simplify tooling are found |
| Plugins | `~/.claude/plugins/installed_plugins.json` — `{"plugins": {"<name>@<marketplace>": [{"installPath": …}]}}` | v2 schema |
| Native | none — `git worktree` is always present | whether a subagent satisfies the executor contract is `execution.md`'s question |

The snapshot the probe compares against is the `capabilities` key above — written by the probe after every run, never hand-edited, and never read as truth. **It is a cache for detecting drift, never the source of truth.** Duplicating the capability list into config and trusting it is exactly how a stored list and reality come apart: the user installs a tool and the skill never notices, or removes one and the skill keeps routing to it.

```
Capabilities   git 2.45 ✓ · gh ✓ · node ✓ · herdr ✗ · tdd skill ✗
Changed        herdr was present at last run, now absent → parallel drops to rung 2
```

The second line is the whole point of re-probing. Print it whenever anything changed; print nothing when nothing did. On the very first probe there is no snapshot to differ from — that is not a change, so write the snapshot and print only the first line.

### What a probe must not do

- **Never install anything.** A probe reports the world, it does not adjust it.
- **Never run a tool to find out whether it works.** `--version` or `--help` is the whole check; anything more has side effects.
- **A failed probe returns "absent", it does not stop the run.** The probe is not a gate — the gates are elsewhere and they already handle absence by degrading and saying so.
