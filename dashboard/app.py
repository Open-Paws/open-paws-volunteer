"""
Streamlit coordination dashboard for open-paws-volunteer.

Tabs:
  1. Active Dispatches  — current open requests, matches, acceptance status
  2. Volunteer Health   — engagement scores, at-risk volunteers, recent activity
  3. Phone Banking      — campaign progress, call outcomes, volunteer leaderboard
  4. XP Leaderboard     — top volunteers by XP (movement-wide, anonymized)

Run:
  streamlit run dashboard/app.py
"""
from __future__ import annotations

import os

import httpx
import streamlit as st

API_BASE = os.getenv("VOLUNTEER_API_URL", "http://localhost:8000")


def api_get(path: str) -> dict | list | None:
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None


def api_post(path: str, payload: dict) -> dict | None:
    try:
        r = httpx.post(f"{API_BASE}{path}", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Open Paws Volunteer",
    page_icon="🐾",
    layout="wide",
)

st.title("Open Paws Volunteer Coordination")

tab_dispatch, tab_health, tab_phone, tab_xp = st.tabs(
    ["Active Dispatches", "Volunteer Health", "Phone Banking", "XP Leaderboard"]
)

# ---------------------------------------------------------------------------
# Tab 1: Active Dispatches
# ---------------------------------------------------------------------------

with tab_dispatch:
    st.header("Active Dispatches")
    st.caption("Current open requests, matches, and acceptance status.")

    col1, col2 = st.columns([2, 1])

    with col1:
        available = api_get("/volunteers/available")
        if available:
            st.metric("Available Volunteers", len(available))
            st.dataframe(
                [
                    {
                        "ID": v["volunteer_id"],
                        "Org": v["org_id"],
                        "Skills": ", ".join(v["skills"]),
                        "Languages": ", ".join(v["languages"]) or "—",
                        "Engagement": v["engagement_status"],
                    }
                    for v in available
                ],
                use_container_width=True,
            )
        else:
            st.info("No available volunteers right now.")

    with col2:
        st.subheader("Create Dispatch Request")
        with st.form("dispatch_form"):
            campaign_id = st.text_input("Campaign ID")
            skills = st.multiselect(
                "Required Skills",
                ["LEGAL", "INVESTIGATION", "TECHNICAL", "COMMUNICATIONS",
                 "DIRECT_ACTION", "PHONE_BANKING", "TRANSLATION", "MEDICAL"],
            )
            urgency = st.selectbox("Urgency", ["THIS_WEEK", "TODAY", "IMMEDIATE"])
            description = st.text_area("Description")
            submitted = st.form_submit_button("Create + Auto-Match")

        if submitted and campaign_id and skills:
            result = api_post(
                "/dispatch/request",
                {
                    "campaign_id": campaign_id,
                    "required_skills": skills,
                    "urgency": urgency,
                    "description": description,
                },
            )
            if result:
                st.success(
                    f"Request created. {result['matched_count']} volunteer(s) matched."
                )
                st.json(result["top_matches"])

# ---------------------------------------------------------------------------
# Tab 2: Volunteer Health
# ---------------------------------------------------------------------------

with tab_health:
    st.header("Volunteer Health")
    st.caption("Engagement scores, at-risk volunteers, recent activity.")

    at_risk = api_get("/engagement/at-risk")
    if at_risk:
        st.warning(f"{len(at_risk)} volunteer(s) need reactivation outreach.")
        st.dataframe(
            [
                {
                    "ID": v["volunteer_id"],
                    "Org": v["org_id"],
                    "Engagement Score": v["engagement_score"],
                    "Last Active": v["last_active"] or "Never",
                }
                for v in at_risk
            ],
            use_container_width=True,
        )
    else:
        st.success("All volunteers are engaged — no reactivation needed right now.")

    st.divider()
    st.caption(
        "Engagement decays 0.1/week of inactivity. "
        "Scores below 0.3 trigger At-Risk status. "
        "Weekly decay runs automatically as a cron job."
    )

# ---------------------------------------------------------------------------
# Tab 3: Phone Banking
# ---------------------------------------------------------------------------

with tab_phone:
    st.header("Phone Banking")
    st.caption("Campaign progress, call outcomes, volunteer leaderboard.")

    campaign_id_input = st.text_input("Campaign ID (for outcome summary)")
    if campaign_id_input:
        summary = api_get(f"/calls/summary/{campaign_id_input}")
        if summary:
            st.subheader("Outcome Summary")
            cols = st.columns(len(summary))
            for col, (outcome, count) in zip(cols, summary.items()):
                col.metric(outcome, count)

    st.divider()
    st.subheader("Log a Call Outcome")
    with st.form("call_log_form"):
        log_campaign = st.text_input("Campaign ID", key="log_campaign")
        log_volunteer = st.text_input("Volunteer ID (pseudonymous)")
        log_contact = st.text_input("Contact ID")
        log_outcome = st.selectbox(
            "Outcome",
            ["answer", "no-answer", "interested", "declined", "left-voicemail"],
        )
        log_duration = st.number_input("Duration (seconds)", min_value=0, step=1)
        log_submitted = st.form_submit_button("Log Outcome")

    if log_submitted and log_campaign and log_volunteer and log_contact:
        result = api_post(
            "/calls/log",
            {
                "campaign_id": log_campaign,
                "volunteer_id": log_volunteer,
                "contact_id": log_contact,
                "outcome": log_outcome,
                "duration_seconds": int(log_duration),
            },
        )
        if result:
            st.success(f"Logged: {result['outcome']} (record {result['record_id']})")

# ---------------------------------------------------------------------------
# Tab 4: XP Leaderboard
# ---------------------------------------------------------------------------

with tab_xp:
    st.header("XP Leaderboard")
    st.caption(
        "Top volunteers by XP — anonymized. "
        "XP syncs to open-paws-platform Guild via Gary MCP."
    )

    available = api_get("/volunteers/available") or []
    if available:
        sorted_by_xp: list[dict] = sorted(
            available,
            key=lambda v: _volunteers_xp_placeholder(v["volunteer_id"]),
            reverse=True,
        )
        for rank, v in enumerate(sorted_by_xp[:10], start=1):
            st.write(f"**#{rank}** — Volunteer `{v['volunteer_id'][-6:]}` | Org: {v['org_id']}")
    else:
        st.info("No volunteers registered yet.")

    st.caption(
        "XP earned by: dispatch accepted (+50), dispatch completed (+150), "
        "call completed (+30), call interested (+75), hours logged (+100/hr)."
    )


def _volunteers_xp_placeholder(volunteer_id: str) -> int:
    """Placeholder XP lookup — replace with platform Guild API call when live."""
    import hashlib
    return int(hashlib.md5(volunteer_id.encode()).hexdigest()[:4], 16)
