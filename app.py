"""Entry point — configures the page and wires up multi-page navigation."""

import streamlit as st

st.set_page_config(
    page_title="Sports Analytics Platform",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialise session defaults ONCE before any page runs ─────────────────────
# This is the only place defaults are set.  All pages read from session_state
# so navigating between tabs never resets the team selection.
if "squad_filter" not in st.session_state:
    st.session_state["squad_filter"] = "Arsenal"   # sensible first-run default
# NOTE: do NOT pre-set "uploaded_csv" here — Streamlit raises
# StreamlitValueAssignmentNotAllowedError if you pre-assign file_uploader keys

pages = {
    "Overview": [
        st.Page("pages/dashboard.py",          title="Dashboard",          icon="🏠"),
    ],
    "Player Analytics": [
        st.Page("pages/player_performance.py", title="Player Performance", icon="📊"),
        st.Page("pages/player_comparison.py",  title="Player Comparison",  icon="🔄"),
    ],
    "Team Analytics": [
        st.Page("pages/team_analytics.py",     title="Team Analytics",     icon="🏆"),
        st.Page("pages/match_analysis.py",     title="Match Analysis",     icon="⚽"),
    ],
    "Medical & Load": [
        st.Page("pages/injury_risk.py",        title="Injury & Load Monitor", icon="⚕️"),
    ],
}

pg = st.navigation(pages)
pg.run()
