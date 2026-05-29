"""
ui/data_source.py

Shared sidebar component: data-source toggle, optional CSV upload,
squad selector, and a get_data() helper with spinner + error handling.
"""

from __future__ import annotations
import streamlit as st

_CSV_PATH = "players_data-2025_2026.csv"


def render_data_source_selector() -> None:
    """
    Render inside `with st.sidebar:`.
    Manages data_mode, squad_filter, and uploaded_csv in session_state.
    """
    st.markdown("---")
    st.markdown("**Data Source**")

    st.radio(
        "Source",
        ["Demo Data", "Real Data (FBref 25/26)"],
        key="data_mode",
        label_visibility="collapsed",
    )

    if st.session_state.get("data_mode") == "Real Data (FBref 25/26)":
        st.file_uploader(
            "Upload FBref CSV",
            type=["csv"],
            key="uploaded_csv",
            help=(
                "Optional — leave blank to use the bundled 2025/26 dataset. "
                "Upload any FBref-format player stats CSV to analyse a different season."
            ),
        )

        uploaded = st.session_state.get("uploaded_csv")
        csv_src = uploaded.getvalue() if uploaded is not None else _CSV_PATH

        if uploaded is not None:
            st.caption(f"File: {uploaded.name}")
        else:
            st.caption("Using bundled 2025/26 dataset")

        try:
            from data.real_loader import get_available_squads
            squads = get_available_squads(csv_src)
            if not squads:
                st.warning("No teams found in the dataset.")
            else:
                default_idx = squads.index("Arsenal") if "Arsenal" in squads else 0
                st.selectbox("Team", squads, index=default_idx, key="squad_filter")
        except Exception as exc:
            st.error(f"Could not read team list: {exc}")
    else:
        st.session_state["squad_filter"] = None

    st.markdown("---")


def get_data() -> tuple:
    """
    Return (players, training, wellness, matches, match_players, events).

    Guards against loading before a team is selected, shows a spinner on
    first load, and falls back to demo data with a clear error on failure.
    """
    mode = st.session_state.get("data_mode", "Demo Data")

    if mode == "Real Data (FBref 25/26)":
        squad = st.session_state.get("squad_filter")

        # Squad not yet selected — render a helpful prompt and use demo data
        if not squad:
            st.info("Select a team from the sidebar to load real data.", icon="ℹ️")
            from data.generator import load_data
            return load_data()

        from data.real_loader import load_real_data
        uploaded = st.session_state.get("uploaded_csv")
        csv_src = uploaded.getvalue() if uploaded is not None else _CSV_PATH

        try:
            with st.spinner(f"Loading {squad} data..."):
                return load_real_data(csv_path=csv_src, squad_filter=squad)
        except FileNotFoundError:
            st.error(
                "Dataset file not found. Upload a CSV in the sidebar or make sure "
                "`players_data-2025_2026.csv` is in the project folder."
            )
            st.info("Showing demo data instead.")
        except ValueError as exc:
            st.error(f"Data error: {exc}")
            st.info("Showing demo data instead.")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            st.info("Showing demo data instead.")

        from data.generator import load_data
        return load_data()

    from data.generator import load_data
    return load_data()
