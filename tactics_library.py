"""
Historical Disruption Tactics Reference Library
================================================
Sourced from:
  - Church Committee Final Report, 1976 (Senate Select Committee to Study
    Governmental Operations with Respect to Intelligence Activities)
  - Frank Donner, "The Age of Surveillance" (1980)
  - Brian Glick, "War at Home: Covert Action Against U.S. Activists" (1989)
  - RAND Corporation influence operations research (2019–2023)
  - Stanford Internet Observatory reports on coordinated inauthentic behavior
  - EU DisinfoLab reports on influence networks
  - Academic literature on GamerGate, BLM counter-campaigns, labor disruption

This library is used by Agent 2 (Tactics Reference) to match observed behavioral
signals against documented historical patterns. Each tactic entry REQUIRES a
non-empty alternate_explanations list — the agent must populate this field
before the ticket can advance.

IMPORTANT DESIGN NOTE:
These patterns describe STRUCTURAL and COORDINATION behaviors, not content or
ideology. The same structural signals appear regardless of which direction a
disruption campaign is running. This tool does not classify political content.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class HistoricalTactic:
    tactic_id: str
    name: str
    category: str
    description: str
    historical_sources: list[str]
    behavioral_indicators: list[str]   # what to look for in metadata/structure
    alternate_explanations: list[str]  # REQUIRED — innocent explanations
    coordination_score_weight: float   # how much this raises the score (0.0–1.0)
    requires_multiple_accounts: bool   # single-account or coordinated?
    notes: str = ""


TACTICS_LIBRARY: list[HistoricalTactic] = [

    # ── Category: Identity & Infiltration ────────────────────────────────────

    HistoricalTactic(
        tactic_id="INF-001",
        name="Persona Construction",
        category="identity_infiltration",
        description=(
            "Creation of synthetic or exaggerated personas designed to appear as "
            "authentic community members, often with fabricated histories and "
            "manufactured credibility signals. Documented extensively in COINTELPRO "
            "operations where agents posed as movement members."
        ),
        historical_sources=[
            "Church Committee Report, Book III, pp. 3-77: 'COINTELPRO — The FBI's "
            "Covert Action Programs Against American Citizens'",
            "Glick (1989), pp. 10-14: 'Infiltration'",
            "Stanford Internet Observatory, 'Unheard Voice' (2022): coordinated "
            "inauthentic behavior across 30 countries",
        ],
        behavioral_indicators=[
            "Account join date significantly predates first activity burst",
            "Profile history shows sudden shift in community focus",
            "Posting history is abnormally consistent in tone/schedule",
            "Account lacks organic social graph (few mutual connections with genuine members)",
            "Bio/profile claims inconsistent with behavioral metadata",
        ],
        alternate_explanations=[
            "Genuine long-time lurker who recently became active",
            "User changed interests or communities",
            "New user who researched the community before joining",
            "Someone recovering from a period of low social media use",
            "Someone who prefers consistency in posting habits",
        ],
        coordination_score_weight=0.3,
        requires_multiple_accounts=False,
        notes="Lowest weight of any signal — account age patterns alone are very weak evidence.",
    ),

    HistoricalTactic(
        tactic_id="INF-002",
        name="Agent Provocateur / Escalation Seeding",
        category="identity_infiltration",
        description=(
            "Infiltrating a community to encourage illegal, extreme, or "
            "embarrassing actions that discredit the broader movement. Documented "
            "in COINTELPRO operations against SCLC, AIM, and labor unions. The "
            "goal is to generate footage, quotes, or incidents that delegitimize "
            "the group externally."
        ),
        historical_sources=[
            "Church Committee Report, Book III, pp. 185-223",
            "Donner (1980), Ch. 5: 'The Techniques of Domestic Intelligence'",
            "Ward Churchill & Jim Vander Wall, 'The COINTELPRO Papers' (1990), "
            "pp. 92-116",
        ],
        behavioral_indicators=[
            "User consistently escalates peaceful discussions toward confrontational framing",
            "Suggestions that push toward illegal or extreme action appear specifically "
            "when moderation/observers are likely present",
            "Pattern of being first to advocate for tactics the broader community "
            "has not endorsed",
            "Escalation attempts increase in frequency before known public events",
        ],
        alternate_explanations=[
            "Genuine frustration with pace of change producing impatient advocacy",
            "Philosophical disagreement about tactics within the movement",
            "Someone who has not read community norms",
            "Radicalization that is organic to the individual",
        ],
        coordination_score_weight=0.55,
        requires_multiple_accounts=False,
        notes=(
            "This tactic is performed by single accounts. Distinguishing genuine "
            "internal disagreement from planted escalation requires pattern over time, "
            "not single-instance judgment."
        ),
    ),

    # ── Category: Wedge Operations ───────────────────────────────────────────

    HistoricalTactic(
        tactic_id="WDG-001",
        name="Factionalization / Divide and Conquer",
        category="wedge_operations",
        description=(
            "Deliberately amplifying internal divisions — racial, ideological, "
            "tactical, or personal — to fragment coalition cohesion. COINTELPRO "
            "sent forged letters between Black Panther chapters, fabricated "
            "conflicts between SNCC and SCLC leadership, and manufactured "
            "evidence of infidelity to undermine leaders."
        ),
        historical_sources=[
            "Church Committee Report, Book III, pp. 187-190: 'Efforts to Promote "
            "Enmity and Discord'",
            "Glick (1989), pp. 14-17: 'Promoting Conflicts'",
            "FBI memo to field offices, 3/4/1968 (declassified): instructions to "
            "'create factionalism' in Black nationalist organizations",
        ],
        behavioral_indicators=[
            "User consistently introduces or amplifies identity-based tensions "
            "regardless of the topic at hand",
            "Posts selectively to inflame specific subgroups while maintaining "
            "different personas with others",
            "Timing of divisive posts correlates with coalition-building moments "
            "(announcements, events, votes)",
            "Identical divisive talking points appear across otherwise-unconnected accounts",
            "Quotes attributed to community leaders that members cannot verify",
        ],
        alternate_explanations=[
            "Genuine ideological disagreement about coalition strategy",
            "Real interpersonal conflict between community members",
            "Someone expressing legitimate frustrations about representation",
            "Organic debate about tactical priorities",
            "Different lived experiences producing different strategic assessments",
        ],
        coordination_score_weight=0.6,
        requires_multiple_accounts=True,
        notes=(
            "Single-account factionalization is almost always legitimate internal "
            "debate. Coordination signal requires the IDENTICAL talking points across "
            "multiple accounts — that's the structural tell."
        ),
    ),

    HistoricalTactic(
        tactic_id="WDG-002",
        name="Leadership Defamation",
        category="wedge_operations",
        description=(
            "Targeting movement leaders with fabricated or exaggerated personal "
            "attacks — affairs, financial misconduct, hypocrisy — to discredit "
            "them and demoralize their base. The FBI sent an anonymous letter to "
            "MLK threatening to expose recordings unless he resigned, and sent "
            "forged letters to his wife."
        ),
        historical_sources=[
            "Church Committee Report, Book III, pp. 220-223: 'Dr. Martin Luther "
            "King, Jr.: Case Study'",
            "Donner (1980), pp. 214-221",
            "Glick (1989), pp. 17-20: 'Harassment and Psychological Warfare'",
        ],
        behavioral_indicators=[
            "Coordinated appearance of identical allegations across multiple accounts "
            "in short time window",
            "Allegations timed to coincide with high-visibility moments (launches, "
            "elections, public appearances)",
            "Claims that cannot be verified and are not attributed to checkable sources",
            "Pattern of targeting the same individual across platforms simultaneously",
            "Accounts with no other community engagement appearing specifically to post allegations",
        ],
        alternate_explanations=[
            "Genuine accountability concerns about a public figure",
            "Organic spread of a real news story",
            "Community members independently sharing the same concern",
            "Journalism that has gained traction",
        ],
        coordination_score_weight=0.7,
        requires_multiple_accounts=True,
        notes=(
            "HIGHEST weight in this category because the simultaneous cross-platform "
            "and timing-correlated version has very few innocent explanations. "
            "Single-account criticism of leaders is almost always legitimate and "
            "should never be flagged."
        ),
    ),

    # ── Category: Information Environment Manipulation ───────────────────────

    HistoricalTactic(
        tactic_id="INF-OPS-001",
        name="Narrative Flooding",
        category="information_environment",
        description=(
            "High-volume injection of off-topic, misleading, or exhausting content "
            "to drown out legitimate discussion. In modern contexts this includes "
            "coordinated reply storms on key announcements. Related to Soviet "
            "'firehose of falsehood' doctrine documented by RAND (2016) and to "
            "documented GamerGate harassment targeting coordination."
        ),
        historical_sources=[
            "RAND Corporation, 'The Russian 'Firehose of Falsehood' Propaganda Model' (2016)",
            "Stanford Internet Observatory, 'Repeat Offenders' (2021): coordinated "
            "reply networks",
            "EU DisinfoLab, 'Indian Chronicles' (2020): synthetic amplification networks",
            "Researchers Massanari (2017) and Marwick (2018) on GamerGate coordination",
        ],
        behavioral_indicators=[
            "Synchronized posting bursts from multiple accounts within narrow time windows (< 30s)",
            "Volume spike on specific topics that does not correlate with external news events",
            "Identical or near-identical language across accounts with no attribution",
            "Reply chains targeting specific community announcements within seconds",
            "Engagement metrics inconsistent with account follower counts or history",
        ],
        alternate_explanations=[
            "Organic viral moment where many people respond simultaneously",
            "Cross-posted announcement bringing users from another server",
            "A news event affecting the community at the same time",
            "A reminder or ping that caused simultaneous notification to many users",
            "Bot activity from legitimate server tools (welcome bots, announcement bots)",
        ],
        coordination_score_weight=0.65,
        requires_multiple_accounts=True,
        notes=(
            "Timing analysis is the key signal here. Humans typing and posting "
            "independently will have variable inter-message gaps (typically 45s–5min). "
            "Sub-30-second synchronized bursts from accounts with no prior interaction "
            "are structurally anomalous."
        ),
    ),

    HistoricalTactic(
        tactic_id="INF-OPS-002",
        name="Strategic Concern Trolling",
        category="information_environment",
        description=(
            "Posing as sympathetic to a movement while consistently introducing "
            "doubt, pessimism, or 'just asking questions' framing designed to "
            "demoralize members and discourage action. Distinct from genuine "
            "strategic disagreement by its pattern: no constructive alternatives "
            "are ever offered, and the user always surfaces at high-stakes moments."
        ),
        historical_sources=[
            "Glick (1989), pp. 20-23: 'Psychological Warfare'",
            "Donner (1980), pp. 200-209",
            "Academic: Whitney Phillips, 'This Is Why We Can't Have Nice Things' (2015)",
        ],
        behavioral_indicators=[
            "Consistent pattern of negative framing across many unrelated issues",
            "Questions that introduce doubt never followed by engagement with answers",
            "Timing of pessimistic posts correlates with momentum-building announcements",
            "User claims solidarity but engagement record shows no positive contributions",
            "Pattern repeats across ticket-level events (announcements, campaigns, votes)",
        ],
        alternate_explanations=[
            "Genuine strategic pessimist who cares about the movement",
            "Someone who has experienced burnout or prior movement failures",
            "Legitimate critic who finds constructive framing difficult",
            "Person with anxiety or depression affecting their communication",
            "Someone who expresses concern differently than community norms expect",
        ],
        coordination_score_weight=0.35,
        requires_multiple_accounts=False,
        notes=(
            "Lowest-weight single-account tactic. Concern trolling is extremely "
            "difficult to distinguish from genuine pessimism. This signal should "
            "NEVER advance a ticket alone — it must appear alongside coordination "
            "signals from Agent 1 to be meaningful."
        ),
    ),

    HistoricalTactic(
        tactic_id="INF-OPS-003",
        name="Rules Weaponization / Bad-Faith Proceduralism",
        category="information_environment",
        description=(
            "Exploiting community rules, platform policies, or bureaucratic "
            "processes to silence legitimate voices while appearing to act in "
            "good faith. Documented in union-busting playbooks, in coordinated "
            "mass-reporting campaigns targeting activists, and in historical "
            "disruption of civil rights meeting procedures."
        ),
        historical_sources=[
            "Donner (1980), pp. 232-241: 'Legal Harassment'",
            "Documented patterns: coordinated mass-reports against LGBTQ+ creators "
            "(2018–2022, multiple platform transparency reports)",
            "Academic: Citron (2014), 'Hate Crimes in Cyberspace', pp. 26-34",
            "Labor relations: documented employer 'salting' and procedural delay tactics",
        ],
        behavioral_indicators=[
            "Coordinated reporting of the same account or content by multiple users "
            "in a short window",
            "Rule-citation behavior that appears specifically against particular members "
            "or viewpoints",
            "Appeals to moderation that use identical framing across different reporters",
            "Pattern of rule invocation that disappears when the targeted behavior stops",
        ],
        alternate_explanations=[
            "Organic community members independently noticing the same rule violation",
            "A legitimate moderation concern that multiple people share",
            "Community members who were told to report something via legitimate channels",
        ],
        coordination_score_weight=0.7,
        requires_multiple_accounts=True,
        notes=(
            "Coordinated mass-reporting is one of the clearest structural signals "
            "because there is a narrow set of innocent explanations for synchronized "
            "reports against the same target."
        ),
    ),

    # ── Category: Coordination Infrastructure ────────────────────────────────

    HistoricalTactic(
        tactic_id="COORD-001",
        name="Off-Platform Coordination Bleed-Through",
        category="coordination_infrastructure",
        description=(
            "When a campaign is organized off-platform (separate Discord server, "
            "Telegram channel, chan board), the coordination leaves structural "
            "traces: synchronized timing, identical terminology appearing before "
            "organic spread would explain it, and arrival patterns inconsistent "
            "with individual discovery."
        ),
        historical_sources=[
            "Stanford Internet Observatory, 'Cross-Platform Fringe Spillover' (2021)",
            "EU DisinfoLab, 'Anti-EU Disinformation' (2019): documented bleed-through "
            "from coordinated Telegram channels to Twitter",
            "RAND, 'Measuring the Information Environment' (2020)",
        ],
        behavioral_indicators=[
            "Terminology or memes appear simultaneously across accounts with no "
            "traceable origin in the monitored community",
            "Accounts with no prior mutual interaction use identical non-obvious phrasing",
            "Activity spikes that correspond to no observable internal trigger",
            "New accounts appear in clusters around the same time with similar early behavior",
        ],
        alternate_explanations=[
            "Organic community members arriving from a shared external interest (subreddit, podcast)",
            "A viral moment on another platform naturally spreading",
            "Mutual friends inviting each other simultaneously",
            "A public announcement that brought in many new members",
        ],
        coordination_score_weight=0.75,
        requires_multiple_accounts=True,
        notes=(
            "Highest weight in the library. Identical non-obvious terminology "
            "appearing simultaneously across accounts with no shared interaction "
            "history is the strongest structural signal available without access "
            "to server logs."
        ),
    ),

    HistoricalTactic(
        tactic_id="COORD-002",
        name="Controlled Velocity Amplification",
        category="coordination_infrastructure",
        description=(
            "Coordinated engagement (likes, shares, boosts, upvotes) timed to "
            "artificially elevate specific content in algorithmic feeds, creating "
            "the appearance of organic popularity. Documented in Russian IRA "
            "operations (Senate Intelligence Committee, 2019) and commercial "
            "influence networks."
        ),
        historical_sources=[
            "Senate Intelligence Committee, 'Report on Russian Active Measures' "
            "Vol. 2 (2019), pp. 47-62",
            "Stanford Internet Observatory, 'Coordinated Link Sharing on Facebook' (2020)",
            "Oxford Internet Institute, 'Industrialized Disinformation' (2021)",
        ],
        behavioral_indicators=[
            "Reaction/engagement pattern on specific content significantly faster "
            "than community baseline",
            "Engagement from accounts with low general activity concentrated on "
            "specific content items",
            "Reaction timing clusters within seconds rather than following natural "
            "logarithmic decay curve",
        ],
        alternate_explanations=[
            "Content that is genuinely popular and shared externally",
            "A notification that caused simultaneous viewing",
            "Server boost or pin that increased visibility",
        ],
        coordination_score_weight=0.5,
        requires_multiple_accounts=True,
    ),
]


# ─── Lookup helpers ──────────────────────────────────────────────────────────

def get_tactic(tactic_id: str) -> HistoricalTactic | None:
    return next((t for t in TACTICS_LIBRARY if t.tactic_id == tactic_id), None)


def get_by_category(category: str) -> list[HistoricalTactic]:
    return [t for t in TACTICS_LIBRARY if t.category == category]


def match_signals_to_tactics(signal_types: list[str]) -> list[HistoricalTactic]:
    """
    Loose match: given a list of coordination signal type strings from Agent 1,
    return tactics whose indicators overlap. Agent 2 uses this for triage.
    """
    matches = []
    for tactic in TACTICS_LIBRARY:
        for signal in signal_types:
            for indicator in tactic.behavioral_indicators:
                if any(word in indicator.lower() for word in signal.lower().split("_")):
                    if tactic not in matches:
                        matches.append(tactic)
                    break
    return matches


SIGNAL_TYPE_TAXONOMY = {
    "synchronized_timing":      "Posts from multiple accounts within narrow time windows",
    "template_language":        "Identical or near-identical non-attributed phrasing",
    "account_age_activity_gap": "Account age significantly predates or postdates activity pattern",
    "coordinated_reporting":    "Multiple accounts reporting same target in short window",
    "cluster_arrival":          "Multiple accounts joining around same time with similar early behavior",
    "engagement_velocity":      "Reaction/boost patterns faster than community baseline",
    "escalation_pattern":       "Consistent push toward confrontational framing at key moments",
    "cross_account_terminology":"Non-obvious identical terms across accounts with no shared history",
    "defamation_timing":        "Allegations appearing simultaneously at high-visibility moments",
    "negative_pattern":         "Consistent pessimistic framing with no constructive alternatives",
}
