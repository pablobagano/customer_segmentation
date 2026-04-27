"""
Customer lookup — search a single customer by ID and see their RFM profile.
"""

import streamlit as st

st.set_page_config(page_title="Customer lookup", layout="wide")

st.title("Customer lookup")
st.caption("Find a customer by ID and view their RFM scores plus assigned cluster.")

st.info(
    "This page is under construction. It will accept a customer ID, look the row "
    "up in `data/segmented_data.csv`, and display their RFM scores, cluster, and "
    "comparison against segment averages."
)
