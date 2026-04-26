"""
Cluster explorer — interactive scatter view of customers colored by cluster.
"""

import streamlit as st

st.set_page_config(page_title="Cluster explorer", layout="wide")

st.title("Cluster explorer")
st.caption("Interactive 2D / 3D scatter of customers colored by their assigned cluster.")

st.info(
    "This page is under construction. It will project customers onto Recency / "
    "Frequency / Monetary axes (or PCA components) and let you drill down by cluster."
)
