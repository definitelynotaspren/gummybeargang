"""
Training Dataset — Disruptor Pattern Recognition
=================================================
Sourced from:
  - Church Committee Final Report (1976), Books II & III
  - Frank Donner, "The Age of Surveillance" (1980)
  - Brian Glick, "War at Home" (1989)
  - RAND Corporation influence operations research (2016–2023)
  - Stanford Internet Observatory published reports (2019–2023)
  - EU DisinfoLab published reports (2019–2022)
  - Academic literature on coordinated inauthentic behavior

FORMAT: Each example is a JSONL training record for the Tactics Reference Agent.
The agent receives coordination signals and must:
  1. Identify which historical tactic it resembles
  2. Assign a confidence score
  3. Populate alternate_explanations (REQUIRED, non-empty)

HOW TO ADD YOUR OWN EXAMPLES:
  - Observe a pattern in your community
  - Sanitize: no real usernames, no server-specific identifiers
  - Describe it structurally (timing, account properties, behavior type)
  - Add to TRAINING_EXAMPLES below
  - Run: python build_dataset.py
"""

import json
import random
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TacticsTrainingExample:
    signals_observed: list[str]          # coordination signal types from Agent 1
    signal_descriptions: list[str]       # human-readable descriptions
    correct_tactic_id: str               # from SIGNAL_TYPE_TAXONOMY
    correct_tactic_name: str
    match_confidence: float              # 0.0–1.0
    false_positive_likelihood: float     # 0.0–1.0
    alternate_explanations: list[str]    # MUST be non-empty
    historical_note: str                 # source citation
    label: str                           # "disruption" | "false_positive" | "ambiguous"


