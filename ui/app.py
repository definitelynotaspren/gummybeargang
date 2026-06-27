"""
GummyBearGang Agent Network Management UI
Flask backend — serves the SPA and provides REST endpoints for agent specialty management.
"""

from __future__ import annotations
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, jsonify, request, render_template, abort

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

CONFIG_FILE = Path(__file__).parent / "agent_config.json"

app = Flask(__name__)


# ── default config ────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "agents": [
        {
            "id": "coordination_detector",
            "name": "Coordination Detector",
            "role": "Agent 1",
            "description": "Analyzes message metadata for synchronized timing, account clustering, and velocity spikes.",
            "specialties": [],
            "thresholds": {"min_score": 0.25, "sync_window_secs": 45},
            "active": True,
        },
        {
            "id": "tactics_reference",
            "name": "Tactics Reference",
            "role": "Agent 2",
            "description": "Matches detected signals against the historical disruption tactics library.",
            "specialties": [],
            "thresholds": {"min_match_confidence": 0.35},
            "active": True,
        },
        {
            "id": "evidence_logger",
            "name": "Evidence Logger",
            "role": "Agent 3",
            "description": "Builds a timestamped evidence chain and assigns a confidence tier.",
            "specialties": [],
            "thresholds": {"confirmed_signals": 3, "confirmed_tactic_matches": 2},
            "active": True,
        },
        {
            "id": "report_writer",
            "name": "Report Writer",
            "role": "Agent 4",
            "description": "Produces an anonymized public notice and a full moderator case file.",
            "specialties": [],
            "thresholds": {},
            "active": True,
        },
    ],
    "specialties": [],
    "domains": [
        {"id": "crypto_scam", "label": "Crypto / Investment Scam", "color": "#f59e0b"},
        {"id": "romance_fraud", "label": "Romance Fraud", "color": "#ec4899"},
        {"id": "brigading", "label": "Coordinated Brigading", "color": "#ef4444"},
        {"id": "narrative_flood", "label": "Narrative Flooding", "color": "#8b5cf6"},
        {"id": "persona_farm", "label": "Persona / Account Farm", "color": "#06b6d4"},
        {"id": "phishing", "label": "Phishing / Social Engineering", "color": "#f97316"},
        {"id": "wedge_ops", "label": "Wedge Operations", "color": "#84cc16"},
        {"id": "pile_on", "label": "Pile-on / Harassment Campaign", "color": "#dc2626"},
        {"id": "disinfo", "label": "Disinformation Seeding", "color": "#7c3aed"},
        {"id": "impersonation", "label": "Impersonation", "color": "#0891b2"},
    ],
    "last_updated": datetime.now(timezone.utc).isoformat(),
}


# ── helpers ───────────────────────────────────────────────────────────────────
def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


