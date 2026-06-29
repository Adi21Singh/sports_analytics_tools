"""
ui/data_source.py

Sidebar widget for team / CSV selection, and the get_data() helper used by
every analytics page.

Design decisions
----------------
- Demo data has been removed.  The app always uses real FBref data.
- The selected team is stored in st.session_state["squad_filter"] which is
  initialised once in app.py before any page runs.  Navigating between tabs
  never resets the selection because Streamlit preserves session_state values
  for widget keys that already exist.
- Uploading a custom CSV is optional.  Leaving it blank uses the bundled
  players_data-2025_2026.csv that ships with the project.
"""

from __future__ import annotations
import streamlit as st

_CSV_PATH = "players_data-2025_2026.csv"


def render_data_source_selector() -> None:
    """
    Render team picker + optional CSV uploader inside `with st.sidebar:`.

    On first run the squad defaults to whatever was set in app.py
    (currently 'Arsenal').  The user can change it at any time; the new value
    persists across all pages for the rest of the session.
    """
    st.markdown("---")
    st.markdown("**Team**")

    # ── Optional custom CSV upload ────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Upload FBref CSV (optional)",
        type=["csv"],
        key="uploaded_csv",
        help=(
            "Leave blank to use the bundled 2025/26 dataset.  "
            "Upload any FBref-format player stats CSV to analyse a "
            "different season or league."
        ),
        label_visibility="collapsed",
    )
    csv_src = uploaded.getvalue() if (uploaded is not None and hasattr(uploaded, "getvalue")) else _CSV_PATH
    if uploaded is not None:
        st.caption(f"📂 {uploaded.name}")
    else:
        st.caption("Using bundled 2025/26 dataset")

    # ── Team selector ─────────────────────────────────────────────────────────
    try:
        from data.real_loader import get_available_squads
        squads = get_available_squads(csv_src)
    except Exception as exc:
        st.error(f"Could not read team list: {exc}")
        st.markdown("---")
        return

    if not squads:
        st.warning("No teams found in the dataset.")
        st.markdown("---")
        return

    # Do NOT pass index= here - session_state["squad_filter"] is already set
    # in app.py before any page runs, so Streamlit uses that value directly.
    # Passing index= alongside a pre-set session_state key triggers a warning.
    st.selectbox(
        "Select team",
        squads,
        key="squad_filter",
        label_visibility="collapsed",
    )
    st.markdown("---")


def get_data() -> tuple:
    """
    Return (players, training, wellness, matches, match_players, events)
    for the currently selected team.

    Always uses real FBref data.  Falls back to demo data only if an
    unrecoverable file error occurs, and displays a clear error message.
    """
    squad = st.session_state.get("squad_filter")
    # uploaded_csv key may not exist yet on first run (file_uploader manages its own state)
    uploaded = st.session_state.get("uploaded_csv", None)
    csv_src = uploaded.getvalue() if (uploaded is not None and hasattr(uploaded, "getvalue")) else _CSV_PATH

    if not squad:
        # Should not happen because app.py initialises squad_filter, but
        # guard defensively.
        st.warning("No team selected - showing demo data.", icon="⚠️")
        from data.generator import load_data
        return load_data()

    from data.real_loader import load_real_data
    try:
        with st.spinner(f"Loading {squad}…"):
            return load_real_data(csv_path=csv_src, squad_filter=squad)
    except FileNotFoundError:
        st.error(
            "Dataset file not found.  Upload a CSV in the sidebar or make "
            "sure `players_data-2025_2026.csv` is in the project folder."
        )
    except ValueError as exc:
        st.error(f"Data error: {exc}")
    except Exception as exc:
        st.error(f"Unexpected error loading data: {exc}")

    st.info("Showing demo data while the issue is resolved.")
    from data.generator import load_data
    return load_data()