TRAINING_EXAMPLES: list[TacticsTrainingExample] = [

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY: Coordinated Timing / Synchronized Posting
    # ══════════════════════════════════════════════════════════════════════════

    TacticsTrainingExample(
        signals_observed=["synchronized_timing", "template_language"],
        signal_descriptions=[
            "5 accounts posted within 18 seconds of each other targeting the same announcement",
            "Three of the five posts used the phrase 'this is suspicious' with identical punctuation",
        ],
        correct_tactic_id="INF-OPS-001",
        correct_tactic_name="Narrative Flooding",
        match_confidence=0.78,
        false_positive_likelihood=0.18,
        alternate_explanations=[
            "Community members all received the same push notification simultaneously",
            "A popular streamer or podcast mentioned the announcement at the same time",
            "Users were already in a voice chat together and reacted at the same time",
            "A pinged role caused simultaneous notification to many users",
        ],
        historical_note=(
            "Mirrors documented reply storm tactics in Stanford Internet Observatory "
            "'Repeat Offenders' (2021): coordinated reply networks timed to announcement posts."
        ),
        label="disruption",
    ),

    TacticsTrainingExample(
        signals_observed=["synchronized_timing"],
        signal_descriptions=[
            "8 accounts posted within 25 seconds — all replying to same event announcement",
        ],
        correct_tactic_id="INF-OPS-001",
        correct_tactic_name="Narrative Flooding",
        match_confidence=0.35,
        false_positive_likelihood=0.72,
        alternate_explanations=[
            "Discord sent a @everyone or @here ping — all members notified simultaneously",
            "The announcement was cross-posted to multiple servers and members saw it at once",
            "Organic excitement causing fast response to a major announcement",
            "Server boost or role ping caused simultaneous notification",
        ],
        historical_note=(
            "Timing alone is weak evidence. Sub-30-second clusters are common whenever "
            "Discord sends a role ping or @everyone notification. "
            "See Stanford SIO note on false positive rates for timing-only signals."
        ),
        label="false_positive",
    ),

    TacticsTrainingExample(
        signals_observed=["synchronized_timing", "cluster_arrival", "template_language"],
        signal_descriptions=[
            "7 accounts joined within a 6-hour window 3 weeks ago",
            "Those same 7 accounts posted within 40 seconds targeting a coalition announcement",
            "5 of the 7 used the phrase 'who even voted for this' without attribution",
        ],
        correct_tactic_id="COORD-001",
        correct_tactic_name="Off-Platform Coordination Bleed-Through",
        match_confidence=0.82,
        false_positive_likelihood=0.14,
        alternate_explanations=[
            "Friend group that joined together after a mutual contact recommended the server",
            "Members from another server who all saw an invite post simultaneously",
            "Participants from a related event or class who joined together",
        ],
        historical_note=(
            "Cluster arrival + identical phrasing + coordinated timing is the "
            "tri-signal pattern documented in EU DisinfoLab 'Indian Chronicles' (2020) "
            "and RAND 'Measuring the Information Environment' (2020) as the strongest "
            "structural indicator of off-platform organization."
        ),
        label="disruption",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY: Factionalization / Wedge Tactics
    # ══════════════════════════════════════════════════════════════════════════

    TacticsTrainingExample(
        signals_observed=["template_language", "cross_account_terminology"],
        signal_descriptions=[
            "Identical framing ('the real problem is internal conflict between X and Y groups') "
            "appeared across 4 accounts with no prior interaction history",
            "The framing appeared within 2 hours of a major coalition announcement",
        ],
        correct_tactic_id="WDG-001",
        correct_tactic_name="Factionalization / Divide and Conquer",
        match_confidence=0.75,
        false_positive_likelihood=0.22,
        alternate_explanations=[
            "Multiple community members independently identified the same genuine tension",
            "An external article or post raised this framing and multiple people read it",
            "Legitimate ideological disagreement that several people articulate similarly",
        ],
        historical_note=(
            "Church Committee Report Book III pp. 187–190 documents COINTELPRO using "
            "identical talking points distributed across infiltrators to create appearance "
            "of organic factionalization. The key structural tell is identical non-obvious "
            "framing across accounts with no prior interaction."
        ),
        label="disruption",
    ),

    TacticsTrainingExample(
        signals_observed=["escalation_pattern"],
        signal_descriptions=[
            "Single user consistently frames tactical disagreements as identity-based "
            "conflicts across 15 posts over 3 weeks",
        ],
        correct_tactic_id="WDG-001",
        correct_tactic_name="Factionalization / Divide and Conquer",
        match_confidence=0.28,
        false_positive_likelihood=0.81,
        alternate_explanations=[
            "Genuine community member who has experienced identity-based exclusion",
            "Someone with strong ideological views about intersectionality in organizing",
            "Person who has read specific theory and applies that lens consistently",
            "Legitimate internal critic with a coherent perspective",
        ],
        historical_note=(
            "Single-account factionalization framing is almost always legitimate "
            "internal debate. The Church Committee pattern required coordinated "
            "distribution across multiple infiltrators — single actors expressing "
            "a consistent viewpoint are not meaningful signals."
        ),
        label="false_positive",
    ),

    TacticsTrainingExample(
        signals_observed=["defamation_timing", "template_language", "synchronized_timing"],
        signal_descriptions=[
            "Three accounts with no prior interaction made identical allegations about "
            "a community leader within 90 minutes of a major membership vote",
            "None of the accounts provided verifiable sources",
            "Accounts had joined within 48 hours of each other 5 weeks prior",
        ],
        correct_tactic_id="WDG-002",
        correct_tactic_name="Leadership Defamation",
        match_confidence=0.88,
        false_positive_likelihood=0.09,
        alternate_explanations=[
            "Multiple community members independently discovered the same concern",
            "A genuine news story published around the same time",
            "Friends who coordinated to raise a real accountability concern",
        ],
        historical_note=(
            "Church Committee Report Book III pp. 220–223 documents FBI sending "
            "coordinated anonymous allegations to MLK's wife and media contacts. "
            "The structural signature — synchronized, unverified allegations timed "
            "to high-stakes moments — is historically consistent. "
            "This is the highest-confidence signal in the library."
        ),
        label="disruption",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY: Persona Construction / Identity
    # ══════════════════════════════════════════════════════════════════════════

    TacticsTrainingExample(
        signals_observed=["account_age_activity_gap"],
        signal_descriptions=[
            "Account joined 8 days ago, has posted 47 times in the last 6 hours, "
            "all in high-visibility channels during a campaign launch",
        ],
        correct_tactic_id="INF-001",
        correct_tactic_name="Persona Construction",
        match_confidence=0.32,
        false_positive_likelihood=0.74,
        alternate_explanations=[
            "New member who is genuinely enthusiastic about the campaign",
            "Someone who joined specifically because of the launch announcement",
            "A person with more free time than average new members",
            "Someone who discovered the server through the campaign and is highly engaged",
        ],
        historical_note=(
            "Account age + activity mismatch alone is very weak evidence. "
            "New member enthusiasm is the most common explanation. "
            "This signal only becomes meaningful in combination with "
            "synchronized timing or template language signals."
        ),
        label="false_positive",
    ),

    TacticsTrainingExample(
        signals_observed=["account_age_activity_gap", "synchronized_timing", "cluster_arrival"],
        signal_descriptions=[
            "4 accounts joined within 12 hours of each other 10 days ago",
            "All 4 have posting patterns concentrated in 2-hour windows that do not "
            "correspond to any announced community event",
            "Posting windows are nearly identical across all 4 accounts",
        ],
        correct_tactic_id="INF-001",
        correct_tactic_name="Persona Construction",
        match_confidence=0.67,
        false_positive_likelihood=0.31,
        alternate_explanations=[
            "Friend group with similar schedules who joined together",
            "Members from a different time zone with overlapping free time",
            "People who joined from the same workplace or school",
        ],
        historical_note=(
            "Glick (1989) pp. 10–14 on COINTELPRO infiltration: agents were often "
            "assigned to join in small groups to provide mutual cover. "
            "The tri-signal combination (cluster arrival + age gap + posting pattern "
            "synchrony) is more meaningful than any single signal."
        ),
        label="ambiguous",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY: Rules Weaponization / Coordinated Reporting
    # ══════════════════════════════════════════════════════════════════════════

    TacticsTrainingExample(
        signals_observed=["coordinated_reporting", "template_language"],
        signal_descriptions=[
            "6 accounts filed reports against the same user within 8 minutes",
            "4 of the 6 reports used identical language: 'this user is spreading misinformation'",
            "The targeted user had just posted a thread criticizing a policy position",
        ],
        correct_tactic_id="INF-OPS-003",
        correct_tactic_name="Rules Weaponization / Bad-Faith Proceduralism",
        match_confidence=0.84,
        false_positive_likelihood=0.12,
        alternate_explanations=[
            "A moderator asked community members to report a specific violation",
            "Multiple people independently noticed a genuine rule violation",
            "A community member publicly called for others to report the post",
        ],
        historical_note=(
            "Coordinated mass-reporting of activists documented extensively: "
            "Platform transparency reports 2018–2022 documented coordinated campaigns "
            "against LGBTQ+ creators, BLM organizers, and labor organizers. "
            "Citron (2014) 'Hate Crimes in Cyberspace' pp. 26–34. "
            "Identical report language is the key structural tell — independent "
            "reporters use different phrasing."
        ),
        label="disruption",
    ),

    TacticsTrainingExample(
        signals_observed=["coordinated_reporting"],
        signal_descriptions=[
            "4 accounts reported the same post within 20 minutes",
            "The post contained content that appeared to violate community rules",
        ],
        correct_tactic_id="INF-OPS-003",
        correct_tactic_name="Rules Weaponization / Bad-Faith Proceduralism",
        match_confidence=0.20,
        false_positive_likelihood=0.85,
        alternate_explanations=[
            "Multiple people genuinely noticed the same rule violation",
            "A community member publicly flagged the post and others followed",
            "The post was visible in a busy channel seen by many people simultaneously",
            "The platform's reporting feature prompted others after the first report",
        ],
        historical_note=(
            "Multiple reports of a single post are often organic — especially "
            "for genuinely violating content. Timing alone without identical "
            "language or other signals is very weak evidence."
        ),
        label="false_positive",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY: Engagement Velocity / Amplification
    # ══════════════════════════════════════════════════════════════════════════

    TacticsTrainingExample(
        signals_observed=["engagement_velocity", "synchronized_timing"],
        signal_descriptions=[
            "A single post received 34 reactions within 90 seconds",
            "22 of the reactor accounts had fewer than 10 prior posts in this server",
            "The post argued against a upcoming community vote",
        ],
        correct_tactic_id="COORD-002",
        correct_tactic_name="Controlled Velocity Amplification",
        match_confidence=0.71,
        false_positive_likelihood=0.28,
        alternate_explanations=[
            "Post was shared to an external community whose members reacted",
            "The post touched on a topic many lurkers care about",
            "Cross-server announcement that brought in temporary viewers",
        ],
        historical_note=(
            "Senate Intelligence Committee Vol. 2 (2019) pp. 47–62 documents "
            "IRA operations using low-activity amplifier accounts to boost content "
            "above algorithmic thresholds. Low-activity reactor accounts "
            "are the key signal — organic reactions come from active community members."
        ),
        label="ambiguous",
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # CATEGORY: Concern Trolling / Strategic Pessimism
    # ══════════════════════════════════════════════════════════════════════════

    TacticsTrainingExample(
        signals_observed=["negative_pattern"],
        signal_descriptions=[
            "User has posted 38 times over 2 weeks; 35 posts express doubt or "
            "pessimism about campaigns; user has never offered an alternative suggestion",
        ],
        correct_tactic_id="INF-OPS-002",
        correct_tactic_name="Strategic Concern Trolling",
        match_confidence=0.22,
        false_positive_likelihood=0.87,
        alternate_explanations=[
            "Genuine strategic pessimist who cares about the movement",
            "Person who has experienced prior movement failure and is cautious",
            "Someone with anxiety affecting how they communicate",
            "Legitimate internal critic with a coherent viewpoint",
            "Someone who expresses care through caution rather than enthusiasm",
        ],
        historical_note=(
            "Strategic pessimism/concern trolling is the hardest tactic to distinguish "
            "from genuine internal critique. Glick (1989) pp. 20–23 notes that "
            "psychological warfare often mimics authentic dissent. "
            "This signal MUST NOT advance a ticket alone — it requires corroboration "
            "from coordination signals to be meaningful."
        ),
        label="false_positive",
    ),

    TacticsTrainingExample(
        signals_observed=[
            "negative_pattern", "synchronized_timing", "cross_account_terminology"
        ],
        signal_descriptions=[
            "3 accounts with no prior interaction all posted defeatist framing "
            "('this will never work, just like last time') within 10 minutes of "
            "a campaign fundraising milestone being announced",
            "Identical phrase 'just like last time' used by all three without prior "
            "discussion of what 'last time' refers to",
        ],
        correct_tactic_id="INF-OPS-002",
        correct_tactic_name="Strategic Concern Trolling",
        match_confidence=0.74,
        false_positive_likelihood=0.21,
        alternate_explanations=[
            "Community members who all experienced the same prior failure",
            "A recent discussion about past failures that multiple people absorbed",
            "Genuine shared discouragement at a similar moment",
        ],
        historical_note=(
            "Donner (1980) pp. 200–209 documents organized demoralization campaigns "
            "designed to suppress fundraising and recruitment momentum. "
            "The structural tell is: identical non-obvious phrasing across "
            "accounts with no shared prior conversation, timed to momentum moments."
        ),
        label="disruption",
    ),

]


# ─── Build JSONL ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a civil rights history researcher specializing in documented
disruption tactics. Given coordination signals, identify which historical tactics they
resemble and provide plausible innocent explanations. Always err toward innocent
explanations. Respond only with JSON."""

def format_example(ex: TacticsTrainingExample) -> dict:
    user_content = f"""Coordination signals observed: {json.dumps(ex.signals_observed)}

Signal descriptions:
{chr(10).join(f'  - {d}' for d in ex.signal_descriptions)}

Assess which historical disruption tactic this most resembles, and provide alternate explanations.

Respond with JSON:
{{
  "tactic_id": "{ex.correct_tactic_id}",
  "tactic_name": "...",
  "match_confidence": 0.0-1.0,
  "match_reasoning": "one sentence",
  "additional_alternate_explanations": ["...", "..."],
  "false_positive_likelihood": 0.0-1.0
}}"""

    assistant_content = json.dumps({
        "tactic_id": ex.correct_tactic_id,
        "tactic_name": ex.correct_tactic_name,
        "match_confidence": ex.match_confidence,
        "match_reasoning": ex.historical_note[:200],
        "additional_alternate_explanations": ex.alternate_explanations,
        "false_positive_likelihood": ex.false_positive_likelihood,
    }, ensure_ascii=False)

    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        "_meta": {
            "label":   ex.label,
            "tactic":  ex.correct_tactic_id,
        }
    }


def build_and_write(out_dir: Path, augment: bool = False):
    records = [format_example(ex) for ex in TRAINING_EXAMPLES]
    random.shuffle(records)

    split = int(len(records) * 0.85)
    train, val = records[:split], records[split:]

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, subset in [("train", train), ("val", val)]:
        path = out_dir / f"{name}.jsonl"
        with open(path, "w") as f:
            for r in subset:
                f.write(json.dumps(r) + "\n")
        print(f"  ✓ {path} ({len(subset)} records)")

    # Class balance report
    from collections import Counter
    labels = Counter(r["_meta"]["label"] for r in records)
    print(f"\n  Label distribution:")
    for label, count in sorted(labels.items()):
        bar = "█" * (count * 20 // max(labels.values()))
        print(f"    {label:15s} {count:3d}  {bar}")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="datasets")
    args = parser.parse_args()
    print("Building tactics reference training dataset...")
    build_and_write(Path(args.out))
