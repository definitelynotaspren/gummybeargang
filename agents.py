"""
Multi-Agent Pipeline — four specialized agents that hand off via ticket envelopes.
Each agent reads the current ticket, does its job, and writes back.
The orchestrator enforces the MAX_AGENT_ROUNDS hard stop.
"""

from __future__ import annotations
import json
import math
import asyncio
import logging
import hashlib
from datetime import datetime, timezone
from collections import defaultdict

import aiohttp

from models import (
    TicketEnvelope, ConfidenceTier, AgentRole,
    CoordinationSignal, TacticMatch, EvidenceItem,
    MAX_AGENT_ROUNDS,
)
from tactics_library import (
    TACTICS_LIBRARY, SIGNAL_TYPE_TAXONOMY,
    match_signals_to_tactics, get_tactic,
)

log = logging.getLogger("watchdog.agents")

OLLAMA_URL   = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:1b"

# Timing window for "synchronized" posting (seconds)
SYNC_WINDOW_SECONDS = 45


# ─── Ollama helper ────────────────────────────────────────────────────────────
async def ollama_json(prompt: str, system: str = "", max_tokens: int = 400) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": (f"{system}\n\n{prompt}" if system else prompt),
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": max_tokens},
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{OLLAMA_URL}/api/generate", json=payload,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as r:
                data = await r.json()
                raw = data.get("response", "{}").strip()
                raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                return json.loads(raw)
    except Exception as e:
        log.warning(f"Ollama call failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — Coordination Detector
# Focus: metadata and structural signals only; never reads message content
# ═══════════════════════════════════════════════════════════════════════════════
class CoordinationDetectorAgent:
    """
    Analyzes message metadata (timestamps, account join dates, posting
    frequency) for structural anomalies consistent with coordination.
    Does NOT read message content.
    """
    role = AgentRole.COORDINATION_DETECTOR

    def __init__(self, message_store: "MessageStore"):
        self.store = message_store

    async def run(self, ticket: TicketEnvelope) -> TicketEnvelope:
        log.info(f"[Agent1] Running coordination detection for {ticket.ticket_id}")
        signals: list[CoordinationSignal] = []
        score = 0.0

        recent = self.store.get_recent(minutes=60)
        if not recent:
            ticket.coordination_score = 0.0
            ticket.completed_agents.append(self.role.value)
            ticket.touch()
            return ticket

        # ── Signal 1: Synchronized timing ─────────────────────────────────
        timing_clusters = self._find_timing_clusters(recent)
        for cluster in timing_clusters:
            if len(cluster["account_ids"]) >= 2:
                sig = CoordinationSignal(
                    signal_type="synchronized_timing",
                    description=(
                        f"{len(cluster['account_ids'])} accounts posted within "
                        f"{cluster['window_seconds']}s of each other "
                        f"({cluster['post_count']} posts total)"
                    ),
                    account_ids_involved=cluster["account_ids"],
                    observed_at=cluster["earliest"],
                    confidence=min(0.9, 0.3 + 0.15 * len(cluster["account_ids"])),
                )
                signals.append(sig)
                score += 0.35 * sig.confidence

        # ── Signal 2: Account age / activity gap ──────────────────────────
        age_gaps = self._find_age_activity_gaps(recent)
        for gap in age_gaps:
            sig = CoordinationSignal(
                signal_type="account_age_activity_gap",
                description=(
                    f"Account joined {gap['join_days_ago']}d ago but "
                    f"shows {gap['recent_posts']} posts in last hour "
                    f"(baseline: {gap['baseline_posts_per_hour']:.1f}/hr)"
                ),
                account_ids_involved=[gap["account_id"]],
                observed_at=datetime.now(timezone.utc).isoformat(),
                confidence=gap["confidence"],
            )
            signals.append(sig)
            score += 0.15 * sig.confidence

        # ── Signal 3: Cluster arrival (new accounts joining together) ──────
        cluster_arrivals = self._find_cluster_arrivals(recent)
        if cluster_arrivals:
            sig = CoordinationSignal(
                signal_type="cluster_arrival",
                description=(
                    f"{cluster_arrivals['count']} accounts joined within "
                    f"{cluster_arrivals['window_hours']}hr of each other"
                ),
                account_ids_involved=cluster_arrivals["account_ids"],
                observed_at=cluster_arrivals["earliest_join"],
                confidence=min(0.85, 0.2 * cluster_arrivals["count"]),
            )
            signals.append(sig)
            score += 0.25 * sig.confidence

        # ── Signal 4: Engagement velocity anomaly ─────────────────────────
        velocity = self._check_engagement_velocity(recent)
        if velocity:
            sig = CoordinationSignal(
                signal_type="engagement_velocity",
                description=(
                    f"Reaction burst: {velocity['reaction_count']} reactions "
                    f"in {velocity['window_seconds']}s "
                    f"(community baseline: {velocity['baseline_per_minute']:.1f}/min)"
                ),
                account_ids_involved=velocity["reactor_ids"],
                observed_at=velocity["observed_at"],
                confidence=velocity["confidence"],
            )
            signals.append(sig)
            score += 0.25 * sig.confidence

        ticket.coordination_signals = signals
        ticket.coordination_score = min(1.0, score)
        ticket.account_cluster_size = max(
            (len(s.account_ids_involved) for s in signals), default=0
        )
        ticket.completed_agents.append(self.role.value)
        ticket.touch()

        log.info(
            f"[Agent1] Done: score={ticket.coordination_score:.2f} "
            f"signals={len(signals)}"
        )
        return ticket

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _find_timing_clusters(self, messages: list[dict]) -> list[dict]:
        if len(messages) < 2:
            return []
        sorted_msgs = sorted(messages, key=lambda m: m["timestamp"])
        clusters = []
        i = 0
        while i < len(sorted_msgs):
            window = [sorted_msgs[i]]
            j = i + 1
            while j < len(sorted_msgs):
                gap = (
                    sorted_msgs[j]["timestamp"] - sorted_msgs[i]["timestamp"]
                ).total_seconds()
                if gap <= SYNC_WINDOW_SECONDS:
                    window.append(sorted_msgs[j])
                    j += 1
                else:
                    break
            if len(window) >= 3:
                account_ids = list({m["account_hash"] for m in window})
                if len(account_ids) >= 2:
                    clusters.append({
                        "account_ids": account_ids,
                        "post_count": len(window),
                        "window_seconds": (
                            window[-1]["timestamp"] - window[0]["timestamp"]
                        ).total_seconds(),
                        "earliest": window[0]["timestamp"].isoformat(),
                    })
            i = j if j > i else i + 1
        return clusters

    def _find_age_activity_gaps(self, messages: list[dict]) -> list[dict]:
        gaps = []
        account_activity = defaultdict(list)
        for m in messages:
            account_activity[m["account_hash"]].append(m)
        for acct_hash, msgs in account_activity.items():
            meta = self.store.get_account_meta(acct_hash)
            if not meta:
                continue
            recent_count = len(msgs)
            baseline = meta.get("baseline_posts_per_hour", 0.5)
            join_days = meta.get("join_days_ago", 999)
            # Flag: very new account posting at high volume
            if join_days < 14 and recent_count > max(5, baseline * 3):
                confidence = min(0.8, 0.3 + 0.05 * recent_count)
                gaps.append({
                    "account_id": acct_hash,
                    "join_days_ago": join_days,
                    "recent_posts": recent_count,
                    "baseline_posts_per_hour": baseline,
                    "confidence": confidence,
                })
        return gaps

    def _find_cluster_arrivals(self, messages: list[dict]) -> dict | None:
        # Look for accounts that joined within 48hr of each other
        account_joins = {}
        for m in messages:
            meta = self.store.get_account_meta(m["account_hash"])
            if meta and "join_timestamp" in meta:
                account_joins[m["account_hash"]] = meta["join_timestamp"]
        if len(account_joins) < 3:
            return None
        joins = sorted(account_joins.items(), key=lambda x: x[1])
        for i in range(len(joins) - 2):
            window_accts = [joins[i]]
            for j in range(i + 1, len(joins)):
                hrs = (joins[j][1] - joins[i][1]).total_seconds() / 3600
                if hrs <= 48:
                    window_accts.append(joins[j])
                else:
                    break
            if len(window_accts) >= 3:
                return {
                    "count": len(window_accts),
                    "window_hours": (
                        window_accts[-1][1] - window_accts[0][1]
                    ).total_seconds() / 3600,
                    "account_ids": [a[0] for a in window_accts],
                    "earliest_join": window_accts[0][1].isoformat(),
                }
        return None

    def _check_engagement_velocity(self, messages: list[dict]) -> dict | None:
        reaction_events = [m for m in messages if m.get("is_reaction")]
        if len(reaction_events) < 5:
            return None
        sorted_r = sorted(reaction_events, key=lambda m: m["timestamp"])
        window_secs = (sorted_r[-1]["timestamp"] - sorted_r[0]["timestamp"]).total_seconds()
        if window_secs < 1:
            return None
        baseline = self.store.get_baseline_reactions_per_minute()
        actual_per_min = len(reaction_events) / (window_secs / 60)
        if actual_per_min > baseline * 4:
            return {
                "reaction_count": len(reaction_events),
                "window_seconds": window_secs,
                "baseline_per_minute": baseline,
                "reactor_ids": list({m["account_hash"] for m in reaction_events}),
                "observed_at": sorted_r[0]["timestamp"].isoformat(),
                "confidence": min(0.9, actual_per_min / (baseline * 4) * 0.5),
            }
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — Tactics Reference
# Focus: match signals to historical playbook; MUST populate alternate_explanations
# ═══════════════════════════════════════════════════════════════════════════════
class TacticsReferenceAgent:
    """
    Matches Agent 1's coordination signals against the historical tactics library.
    Critically: always populates alternate_explanations before advancing the ticket.
    """
    role = AgentRole.TACTICS_REFERENCE

    SYSTEM = (
        "You are a civil rights history researcher specializing in documented "
        "disruption tactics. Given coordination signals, you identify which "
        "historical tactics they most resemble AND provide plausible innocent "
        "explanations. You are cautious and err toward innocent explanations. "
        "Respond only with JSON."
    )

    async def run(self, ticket: TicketEnvelope) -> TicketEnvelope:
        log.info(f"[Agent2] Running tactics reference for {ticket.ticket_id}")

        signal_types = [s.signal_type for s in ticket.coordination_signals]
        candidate_tactics = match_signals_to_tactics(signal_types)

        tactic_matches: list[TacticMatch] = []
        all_alternates: list[str] = []
        total_fp_score = 0.0

        for tactic in candidate_tactics:
            # Ask Ollama to assess match quality + generate additional alternates
            prompt = f"""Coordination signals observed: {json.dumps(signal_types)}

Historical tactic to assess:
- Name: {tactic.name}
- Category: {tactic.category}
- Description: {tactic.description[:300]}
- Known indicators: {json.dumps(tactic.behavioral_indicators[:4])}

Existing alternate explanations: {json.dumps(tactic.alternate_explanations)}

Respond with JSON:
{{
  "match_confidence": 0.0-1.0,
  "match_reasoning": "one sentence",
  "additional_alternate_explanations": ["at least two more innocent explanations"],
  "false_positive_likelihood": 0.0-1.0
}}"""

            result = await ollama_json(prompt, self.SYSTEM, max_tokens=300)

            match_conf = float(result.get("match_confidence", 0.3))
            fp_likelihood = float(result.get("false_positive_likelihood", 0.5))
            extra_alternates = result.get("additional_alternate_explanations", [])

            all_alternates.extend(tactic.alternate_explanations)
            all_alternates.extend(extra_alternates)
            total_fp_score += fp_likelihood

            if match_conf >= 0.35:   # threshold: only include meaningful matches
                tactic_matches.append(TacticMatch(
                    tactic_name=tactic.name,
                    historical_source=tactic.historical_sources[0] if tactic.historical_sources else "See tactics_library.py",
                    description=tactic.description[:400],
                    alternate_explanations=tactic.alternate_explanations + extra_alternates,
                    match_confidence=match_conf,
                ))

        # Deduplicate alternates
        all_alternates = list(dict.fromkeys(all_alternates))

        # Ensure alternate_explanations is NEVER empty — gate on this
        if not all_alternates:
            all_alternates = [
                "Organic community members coincidentally active at the same time",
                "External event causing simultaneous engagement",
                "Technical artifact (bot, notification burst, pin)",
                "Genuine new member influx from shared interest community",
            ]

        avg_fp = total_fp_score / len(candidate_tactics) if candidate_tactics else 0.8

        ticket.tactic_matches = tactic_matches
        ticket.all_alternate_explanations = all_alternates
        ticket.tactics_false_positive_estimate = avg_fp
        ticket.completed_agents.append(self.role.value)
        ticket.touch()

        log.info(
            f"[Agent2] Done: {len(tactic_matches)} tactic matches, "
            f"FP estimate={avg_fp:.2f}, alternates={len(all_alternates)}"
        )
        return ticket


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — Evidence Logger
# Focus: build a timestamped, sourced case file; assign confidence tier
# ═══════════════════════════════════════════════════════════════════════════════
class EvidenceLoggerAgent:
    """
    Assembles a structured, chronological evidence chain.
    Assigns confidence tier (SPECULATIVE / CORROBORATED / CONFIRMED).
    Never stores raw message content — only message IDs and behavioral descriptions.
    """
    role = AgentRole.EVIDENCE_LOGGER

    async def run(self, ticket: TicketEnvelope) -> TicketEnvelope:
        log.info(f"[Agent3] Building evidence log for {ticket.ticket_id}")

        items: list[EvidenceItem] = []
        item_counter = 0

        for signal in ticket.coordination_signals:
            item_counter += 1
            items.append(EvidenceItem(
                item_id=f"{ticket.ticket_id}-E{item_counter:03d}",
                timestamp=signal.observed_at,
                message_id="[see coordination_signals metadata]",
                channel_id="[logged in audit store]",
                behavior_observed=(
                    f"Coordination signal: {SIGNAL_TYPE_TAXONOMY.get(signal.signal_type, signal.signal_type)}. "
                    f"{signal.description}"
                ),
                supporting_signals=[signal.signal_type],
                confidence_contribution=signal.confidence,
            ))

        for match in ticket.tactic_matches:
            item_counter += 1
            items.append(EvidenceItem(
                item_id=f"{ticket.ticket_id}-E{item_counter:03d}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                message_id="[tactics reference — no message]",
                channel_id="[historical match]",
                behavior_observed=(
                    f"Historical pattern match: '{match.tactic_name}' "
                    f"(confidence {match.match_confidence:.0%}). "
                    f"Source: {match.historical_source}"
                ),
                supporting_signals=["tactics_library_match"],
                confidence_contribution=match.match_confidence * 0.5,
            ))

        # ── Assign confidence tier ─────────────────────────────────────────
        signal_types = {s.signal_type for s in ticket.coordination_signals}
        n_signals = len(signal_types)
        n_matches = len(ticket.tactic_matches)
        avg_signal_conf = (
            sum(s.confidence for s in ticket.coordination_signals)
            / max(len(ticket.coordination_signals), 1)
        )

        if n_signals >= 3 and n_matches >= 2 and avg_signal_conf >= 0.65:
            tier = ConfidenceTier.CONFIRMED
        elif n_signals >= 2 or (n_signals >= 1 and n_matches >= 1):
            tier = ConfidenceTier.CORROBORATED
        else:
            tier = ConfidenceTier.SPECULATIVE

        # ── Build timeline summary ─────────────────────────────────────────
        sorted_items = sorted(items, key=lambda i: i.timestamp)
        timeline_lines = []
        for it in sorted_items:
            ts = it.timestamp[:19].replace("T", " ")
            timeline_lines.append(f"  {ts}  [{it.item_id}]  {it.behavior_observed[:120]}")
        timeline = "\n".join(timeline_lines)

        ticket.evidence_items = items
        ticket.confidence_tier = tier
        ticket.timeline_summary = timeline
        ticket.completed_agents.append(self.role.value)
        ticket.touch()

        log.info(
            f"[Agent3] Done: {len(items)} evidence items, "
            f"tier={tier.value}"
        )
        return ticket


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 4 — Report Writer
# Focus: produce two outputs — anonymized public summary, detailed mod report
# ═══════════════════════════════════════════════════════════════════════════════
class ReportWriterAgent:
    """
    Produces two reports:
      - public_summary: anonymized, safe for public transparency channel
      - mod_report: full evidence chain, account identifiers only if CONFIRMED
    Closes the ticket.
    """
    role = AgentRole.REPORT_WRITER

    SYSTEM = (
        "You write moderation transparency notices for a civil society Discord community. "
        "Your audience is two groups reading the same post: community members who may be "
        "confused or concerned about seeing a moderation notice, and moderators using the "
        "public channel as a transparency record. "
        "Tone: calm, factual, non-alarming. Never speculative. Never accusatory. "
        "You never name, identify, or hint at specific users. "
        "You always acknowledge that innocent explanations exist and are being considered. "
        "You always confirm that no automated action has been taken. "
        "Respond only with JSON. No preamble, no markdown fences."
    )

    async def run(self, ticket: TicketEnvelope) -> TicketEnvelope:
        log.info(f"[Agent4] Writing reports for {ticket.ticket_id}")

        tactic_names = [m.tactic_name for m in ticket.tactic_matches]
        signal_types = [s.signal_type for s in ticket.coordination_signals]

        # ── Public summary (slot-based structured notice) ──────────────────
        pub_prompt = f"""You are writing a public moderation transparency notice.
Fill in each field of the JSON below. Rules for each field are in [brackets].
Observed signals: {signal_types}
Confidence tier: {ticket.confidence_tier.value}
Coordination score: {ticket.coordination_score:.0%}
False positive estimate: {ticket.tactics_false_positive_estimate:.0%}
Alternate explanations available: {ticket.all_alternate_explanations[:3]}
Historical pattern matches: {[m.tactic_name for m in ticket.tactic_matches]}
Ticket ID: {ticket.ticket_id}
Respond with this exact JSON structure, all fields required:
{{
  "what_we_observed": "[1-2 sentences. Describe the structural/timing pattern in plain language. No usernames, no IDs, no political framing. Example: 'Several accounts posted in close succession targeting the same thread.' Focus on the pattern, not any judgment about intent.]",
  "what_this_means": "[1 sentence. Explain what the confidence tier means at a human level. SPECULATIVE = one signal, many innocent explanations. CORROBORATED = multiple independent signals. CONFIRMED = convergent signals across multiple detection methods. Do not editorialize.]",
  "alternate_explanations": "[1 sentence naming 2-3 of the innocent explanations that were considered. Frame as genuinely plausible, not as a disclaimer. Example: 'Explanations considered include a shared announcement driving simultaneous engagement, a notification burst, or members from the same external community joining around the same time.']",
  "what_happens_next": "[1 sentence. State that human moderators are reviewing the evidence and that no automated action has been or will be taken by this system.]",
  "false_positive_note": "[1 short sentence. State the false positive estimate as a percentage and that it is factored into moderator review. Example: 'The system estimates a {ticket.tactics_false_positive_estimate:.0%} false positive rate for this pattern.']",
  "contest_instructions": "[1 sentence. Tell users they can reference ticket ID {ticket.ticket_id} when contacting moderators if they believe they were flagged in error.]"
}}"""

        pub_result = await ollama_json(pub_prompt, self.SYSTEM, max_tokens=400)

        required_fields = [
            "what_we_observed", "what_this_means", "alternate_explanations",
            "what_happens_next", "false_positive_note", "contest_instructions",
        ]
        missing = [f for f in required_fields if not pub_result.get(f)]
        if missing:
            log.warning(f"[Agent4] Public notice missing fields: {missing} — using fallbacks")

        ticket.public_notice_fields = {
            "what_we_observed":       pub_result.get("what_we_observed",       self._fallback_observed(ticket)),
            "what_this_means":        pub_result.get("what_this_means",        self._fallback_tier(ticket)),
            "alternate_explanations": pub_result.get("alternate_explanations", self._fallback_alternates(ticket)),
            "what_happens_next":      pub_result.get("what_happens_next",      "Human moderators are reviewing this. No automated action has been taken."),
            "false_positive_note":    pub_result.get("false_positive_note",    f"Estimated false positive rate: {ticket.tactics_false_positive_estimate:.0%}."),
            "contest_instructions":   pub_result.get("contest_instructions",   f"Reference ticket `{ticket.ticket_id}` when contacting moderators if you believe you were flagged in error."),
        }
        public_summary = " ".join(ticket.public_notice_fields.values())

        # ── Mod report (full detail; account IDs only if CONFIRMED) ───────
        include_ids = ticket.confidence_tier == ConfidenceTier.CONFIRMED
        account_ids_section = ""
        if include_ids:
            all_ids = list({
                acct_id
                for sig in ticket.coordination_signals
                for acct_id in sig.account_ids_involved
            })
            account_ids_section = (
                f"ACCOUNT CLUSTER (CONFIRMED tier — hashed IDs for mod lookup):\n"
                + "\n".join(f"  • {aid}" for aid in all_ids)
                + "\n\n"
            )
        else:
            account_ids_section = (
                f"ACCOUNT IDENTIFIERS: Withheld — confidence tier is "
                f"{ticket.confidence_tier.value}, not CONFIRMED. "
                f"Moderators should use evidence item IDs to pull from audit log.\n\n"
            )

        tactic_section = ""
        for m in ticket.tactic_matches:
            tactic_section += (
                f"  • {m.tactic_name} ({m.match_confidence:.0%} match)\n"
                f"    Source: {m.historical_source}\n"
                f"    Alternate explanations: {'; '.join(m.alternate_explanations[:2])}\n\n"
            )

        checklist = [
            "[ ] Review evidence items in audit log against ticket ID",
            "[ ] Check account metadata for items flagged CORROBORATED or above",
            "[ ] Consider alternate explanations listed before any action",
            "[ ] Dismiss ticket if false positive",
            "[ ] Escalate to senior moderator if CONFIRMED tier",
            "[ ] Request context from user(s) if appropriate",
            "[ ] No automated action has been or will be taken by this system",
        ]

        mod_report = f"""
╔══════════════════════════════════════════════════════════════════════╗
  MODERATION CASE FILE
  Ticket: {ticket.ticket_id}
  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
  Confidence: {ticket.confidence_tier.value}
  Coordination Score: {ticket.coordination_score:.0%}
  False Positive Estimate: {ticket.tactics_false_positive_estimate:.0%}
╚══════════════════════════════════════════════════════════════════════╝

{account_ids_section}COORDINATION SIGNALS DETECTED:
{chr(10).join(f"  • [{s.signal_type}] {s.description} (confidence: {s.confidence:.0%})" for s in ticket.coordination_signals)}

HISTORICAL PATTERN MATCHES:
{tactic_section if tactic_section else "  None above threshold."}

EVIDENCE TIMELINE:
{ticket.timeline_summary}

ALTERNATE EXPLANATIONS (must be considered before any action):
{chr(10).join(f"  • {a}" for a in ticket.all_alternate_explanations[:6])}

MODERATOR ACTION REQUIRED:
{chr(10).join(checklist)}

───────────────────────────────────────────────────────────────────────
This report was generated automatically. No action has been taken.
All decisions are made by human moderators only.
To contest this report, reference ticket {ticket.ticket_id} to moderators.
───────────────────────────────────────────────────────────────────────
""".strip()

        ticket.public_summary = public_summary
        ticket.mod_report = mod_report
        ticket.mod_action_checklist = checklist
        ticket.report_ready = True
        ticket.status = "closed"
        ticket.completed_agents.append(self.role.value)
        ticket.touch()

        log.info(f"[Agent4] Reports ready for {ticket.ticket_id}")
        return ticket

    def _fallback_observed(self, ticket: TicketEnvelope) -> str:
        types = ", ".join(s.signal_type.replace("_", " ") for s in ticket.coordination_signals)
        return f"The monitoring system detected structural coordination patterns: {types}."

    def _fallback_tier(self, ticket: TicketEnvelope) -> str:
        descriptions = {
            "SPECULATIVE":  "A single signal was detected; many innocent explanations exist and are being considered.",
            "CORROBORATED": "Multiple independent signals were detected pointing in the same direction.",
            "CONFIRMED":    "Convergent signals were detected across multiple detection methods with low alternate explanation rate.",
        }
        return descriptions.get(ticket.confidence_tier.value, "Coordination patterns were detected.")

    def _fallback_alternates(self, ticket: TicketEnvelope) -> str:
        alts = ticket.all_alternate_explanations[:2]
        if not alts:
            return "Innocent explanations including organic community activity are being considered."
        return f"Explanations considered include: {'; '.join(alts)}."


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# Wires agents together, enforces round limit, routes output
# ═══════════════════════════════════════════════════════════════════════════════
class AgentOrchestrator:
    """
    Runs the four agents in sequence on a ticket.
    Hard stops at MAX_AGENT_ROUNDS.
    Skips if coordination_score is below minimum threshold.
    """
    MIN_SCORE_TO_ADVANCE = 0.25   # below this, Agent 1 closes the ticket immediately

    def __init__(self, message_store: "MessageStore"):
        self.agent1 = CoordinationDetectorAgent(message_store)
        self.agent2 = TacticsReferenceAgent()
        self.agent3 = EvidenceLoggerAgent()
        self.agent4 = ReportWriterAgent()

    async def process(self, trigger_context: dict) -> TicketEnvelope | None:
        ticket = TicketEnvelope()
        log.info(f"[Orchestrator] Opening ticket {ticket.ticket_id}")

        # Round 1 — Coordination Detector
        ticket = await self.agent1.run(ticket)
        if ticket.current_round >= MAX_AGENT_ROUNDS:
            return ticket

        if ticket.coordination_score < self.MIN_SCORE_TO_ADVANCE:
            log.info(
                f"[Orchestrator] Score {ticket.coordination_score:.2f} below threshold, "
                f"closing {ticket.ticket_id}"
            )
            ticket.status = "dismissed"
            return None

        # Round 2 — Tactics Reference
        ticket = await self.agent2.run(ticket)
        if ticket.current_round >= MAX_AGENT_ROUNDS:
            return ticket

        # Round 3 — Evidence Logger
        ticket = await self.agent3.run(ticket)
        if ticket.current_round >= MAX_AGENT_ROUNDS:
            return ticket

        # Round 4 — Report Writer (final round)
        ticket = await self.agent4.run(ticket)
        return ticket


# ─── Stub: MessageStore (implement per-deployment) ───────────────────────────
class MessageStore:
    """
    Stub for the message metadata store.
    In production: back with SQLite or DuckDB.
    IMPORTANT: store account_hash (SHA-256 of user_id), NOT raw user IDs,
    in the activity log. Raw IDs are only pulled at CONFIRMED tier by mods.
    """
    def __init__(self):
        self._messages: list[dict] = []
        self._account_meta: dict[str, dict] = {}
        self._baseline_rpm = 2.0

    def ingest(self, discord_message):
        """Call this for every message. Stores metadata only."""
        account_hash = hashlib.sha256(
            str(discord_message.author.id).encode()
        ).hexdigest()[:16]

        self._messages.append({
            "account_hash": account_hash,
            "raw_user_id": discord_message.author.id,  # only for CONFIRMED lookups
            "timestamp": discord_message.created_at.replace(tzinfo=timezone.utc),
            "channel_id": str(discord_message.channel.id),
            "message_id": str(discord_message.id),
            "is_reaction": False,
        })

        # Update account meta
        if account_hash not in self._account_meta:
            join_dt = getattr(discord_message.author, "joined_at", None)
            join_days = None
            if join_dt:
                join_days = (datetime.now(timezone.utc) - join_dt.replace(tzinfo=timezone.utc)).days
            self._account_meta[account_hash] = {
                "join_days_ago": join_days or 999,
                "join_timestamp": join_dt,
                "baseline_posts_per_hour": 0.5,
            }

    def ingest_reaction(self, payload, reactor_id: int):
        account_hash = hashlib.sha256(str(reactor_id).encode()).hexdigest()[:16]
        self._messages.append({
            "account_hash": account_hash,
            "raw_user_id": reactor_id,
            "timestamp": datetime.now(timezone.utc),
            "channel_id": str(payload.channel_id),
            "message_id": str(payload.message_id),
            "is_reaction": True,
        })

    def get_recent(self, minutes: int = 60) -> list[dict]:
        cutoff = datetime.now(timezone.utc).timestamp() - minutes * 60
        return [
            m for m in self._messages
            if m["timestamp"].timestamp() >= cutoff
        ]

    def get_account_meta(self, account_hash: str) -> dict | None:
        return self._account_meta.get(account_hash)

    def get_raw_user_id(self, account_hash: str) -> int | None:
        """Only called by CONFIRMED-tier mod reports."""
        for m in self._messages:
            if m["account_hash"] == account_hash:
                return m["raw_user_id"]
        return None

    def get_baseline_reactions_per_minute(self) -> float:
        return self._baseline_rpm
