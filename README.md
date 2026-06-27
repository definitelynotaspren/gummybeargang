# Disruptor Pattern Watchdog
## A transparency-first, human-in-the-loop coordination monitoring tool for Discord

---

## What this is

A four-agent pipeline that monitors Discord servers for **structural coordination patterns** historically associated with bad-faith disruption of civil society organizations. The tool documents; humans decide.

**What it monitors:** Metadata and coordination structure — timing patterns, account clustering, synchronized language across unrelated accounts. It does NOT classify message content or political viewpoints.

**What it never does:** Issue bans, send reports to authorities, DM users, or take any automated action. Every pipeline run produces documentation for human moderator review.

**Why structural signals only:** Content-based classifiers for "disruptors" have a well-documented failure mode — they become indistinguishable from surveillance tools used against the very movements they're meant to protect. Structural coordination signals (synchronized timing, cluster arrivals, identical non-attributed phrasing across accounts with no shared history) are specific to coordination behavior, not to any particular viewpoint.

---

## Architecture

```
Discord messages → MessageStore (metadata only; no content stored)
                        │
                 [every N messages or T minutes]
                        │
              AgentOrchestrator (hard stop: 4 rounds per ticket)
                        │
          ┌─────────────┼──────────────┬──────────────┐
          │             │              │               │
    Agent 1:      Agent 2:       Agent 3:        Agent 4:
    Coordination  Tactics        Evidence        Report
    Detector      Reference      Logger          Writer
    (metadata     (historical    (case file      (two outputs)
    signals)      match +        + confidence        │
                  alternates)    tier)           ┌───┴───┐
                                             public  mod-only
                                             notice  full report
```

All four agents post structured JSON summaries to **#agent-coordination** — a hidden channel that serves as the full audit trail. The pipeline runs once end-to-end per trigger, producing at most one ticket per run.

---

## Channels required

| Channel | Visibility | Purpose |
|---------|-----------|---------|
| `#agent-coordination` | Bot + admins only | Agent pipeline audit trail (JSON envelopes) |
| `#transparency-log` | Public | Anonymized coordination notices |
| `#mod-reports` | Moderators only | Full case files with evidence chains |

---

## The four agents

### Agent 1 — Coordination Detector
**Runs on:** Message metadata and timestamps. Never reads message content.

Detects:
- Synchronized posting bursts (multiple accounts, narrow time window)
- Account age / activity anomalies (very new account, very high volume)
- Cluster arrivals (multiple accounts joining within 48hr of each other)
- Engagement velocity anomalies (reaction bursts vs. community baseline)

Outputs: `coordination_score` (0–1), `coordination_signals[]`

### Agent 2 — Tactics Reference
**Runs on:** Agent 1's signal list.

Matches signals against the historical disruption tactics library (Church Committee taxonomy, RAND influence op research, Stanford Internet Observatory frameworks). **Required to populate `alternate_explanations[]` before the ticket advances** — this is a hard gate.

Outputs: `tactic_matches[]`, `alternate_explanations[]`, `false_positive_estimate`

### Agent 3 — Evidence Logger
**Runs on:** Output from Agents 1 and 2.

Builds a timestamped, chronological evidence chain. References message IDs (not content). Assigns confidence tier:
- `SPECULATIVE` — single signal, many alternate explanations
- `CORROBORATED` — 2+ independent signals
- `CONFIRMED` — convergent signals, low alternate explanation rate

Account identifiers are withheld from reports unless `CONFIRMED`.

Outputs: `evidence_items[]`, `confidence_tier`, `timeline_summary`

### Agent 4 — Report Writer
**Runs on:** Full ticket envelope.

Produces two outputs:
1. **Public notice** — anonymized, includes ticket ID, alternate explanations, false positive estimate, "human moderators are reviewing this"
2. **Mod case file** — full evidence chain, historical sources, account hashes (CONFIRMED only), moderator action checklist

Closes the ticket. Hard stops the pipeline.

---

## Ticket lifecycle

