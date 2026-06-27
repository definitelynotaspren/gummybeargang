"""
Discord Bot — Disruptor Pattern Watchdog
Wires message ingestion → orchestrator → agent coordination channel →
public transparency channel + mod-only channel.
"""

import os
import json
import asyncio
import logging
import hashlib
from datetime import datetime, timezone

import discord
from discord.ext import tasks

from agents import AgentOrchestrator, MessageStore
from models import TicketEnvelope, ConfidenceTier, MAX_AGENT_ROUNDS

log = logging.getLogger("watchdog.discord")

# ─── Channel IDs (set via env or config) ─────────────────────────────────────
AGENT_COORD_CHANNEL_ID  = int(os.environ.get("AGENT_COORD_CHANNEL_ID",  "0"))
PUBLIC_CHANNEL_ID       = int(os.environ.get("PUBLIC_CHANNEL_ID",       "0"))
MOD_CHANNEL_ID          = int(os.environ.get("MOD_CHANNEL_ID",          "0"))

# How many messages to buffer before triggering analysis
TRIGGER_MESSAGE_COUNT   = int(os.environ.get("TRIGGER_MESSAGE_COUNT",   "20"))
# How often (seconds) to run a scheduled analysis pass
ANALYSIS_INTERVAL_SECS  = int(os.environ.get("ANALYSIS_INTERVAL_SECS", "300"))


