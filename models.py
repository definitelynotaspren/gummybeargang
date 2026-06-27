"""
Shared data models for the multi-agent disruptor watchdog.
All agents read/write TicketEnvelopes; the ticket ID is the only persistent
identifier that flows between agents and into public-facing output.
"""

from __future__ import annotations
import uuid
import json
from enum import Enum
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional


# ─── Confidence Ladder ───────────────────────────────────────────────────────
class ConfidenceTier(str, Enum):
    SPECULATIVE   = "SPECULATIVE"    # single signal, alternate explanations likely
    CORROBORATED  = "CORROBORATED"   # 2+ independent signals
    CONFIRMED     = "CONFIRMED"      # convergent signals, low alternate explanation rate

    def upgrade(self) -> "ConfidenceTier":
        order = [self.SPECULATIVE, self.CORROBORATED, self.CONFIRMED]
        idx = order.index(self)
        return order[min(idx + 1, len(order) - 1)]


# ─── Agent Roles ─────────────────────────────────────────────────────────────
class AgentRole(str, Enum):
    COORDINATION_DETECTOR = "coordination_detector"   # Agent 1
    TACTICS_REFERENCE     = "tactics_reference"       # Agent 2
    EVIDENCE_LOGGER       = "evidence_logger"         # Agent 3
    REPORT_WRITER         = "report_writer"           # Agent 4


MAX_AGENT_ROUNDS = 4  # hard stop per ticket


# ─── Coordination Signals (Agent 1 output) ───────────────────────────────────
@dataclass
class CoordinationSignal:
    signal_type: str           # e.g. "synchronized_timing", "template_language"
    description: str
    account_ids_involved: list[str]   # internal IDs, never go to public channel
    observed_at: str           # ISO timestamp
    confidence: float          # 0.0–1.0


# ─── Tactic Match (Agent 2 output) ───────────────────────────────────────────
@dataclass
class TacticMatch:
    tactic_name: str
    historical_source: str     # e.g. "COINTELPRO / Church Committee Vol. 6, p.187"
    description: str
    alternate_explanations: list[str]   # REQUIRED — must be non-empty
    match_confidence: float    # 0.0–1.0


# ─── Evidence Item (Agent 3 output) ──────────────────────────────────────────
@dataclass
class EvidenceItem:
    item_id: str
    timestamp: str
    message_id: str            # Discord message snowflake — no content stored
    channel_id: str
    behavior_observed: str     # human-readable description, no username
    supporting_signals: list[str]
    confidence_contribution: float


# ─── The Ticket Envelope (flows through all agents) ──────────────────────────
@dataclass
class TicketEnvelope:
    ticket_id: str = field(default_factory=lambda: f"TKT-{uuid.uuid4().hex[:8].upper()}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Pipeline state
    current_round: int = 0
    completed_agents: list[str] = field(default_factory=list)
    status: str = "open"       # open | closed | dismissed

    # Agent 1 — Coordination Detector
    coordination_score: float = 0.0
    coordination_signals: list[CoordinationSignal] = field(default_factory=list)
    account_cluster_size: int = 0

    # Agent 2 — Tactics Reference
    tactic_matches: list[TacticMatch] = field(default_factory=list)
    all_alternate_explanations: list[str] = field(default_factory=list)
    tactics_false_positive_estimate: float = 0.0

    # Agent 3 — Evidence Logger
    evidence_items: list[EvidenceItem] = field(default_factory=list)
    confidence_tier: ConfidenceTier = ConfidenceTier.SPECULATIVE
    timeline_summary: str = ""

    # Agent 4 — Report Writer
    public_summary: str = ""       # anonymized, safe for public channel
    public_notice_fields: dict = field(default_factory=dict)  # slot-based structured notice
    mod_report: str = ""           # full detail, mod channel only
    mod_action_checklist: list[str] = field(default_factory=list)
    report_ready: bool = False

    def touch(self):
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.current_round += 1

    def to_dict(self) -> dict:
        d = asdict(self)
        d["confidence_tier"] = self.confidence_tier.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TicketEnvelope":
        d = dict(d)
        d["confidence_tier"] = ConfidenceTier(d.get("confidence_tier", "SPECULATIVE"))
        d["coordination_signals"] = [CoordinationSignal(**s) for s in d.get("coordination_signals", [])]
        d["tactic_matches"] = [TacticMatch(**t) for t in d.get("tactic_matches", [])]
        d["evidence_items"] = [EvidenceItem(**e) for e in d.get("evidence_items", [])]
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_json(cls, s: str) -> "TicketEnvelope":
        return cls.from_dict(json.loads(s))
