"""
Customer Segmentation Dashboard — landing page.

This is the entry point for `streamlit run app.py`. It introduces the project
and links to the analytical pages defined in `pages/`.
"""

import streamlit as st


# ---------------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Customer Segmentation",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.title("Customer Segmentation Dashboard")
st.subheader("RFM-based clustering of marketing campaign customers")

st.markdown(
    """
    This dashboard explores **customer segments** derived from the
    [Customer Personality Analysis](https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis)
    dataset. Customers are scored on **Recency, Frequency, and Monetary value**
    and grouped via **K-Means clustering** to surface actionable marketing personas.
    """
)

st.divider()


# ---------------------------------------------------------------------------
# Pipeline overview
# ---------------------------------------------------------------------------
st.markdown("### Pipeline overview")

step_cols = st.columns(4)
steps = [
    ("1. Raw data", "Marketing campaign responses, demographics, and purchase channels."),
    ("2. EDA & cleaning", "Handle missing values, outliers, and engineer RFM features."),
    ("3. RFM scoring", "Compute Recency, Frequency, and Monetary metrics per customer."),
    ("4. K-Means clustering", "Group customers into actionable segments and label them."),
]
for col, (title, caption) in zip(step_cols, steps):
    with col:
        st.markdown(f"**{title}**")
        st.caption(caption)

st.divider()


# ---------------------------------------------------------------------------
# Navigation cards
# ---------------------------------------------------------------------------
st.markdown("### Explore the dashboard")

left, right = st.columns(2)

with left:
    with st.container(border=True):
        st.markdown("#### Raw data explorer")
        st.caption("Browse the original dataset with filters and column views.")
        st.page_link("pages/1_Raw_Data.py", label="Open raw data explorer")

    with st.container(border=True):
        st.markdown("#### Cluster explorer")
        st.caption("Interactive scatter view of customers colored by cluster.")
        st.page_link("pages/3_Cluster_Explorer.py", label="Open cluster explorer")

with right:
    with st.container(border=True):
        st.markdown("#### Segments overview")
        st.caption("Per-segment summary: size, RFM averages, recommended actions.")
        st.page_link("pages/2_Segments_Overview.py", label="Open segments overview")

    with st.container(border=True):
        st.markdown("#### Customer lookup")
        st.caption("Find a customer by ID to see their RFM scores and assigned cluster.")
        st.page_link("pages/4_Customer_Lookup.py", label="Open customer lookup")

st.divider()


# ---------------------------------------------------------------------------
# About / methodology
# ---------------------------------------------------------------------------
with st.expander("About this project"):
    st.markdown(
        """
        - **Methodology:** RFM scoring followed by K-Means clustering, with the elbow method used to choose `k`.
        - **Dataset:** Customer Personality Analysis (~2,200 rows, 29 columns).
        - **Stack:** Streamlit, scikit-learn, plotly, pandas.
        - **Source notebooks:** see `notebooks/exploratory_analysis.ipynb` and `notebooks/customer_kmeans.ipynb` in the repo.
        """
    )

st.caption("Built by Pablo Bagano — see the README for setup instructions.")