class WatchdogBot(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(intents=intents)

        self.store = MessageStore()
        self.orchestrator = AgentOrchestrator(self.store)
        self._analysis_lock = asyncio.Lock()
        self._message_buffer_count = 0
        self._open_tickets: dict[str, TicketEnvelope] = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_ready(self):
        log.info(f"Watchdog online as {self.user}")
        self._verify_channels()
        self.scheduled_analysis.start()

    def _verify_channels(self):
        for name, cid in [
            ("agent_coord", AGENT_COORD_CHANNEL_ID),
            ("public",      PUBLIC_CHANNEL_ID),
            ("mod",         MOD_CHANNEL_ID),
        ]:
            ch = self.get_channel(cid)
            if ch:
                log.info(f"  Channel [{name}] → #{ch.name}")
            else:
                log.warning(f"  Channel [{name}] ID={cid} NOT FOUND — check config")

    # ── Message ingestion ─────────────────────────────────────────────────────

    async def on_message(self, message: discord.Message):
        # Never watch our own messages or the agent coordination channel
        if message.author.bot:
            return
        if message.channel.id in (AGENT_COORD_CHANNEL_ID, MOD_CHANNEL_ID):
            return

        self.store.ingest(message)
        self._message_buffer_count += 1

        if self._message_buffer_count >= TRIGGER_MESSAGE_COUNT:
            self._message_buffer_count = 0
            asyncio.create_task(self._run_analysis("message_count_trigger"))

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.channel_id in (AGENT_COORD_CHANNEL_ID, MOD_CHANNEL_ID):
            return
        self.store.ingest_reaction(payload, payload.user_id)

    # ── Scheduled analysis ────────────────────────────────────────────────────

    @tasks.loop(seconds=ANALYSIS_INTERVAL_SECS)
    async def scheduled_analysis(self):
        await self._run_analysis("scheduled")

    @scheduled_analysis.before_loop
    async def before_scheduled(self):
        await self.wait_until_ready()

    # ── Core analysis pipeline ────────────────────────────────────────────────

    async def _run_analysis(self, trigger: str):
        if self._analysis_lock.locked():
            log.debug("Analysis already running, skipping")
            return

        async with self._analysis_lock:
            log.info(f"Starting analysis pass (trigger={trigger})")
            try:
                ticket = await self.orchestrator.process({"trigger": trigger})
                if ticket and ticket.report_ready:
                    await self._dispatch_reports(ticket)
                    await self._post_agent_summary(ticket)
            except Exception as e:
                log.error(f"Analysis pipeline error: {e}", exc_info=True)

    # ── Agent coordination channel ────────────────────────────────────────────

    async def _post_agent_summary(self, ticket: TicketEnvelope):
        """
        Posts a structured JSON summary to the agent coordination channel.
        This channel is the paper trail of what each agent decided.
        """
        ch = self.get_channel(AGENT_COORD_CHANNEL_ID)
        if not ch:
            return

        summary = {
            "ticket_id":          ticket.ticket_id,
            "timestamp":          datetime.now(timezone.utc).isoformat(),
            "rounds_completed":   ticket.current_round,
            "agents_run":         ticket.completed_agents,
            "coordination_score": round(ticket.coordination_score, 3),
            "confidence_tier":    ticket.confidence_tier.value,
            "signal_count":       len(ticket.coordination_signals),
            "tactic_match_count": len(ticket.tactic_matches),
            "evidence_item_count":len(ticket.evidence_items),
            "fp_estimate":        round(ticket.tactics_false_positive_estimate, 3),
            "status":             ticket.status,
            "hard_stop_at":       MAX_AGENT_ROUNDS,
        }

        content = (
            f"```json\n{json.dumps(summary, indent=2)}\n```\n"
            f"*Agent pipeline complete — {ticket.current_round}/{MAX_AGENT_ROUNDS} rounds*"
        )
        await ch.send(content[:2000])

    # ── Report dispatch ───────────────────────────────────────────────────────

    async def _dispatch_reports(self, ticket: TicketEnvelope):
        await self._send_public_notice(ticket)
        await self._send_mod_report(ticket)

    async def _send_public_notice(self, ticket: TicketEnvelope):
        ch = self.get_channel(PUBLIC_CHANNEL_ID)
        if not ch:
            log.warning("Public channel not found — skipping public notice")
            return

        tier = ticket.confidence_tier
        color_map = {
            ConfidenceTier.SPECULATIVE:  discord.Color.light_grey(),
            ConfidenceTier.CORROBORATED: discord.Color.orange(),
            ConfidenceTier.CONFIRMED:    discord.Color.red(),
        }
        tier_emoji = {
            ConfidenceTier.SPECULATIVE:  "🟡",
            ConfidenceTier.CORROBORATED: "🟠",
            ConfidenceTier.CONFIRMED:    "🔴",
        }

        embed = discord.Embed(
            title=f"{tier_emoji[tier]} Coordination Review Notice",
            description=ticket.public_summary,
            color=color_map[tier],
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="Ticket ID",
            value=f"`{ticket.ticket_id}` — reference this to moderators if you believe you were flagged in error",
            inline=False,
        )
        embed.add_field(
            name="Confidence",
            value=f"{tier.value} ({ticket.coordination_score:.0%} coordination score)",
            inline=True,
        )
        embed.add_field(
            name="False Positive Estimate",
            value=f"{ticket.tactics_false_positive_estimate:.0%}",
            inline=True,
        )
        embed.add_field(
            name="Alternate Explanations Considered",
            value="\n".join(f"• {a}" for a in ticket.all_alternate_explanations[:3]),
            inline=False,
        )
        embed.set_footer(
            text="No automated action has been taken. Human moderators are reviewing this."
        )
        await ch.send(embed=embed)

    async def _send_mod_report(self, ticket: TicketEnvelope):
        ch = self.get_channel(MOD_CHANNEL_ID)
        if not ch:
            log.warning("Mod channel not found — skipping mod report")
            return

        # Send in chunks if needed (Discord 2000 char limit)
        report = ticket.mod_report
        chunks = [report[i:i+1900] for i in range(0, len(report), 1900)]

        await ch.send(f"📁 **Case File — `{ticket.ticket_id}`**")
        for chunk in chunks:
            await ch.send(f"```\n{chunk}\n```")

        # Interactive checklist embed
        embed = discord.Embed(
            title=f"Moderator Actions Required — {ticket.ticket_id}",
            description="Review the case file above and take one of the following actions:",
            color=discord.Color.dark_blue(),
        )
        embed.add_field(
            name="Action Checklist",
            value="\n".join(ticket.mod_action_checklist),
            inline=False,
        )
        embed.add_field(
            name="Account Identifiers",
            value=(
                "Available in audit log for CONFIRMED tier only. "
                f"Current tier: **{ticket.confidence_tier.value}**"
                if ticket.confidence_tier != ConfidenceTier.CONFIRMED
                else "⚠️ CONFIRMED tier — account hashes in case file. "
                     "Pull raw IDs from audit log before any action."
            ),
            inline=False,
        )
        embed.set_footer(
            text=f"Pipeline: {' → '.join(ticket.completed_agents)} "
                 f"| Rounds: {ticket.current_round}/{MAX_AGENT_ROUNDS}"
        )
        await ch.send(embed=embed)


def run():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("watchdog.log")],
    )
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set")
    bot = WatchdogBot()
    bot.run(token)


if __name__ == "__main__":
    run()
