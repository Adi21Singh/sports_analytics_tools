"""Entry point — configures the page and wires up multi-page navigation."""

import streamlit as st

st.set_page_config(
    page_title="Sports Analytics Platform",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