def save_config(cfg: dict):
    cfg["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def find_agent(cfg: dict, agent_id: str) -> dict | None:
    return next((a for a in cfg["agents"] if a["id"] == agent_id), None)


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── agents ────────────────────────────────────────────────────────────────────

@app.route("/api/agents", methods=["GET"])
def get_agents():
    cfg = load_config()
    return jsonify(cfg["agents"])


@app.route("/api/agents/<agent_id>", methods=["GET"])
def get_agent(agent_id: str):
    cfg = load_config()
    agent = find_agent(cfg, agent_id)
    if not agent:
        abort(404, f"Agent {agent_id} not found")
    return jsonify(agent)


@app.route("/api/agents/<agent_id>", methods=["PATCH"])
def update_agent(agent_id: str):
    cfg = load_config()
    agent = find_agent(cfg, agent_id)
    if not agent:
        abort(404)
    body = request.get_json(force=True)
    allowed = {"specialties", "thresholds", "active"}
    for k, v in body.items():
        if k in allowed:
            agent[k] = v
    save_config(cfg)
    return jsonify(agent)


# ── domains ───────────────────────────────────────────────────────────────────

@app.route("/api/domains", methods=["GET"])
def get_domains():
    cfg = load_config()
    return jsonify(cfg["domains"])


@app.route("/api/domains", methods=["POST"])
def create_domain():
    cfg = load_config()
    body = request.get_json(force=True)
    label = (body.get("label") or "").strip()
    color = body.get("color", "#6b7280")
    if not label:
        abort(400, "label is required")
    import re, uuid
    domain_id = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or uuid.uuid4().hex[:8]
    if any(d["id"] == domain_id for d in cfg["domains"]):
        domain_id = f"{domain_id}_{uuid.uuid4().hex[:4]}"
    domain = {"id": domain_id, "label": label, "color": color}
    cfg["domains"].append(domain)
    save_config(cfg)
    return jsonify(domain), 201


@app.route("/api/domains/<domain_id>", methods=["DELETE"])
def delete_domain(domain_id: str):
    cfg = load_config()
    cfg["domains"] = [d for d in cfg["domains"] if d["id"] != domain_id]
    # remove from any agent specialties too
    for agent in cfg["agents"]:
        agent["specialties"] = [s for s in agent.get("specialties", []) if s["domain_id"] != domain_id]
    save_config(cfg)
    return "", 204


# ── specialties ───────────────────────────────────────────────────────────────

@app.route("/api/agents/<agent_id>/specialties", methods=["POST"])
def add_specialty(agent_id: str):
    cfg = load_config()
    agent = find_agent(cfg, agent_id)
    if not agent:
        abort(404)
    body = request.get_json(force=True)
    domain_id = body.get("domain_id")
    if not domain_id:
        abort(400, "domain_id required")
    domain = next((d for d in cfg["domains"] if d["id"] == domain_id), None)
    if not domain:
        abort(404, f"Domain {domain_id} not found")
    if any(s["domain_id"] == domain_id for s in agent.get("specialties", [])):
        abort(409, "Specialty already assigned")
    specialty = {
        "domain_id": domain_id,
        "label": domain["label"],
        "color": domain["color"],
        "notes": body.get("notes", ""),
        "priority": body.get("priority", "medium"),
        "assigned_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.setdefault("specialties", []).append(specialty)
    save_config(cfg)
    return jsonify(specialty), 201


@app.route("/api/agents/<agent_id>/specialties/<domain_id>", methods=["DELETE"])
def remove_specialty(agent_id: str, domain_id: str):
    cfg = load_config()
    agent = find_agent(cfg, agent_id)
    if not agent:
        abort(404)
    agent["specialties"] = [s for s in agent.get("specialties", []) if s["domain_id"] != domain_id]
    save_config(cfg)
    return "", 204


@app.route("/api/agents/<agent_id>/specialties/<domain_id>", methods=["PATCH"])
def update_specialty(agent_id: str, domain_id: str):
    cfg = load_config()
    agent = find_agent(cfg, agent_id)
    if not agent:
        abort(404)
    spec = next((s for s in agent.get("specialties", []) if s["domain_id"] == domain_id), None)
    if not spec:
        abort(404)
    body = request.get_json(force=True)
    for k in ("notes", "priority"):
        if k in body:
            spec[k] = body[k]
    save_config(cfg)
    return jsonify(spec)


# ── tactics summary ───────────────────────────────────────────────────────────

@app.route("/api/tactics", methods=["GET"])
def get_tactics():
    try:
        from tactics_library import TACTICS_LIBRARY
        return jsonify([
            {
                "tactic_id": t.tactic_id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "coordination_score_weight": t.coordination_score_weight,
                "requires_multiple_accounts": t.requires_multiple_accounts,
                "behavioral_indicators": t.behavioral_indicators,
                "alternate_explanations": t.alternate_explanations,
                "historical_sources": t.historical_sources,
            }
            for t in TACTICS_LIBRARY
        ])
    except ImportError:
        return jsonify([])


# ── config snapshot ───────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def get_config():
    cfg = load_config()
    return jsonify({"last_updated": cfg.get("last_updated")})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
