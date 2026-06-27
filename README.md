# Disruptor Pattern Watchdog
## A transparency-first, human-in-the-loop coordination monitoring tool for Discord

---

## What this does (and what it doesn't)

This bot watches your Discord server for **structural coordination patterns** — the kind historically associated with organized bad-faith disruption of civil society organizations. Think: multiple new accounts showing up in a cluster, synchronized posting bursts, reaction flooding.

**What it monitors:** Metadata and coordination structure — timing patterns, account ages, synchronized posting across unrelated accounts. It never reads or stores message content.

**What it never does:** Ban anyone, kick anyone, DM anyone, or contact any authority. Every pipeline run produces a report for human moderator review. No automated action. Full stop.

**Why structural signals only:** Content-based "disruptor" classifiers have a well-documented failure mode — they become surveillance tools used against the movements they're supposed to protect. Structural signals (synchronized timing, cluster arrivals, identical phrasing across accounts with no shared history) are specific to coordination behavior, not to any particular viewpoint or politics.

---

## Files in this repo

```
discord_bot.py       — the bot itself; runs continuously and ingests messages
agents.py            — the four-agent pipeline + MessageStore (metadata-only store)
models.py            — shared data models (TicketEnvelope, signals, evidence)
tactics_library.py   — historical disruption tactics reference (Church Committee,
                       RAND, Stanford Internet Observatory, etc.)
build_dataset.py     — training dataset builder for the Tactics Reference agent
ui/
  app.py             — Flask web UI for managing agent configuration
  requirements.txt   — Flask dependency
  templates/
    index.html       — single-page agent management dashboard
visitor.js           — standalone frontend analytics snippet (unrelated to bot)
```

---

## How the pipeline works

When the bot triggers (either after a set number of messages, or on a timer), it opens a **ticket** and runs it through four agents in sequence:

```
Discord messages → MessageStore (metadata only; no content stored)
                        │
               [trigger fires]
                        │
              AgentOrchestrator
                        │
          ┌─────────────┼──────────────┬──────────────┐
          │             │              │               │
    Agent 1:      Agent 2:       Agent 3:        Agent 4:
    Coordination  Tactics        Evidence        Report
    Detector      Reference      Logger          Writer
    (score 0–1)   (tactic        (confidence     (two outputs)
                  matches +      tier)               │
                  alternates)                    ┌───┴───┐
                                             public  mod-only
                                             notice  full report
```

- If Agent 1's score is below 0.25, the ticket is dismissed. Nothing is posted.
- Agent 2 is **required** to generate alternate innocent explanations before the ticket advances — this is a hard gate in the code.
- Agent 3 assigns a confidence tier: `SPECULATIVE`, `CORROBORATED`, or `CONFIRMED`.
- Agent 4 produces two outputs: an anonymized public notice, and a full case file for moderators.
- The pipeline hard-stops at 4 rounds. One ticket per run, maximum.

All four agents post structured JSON to a hidden `#agent-coordination` channel — the full audit trail.

---

## Channels you need to create

Before starting the bot, create these three channels in your Discord server:

| Channel name | Who can see it | Purpose |
|---|---|---|
| `#agent-coordination` | Bot + admins only | Full pipeline audit trail (JSON) |
| `#transparency-log` | Public | Anonymized coordination notices |
| `#mod-reports` | Moderators only | Full case files with evidence chains |

You'll need the channel IDs for these — see [Getting channel IDs](#getting-channel-ids) below.

---

## Prerequisites

Before installing, you need:

