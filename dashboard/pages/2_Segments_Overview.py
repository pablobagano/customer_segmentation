"""
Segments overview — per-cluster summary with recommended actions.
"""

import streamlit as st

st.set_page_config(page_title="Segments overview", layout="wide")

st.title("Segments overview")
st.caption("Cluster size, RFM averages per segment, and recommended marketing actions.")

st.info(
    "This page is under construction. It will load `data/segmented_data.csv` "
    "and surface per-cluster KPIs alongside suggested marketing playbooks."
)