```
Trigger (message count or schedule)
    ↓
Agent 1 runs → coordination_score
    ↓
[if score < 0.25] → ticket dismissed, nothing posted
    ↓
Agent 2 runs → tactic matches + alternates
    ↓
Agent 3 runs → evidence log + confidence tier
    ↓
Agent 4 runs → reports posted
    ↓
Ticket closed (max 4 rounds, hard stop)
```

Only tickets that clear Agent 1's minimum threshold (0.25 coordination score) advance. Most benign activity never produces a ticket.

---

## Transparency and false positive protection

**Anonymization ladder:**
- Public channel: never contains usernames or user IDs
- Mod channel: account *hashes* (for audit log lookup) only at `CORROBORATED` or above
- Account *identifiers*: only retrievable by moderators for `CONFIRMED` tier tickets, by pulling from the audit log

**Every report includes:**
- Estimated false positive likelihood
- List of alternate innocent explanations (required, non-empty)
- Statement that no automated action has been taken
- Ticket ID for users to contest with moderators

**Due process path:**
Any user who believes they were flagged in error can reference their ticket ID (visible in the public channel) when contacting moderators. The full evidence chain is preserved in the audit log so moderators can assess the reasoning.

**The moderator checklist (always included in mod report):**
```
[ ] Review evidence items in audit log against ticket ID
[ ] Check account metadata for items flagged CORROBORATED or above
[ ] Consider alternate explanations listed before any action
[ ] Dismiss ticket if false positive
[ ] Escalate to senior moderator if CONFIRMED tier
[ ] Request context from user(s) if appropriate
[ ] No automated action has been or will be taken by this system
```

---

## Historical sources for the tactics library

The `tactics_library.py` tactic entries cite their sources inline. Primary sources used:

- **Church Committee Final Report** (1976) — Senate Select Committee to Study Governmental Operations with Respect to Intelligence Activities. Books II & III are the primary source on COINTELPRO tactics. Public domain.
- **Frank Donner, "The Age of Surveillance"** (1980) — comprehensive taxonomy of domestic intelligence disruption methods
- **Brian Glick, "War at Home"** (1989) — practical guide to COINTELPRO tactics written for organizers
- **RAND Corporation influence operations research** (2016–2023) — "Firehose of Falsehood" and related reports, all public
- **Stanford Internet Observatory** — "Repeat Offenders," "Unheard Voice," and other published reports on coordinated inauthentic behavior
- **EU DisinfoLab** — "Indian Chronicles," "Anti-EU Disinformation," other published influence network analyses
- **Senate Intelligence Committee, Vol. 2** (2019) — Russian active measures report

---

## Setup

### Environment variables

```bash
DISCORD_BOT_TOKEN=your_bot_token
AGENT_COORD_CHANNEL_ID=123456789   # hidden, bot + admins only
PUBLIC_CHANNEL_ID=123456789        # transparency log, public
MOD_CHANNEL_ID=123456789           # mod-only full reports
TRIGGER_MESSAGE_COUNT=20           # messages before analysis pass
ANALYSIS_INTERVAL_SECS=300         # seconds between scheduled passes
```

### Install

```bash
pip install discord.py aiohttp
ollama pull llama3.2:1b
ollama create watchdog-tactics -f config/Modelfile

# Build training dataset
cd training && python build_dataset.py

# Run
python bot/discord_bot.py
```

### Fine-tuning the tactics reference agent

```bash
cd training
python build_dataset.py           # generates datasets/train.jsonl + val.jsonl

# Add your own observed examples to build_dataset.py → TRAINING_EXAMPLES
# Then follow llama.cpp fine-tuning steps (same as grooming-watchdog guide)
```

---

## What this does NOT do

- Does not classify political content or viewpoints
- Does not issue automated bans, kicks, mutes, or warnings
- Does not send reports to any external authority
- Does not DM users
- Does not store raw message content (only message IDs and metadata)
- Does not expose user IDs in public-facing output
- Does not take any action without explicit human moderator decision

---

## Suggested reading for moderators using this tool

- Glick, Brian. *War at Home* (1989) — short, practical, written for organizers
- Church Committee Final Report, Book III (1976) — primary source, free at archive.org
- Stanford Internet Observatory published reports — free at cyber.fsi.stanford.edu
- RAND, "The Russian Firehose of Falsehood" (2016) — free at rand.org