1. **Python 3.10 or newer** — check with `python3 --version`
2. **A Discord bot token** — see [Creating your Discord bot](#creating-your-discord-bot) below
3. **Ollama** — the local AI model runner. Download from [ollama.com](https://ollama.com)

---

## Creating your Discord bot

If you've never made a Discord bot before:

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) and click **New Application**. Name it whatever you want.
2. In the left sidebar, click **Bot**.
3. Click **Reset Token** and copy the token somewhere safe. This is your `DISCORD_BOT_TOKEN`. Treat it like a password.
4. Scroll down to **Privileged Gateway Intents** and enable all three:
   - Server Members Intent
   - Message Content Intent
   - Presence Intent
5. In the left sidebar, click **OAuth2**, then **URL Generator**.
6. Under **Scopes**, check `bot`.
7. Under **Bot Permissions**, check: `Read Messages/View Channels`, `Send Messages`, `Read Message History`, `Add Reactions`.
8. Copy the generated URL, paste it in your browser, and invite the bot to your server.

---

## Getting channel IDs

In Discord, you need to enable **Developer Mode** to see channel IDs:

1. Open Discord settings → **Advanced** → turn on **Developer Mode**.
2. Right-click any channel name → **Copy Channel ID**.

Do this for each of your three channels (`#agent-coordination`, `#transparency-log`, `#mod-reports`).

---

## Install

### 1. Install Python dependencies

```bash
pip install discord.py aiohttp
```

### 2. Install and start Ollama

Download Ollama from [ollama.com](https://ollama.com), install it, then run:

```bash
ollama serve        # starts the Ollama server (keep this running)
ollama pull llama3.2:1b   # downloads the model (~1.3GB, one-time)
```

Ollama needs to be running (`ollama serve`) any time you run the bot. You can test it's working with:

```bash
ollama run llama3.2:1b "Say hello"
```

### 3. Build the training dataset (optional but recommended)

This generates the training data that helps the Tactics Reference agent recognize patterns. Run it once before starting the bot:

```bash
python build_dataset.py
```

It will create `datasets/train.jsonl` and `datasets/val.jsonl`. If you want to add your own observed examples, open `build_dataset.py` and add entries to the `TRAINING_EXAMPLES` list — the format is documented at the top of that file.

### 4. Set your environment variables

The bot reads all its configuration from environment variables. Set them before running:

**On Linux/macOS:**
```bash
export DISCORD_BOT_TOKEN=your_token_here
export AGENT_COORD_CHANNEL_ID=123456789012345678
export PUBLIC_CHANNEL_ID=123456789012345679
export MOD_CHANNEL_ID=123456789012345680
export TRIGGER_MESSAGE_COUNT=20
export ANALYSIS_INTERVAL_SECS=300
```

**On Windows (Command Prompt):**
```cmd
set DISCORD_BOT_TOKEN=your_token_here
set AGENT_COORD_CHANNEL_ID=123456789012345678
set PUBLIC_CHANNEL_ID=123456789012345679
set MOD_CHANNEL_ID=123456789012345680
set TRIGGER_MESSAGE_COUNT=20
set ANALYSIS_INTERVAL_SECS=300
```

Or create a `.env` file and load it with a tool like `python-dotenv` (add `from dotenv import load_dotenv; load_dotenv()` to the top of `discord_bot.py`).

**What these settings do:**

| Variable | Default | Description |
|---|---|---|
| `DISCORD_BOT_TOKEN` | *(required)* | Your bot token from the Discord developer portal |
| `AGENT_COORD_CHANNEL_ID` | *(required)* | Channel ID for the hidden audit log |
| `PUBLIC_CHANNEL_ID` | *(required)* | Channel ID for public anonymized notices |
| `MOD_CHANNEL_ID` | *(required)* | Channel ID for moderator case files |
| `TRIGGER_MESSAGE_COUNT` | `20` | How many messages to buffer before running analysis |
| `ANALYSIS_INTERVAL_SECS` | `300` | How often (seconds) to run a scheduled pass (300 = every 5 min) |

### 5. Run the bot

Make sure Ollama is running in one terminal, then in another:

```bash
python discord_bot.py
```

You should see output like:
```
2025-01-15 12:00:00 [INFO] watchdog.discord: Watchdog online as YourBot#1234
2025-01-15 12:00:00 [INFO] watchdog.discord:   Channel [agent_coord] → #agent-coordination
2025-01-15 12:00:00 [INFO] watchdog.discord:   Channel [public] → #transparency-log
2025-01-15 12:00:00 [INFO] watchdog.discord:   Channel [mod] → #mod-reports
```

If you see `NOT FOUND` next to a channel name, double-check that channel ID.

Logs are also written to `watchdog.log` in the same directory.

---

## Optional: Web UI for agent management

There's a Flask web interface for viewing and adjusting agent configuration (thresholds, which agents are active, etc.).

```bash
cd ui
pip install -r requirements.txt
python app.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

This runs separately from the bot. You don't need it to run the bot — it's just a management dashboard.

---

## Understanding the output

### Public notice (in `#transparency-log`)

An embed with:
- A color-coded confidence indicator (🟡 SPECULATIVE / 🟠 CORROBORATED / 🔴 CONFIRMED)
- A brief description of what was observed — no usernames, no user IDs
- The estimated false positive rate
- A list of alternate innocent explanations that were considered
- A ticket ID that any user can reference if they believe they were flagged in error
- A footer confirming no automated action was taken

### Moderator case file (in `#mod-reports`)

The full picture:
- Coordination signals detected, with confidence scores
- Historical pattern matches from the tactics library, with source citations
- Chronological evidence timeline (message IDs only, no content)
- Alternate explanations (always included)
- Account information — **only at CONFIRMED tier**, and only as hashed IDs. Raw account IDs can be looked up from the audit log.
- A moderator action checklist

### Agent audit log (in `#agent-coordination`)

A JSON summary of each completed pipeline run — what each agent decided, how many signals were found, the final confidence tier, and the round count. This channel is the paper trail.

---

## Confidence tiers

| Tier | What it means | Account IDs in report |
|---|---|---|
| `SPECULATIVE` | Single signal; many plausible innocent explanations | Withheld |
| `CORROBORATED` | 2+ independent signals, or a signal + tactic match | Withheld (use audit log) |
| `CONFIRMED` | 3+ signals, 2+ tactic matches, average confidence ≥65% | Hashed IDs included |

Moderators should treat CONFIRMED tickets with greater concern but still work through the checklist before taking any action. The system does not take action at any tier.

---

## Due process path

Any user who believes they were flagged in error can:

1. Find the ticket ID from the notice in `#transparency-log`
2. Reference that ticket ID when messaging moderators
3. Moderators can pull the full evidence chain from the audit log and review the reasoning

The evidence chain is preserved indefinitely in `#agent-coordination`.

---

## Moderator checklist (always included in every case file)

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

## Adjusting sensitivity

If the bot is firing too often (or not enough), adjust these:

**Too sensitive (too many tickets):**
- Raise `TRIGGER_MESSAGE_COUNT` (analyze less frequently by message count)
- Raise `ANALYSIS_INTERVAL_SECS` (analyze less frequently on schedule)
- In `agents.py`, raise `AgentOrchestrator.MIN_SCORE_TO_ADVANCE` above `0.25`

**Not sensitive enough:**
- Lower `TRIGGER_MESSAGE_COUNT` or `ANALYSIS_INTERVAL_SECS`
- Lower `MIN_SCORE_TO_ADVANCE`

You can also adjust the per-agent thresholds through the web UI (`ui/app.py`), which writes to `ui/agent_config.json`.

---

## Adding your own tactics patterns

Open `build_dataset.py` and add entries to `TRAINING_EXAMPLES`. Each entry needs:

- `signals_observed` — what signal types were seen (from `SIGNAL_TYPE_TAXONOMY` in `tactics_library.py`)
- `signal_descriptions` — human-readable descriptions of what you observed
- `correct_tactic_id` and `correct_tactic_name` — the closest match from the tactics library
- `match_confidence` and `false_positive_likelihood` — your assessment
- `alternate_explanations` — **required, must be non-empty** — innocent explanations for what you saw
- `label` — `"disruption"`, `"false_positive"`, or `"ambiguous"`

Sanitize all examples before adding: no real usernames, no server-specific identifiers, no content from actual messages.

After adding examples, re-run `python build_dataset.py` to regenerate the training dataset.

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

## Historical sources for the tactics library

Tactic entries in `tactics_library.py` cite their sources inline. Primary sources:

- **Church Committee Final Report** (1976) — Senate Select Committee to Study Governmental Operations with Respect to Intelligence Activities. Books II & III. Public domain, available at archive.org.
- **Frank Donner, "The Age of Surveillance"** (1980) — comprehensive taxonomy of domestic intelligence disruption methods
- **Brian Glick, "War at Home"** (1989) — practical guide to COINTELPRO tactics written for organizers. Short and worth reading.
- **RAND Corporation influence operations research** (2016–2023) — "Firehose of Falsehood" and related reports, all public at rand.org
- **Stanford Internet Observatory** — "Repeat Offenders," "Unheard Voice," and other published reports. Free at cyber.fsi.stanford.edu.
- **EU DisinfoLab** — "Indian Chronicles," "Anti-EU Disinformation," other published influence network analyses
- **Senate Intelligence Committee, Vol. 2** (2019) — Russian active measures report

---

## Suggested reading for moderators

- Glick, Brian. *War at Home* (1989) — short, practical, written for organizers
- Church Committee Final Report, Book III (1976) — primary source, free at archive.org
- Stanford Internet Observatory published reports — free at cyber.fsi.stanford.edu
- RAND, "The Russian Firehose of Falsehood" (2016) — free at rand.org

---

## Troubleshooting

**Bot comes online but channels show `NOT FOUND`**
Double-check that you copied the channel IDs correctly (they should be 18-digit numbers), that Developer Mode is enabled in Discord, and that the bot has permission to see those channels.

**Analysis runs but nothing posts**
Most likely the coordination score is below 0.25 and tickets are being dismissed — this is normal for healthy servers. Check `watchdog.log` for lines like `Score 0.12 below threshold, closing TKT-XXXXXXXX`.

**Ollama errors in the log**
Make sure `ollama serve` is running in a separate terminal. The bot will fall back to default values if Ollama is unavailable, but tactic matching quality will be reduced.

**`DISCORD_BOT_TOKEN environment variable not set` error**
The bot requires this variable to start. Make sure you've exported it in the same terminal session where you're running the bot.

**Bot is posting too many notices**
Raise `TRIGGER_MESSAGE_COUNT` or `MIN_SCORE_TO_ADVANCE` in `agents.py`. See [Adjusting sensitivity](#adjusting-sensitivity).
