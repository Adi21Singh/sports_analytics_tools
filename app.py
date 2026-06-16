"""Entry point — configures the page and wires up multi-page navigation."""

import streamlit as st

st.set_page_config(
    page_title="Sports Analytics Platform",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "La Liga 2015/16 Analysis": [
        st.Page("pages/match_analysis.py",     title="Match Analysis",     icon="⚽"),
        st.Page("pages/press_intelligence.py", title="Press Intelligence", icon="🔍"),
    ],
}

pg = st.navigation(pages)
pg.run()
