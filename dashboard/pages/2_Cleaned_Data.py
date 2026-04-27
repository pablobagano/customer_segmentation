"""
Cleaned Data — business dashboard over the post-cleaning customer dataset.

Layout responsibility lives here; figure logic lives in ``charts.py``.
"""

import streamlit as st
import pandas as pd

import charts
from data_paths import TREATED_DATA


# --------------------------------------------------------------------------- #
# Page setup
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="Cleaned data — dashboard", layout="wide")

st.title("Customer dashboard")
st.caption(
    "Business view of the cleaned customer dataset — demographics, spending, "
    "channels, and campaign performance."
)


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #

@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(TREATED_DATA)
    df["Dt_Customer"] = pd.to_datetime(df["Dt_Customer"])
    return df


df_full = load_data()


# --------------------------------------------------------------------------- #
# Filter strip
# --------------------------------------------------------------------------- #

with st.container():
    f1, f2, f3 = st.columns([2, 2, 1])

    with f1:
        edu_options = sorted(df_full["Education"].unique())
        edu_filter = st.multiselect(
            "Education", edu_options, default=edu_options,
        )
    with f2:
        mar_options = sorted(df_full["Marital_Status"].unique())
        mar_filter = st.multiselect(
            "Marital status", mar_options, default=mar_options,
        )
    with f3:
        kids_filter = st.selectbox(
            "Has kids in home?",
            options=["All", "Yes", "No"],
            index=0,
        )

mask = (
    df_full["Education"].isin(edu_filter)
    & df_full["Marital_Status"].isin(mar_filter)
)
if kids_filter == "Yes":
    mask &= (df_full["Kidhome"] + df_full["Teenhome"]) > 0
elif kids_filter == "No":
    mask &= (df_full["Kidhome"] + df_full["Teenhome"]) == 0

df = df_full[mask]

if len(df) == 0:
    st.warning("No customers match the selected filters.")
    st.stop()

st.caption(
    f"Showing **{len(df):,}** of {len(df_full):,} customers "
    f"({len(df) / len(df_full) * 100:.1f}% of cleaned dataset)."
)


# --------------------------------------------------------------------------- #
# 1. KPI scorecard
# --------------------------------------------------------------------------- #

st.divider()

kpis = charts.kpi_scorecard(df)
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Customers", f"{kpis['total_customers']:,}")
k2.metric("Total revenue", f"${kpis['total_revenue']:,.0f}")
k3.metric("Avg. customer value", f"${kpis['avg_customer_value']:,.0f}")
k4.metric("Last campaign response", f"{kpis['last_campaign_response'] * 100:.1f}%")
k5.metric("Cumulative acceptance", f"{kpis['cumulative_acceptance'] * 100:.1f}%")
k6.metric("Complaint rate", f"{kpis['complaint_rate'] * 100:.2f}%")


# --------------------------------------------------------------------------- #
# 2. Customer demographics
# --------------------------------------------------------------------------- #

st.divider()
st.subheader("Customer demographics")
st.caption("Who are our customers?")

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(charts.demo_age_hist(df), use_container_width=True)
with c2:
    st.plotly_chart(charts.demo_income_hist(df), use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.plotly_chart(charts.demo_education_donut(df), use_container_width=True)
with c4:
    st.plotly_chart(charts.demo_marital_donut(df), use_container_width=True)

c5, c6 = st.columns(2)
with c5:
    st.plotly_chart(charts.demo_household_heatmap(df), use_container_width=True)
with c6:
    st.plotly_chart(charts.demo_acquisition_curve(df), use_container_width=True)


# --------------------------------------------------------------------------- #
# 3. Spending behavior
# --------------------------------------------------------------------------- #

st.divider()
st.subheader("Spending behavior")
st.caption("What do they buy?")

c7, c8 = st.columns(2)
with c7:
    st.plotly_chart(charts.spend_product_share(df), use_container_width=True)
with c8:
    st.plotly_chart(charts.spend_highest_breakdown(df), use_container_width=True)

st.plotly_chart(charts.spend_total_distribution(df), use_container_width=True)

scatter_color = st.radio(
    "Color the scatter by",
    options=["Highest_Spent", "Marital_Status", "Education"],
    horizontal=True,
    key="scatter_color",
)
st.plotly_chart(
    charts.spend_vs_income_scatter(df, color_by=scatter_color),
    use_container_width=True,
)


# --------------------------------------------------------------------------- #
# 4. Channels
# --------------------------------------------------------------------------- #

st.divider()
st.subheader("Purchase channels")
st.caption("How do they buy?")

c9, c10 = st.columns(2)
with c9:
    st.plotly_chart(charts.channel_mix(df), use_container_width=True)
with c10:
    st.plotly_chart(
        charts.channel_web_visits_vs_purchases(df), use_container_width=True
    )

channel_dim = st.selectbox(
    "Group channel preference by",
    options=["Education", "Marital_Status"],
    key="channel_dim",
)
st.plotly_chart(
    charts.channel_preference_by(df, dimension=channel_dim),
    use_container_width=True,
)


# --------------------------------------------------------------------------- #
# 5. Campaign performance
# --------------------------------------------------------------------------- #

st.divider()
st.subheader("Campaign performance")
st.caption("Are our campaigns working?")

c11, c12 = st.columns(2)
with c11:
    st.plotly_chart(charts.campaign_response_rates(df), use_container_width=True)
with c12:
    st.plotly_chart(
        charts.campaign_acceptance_distribution(df), use_container_width=True
    )

campaign_dim = st.selectbox(
    "Group response rate by",
    options=["Education", "Marital_Status"],
    key="campaign_dim",
)
c13, c14 = st.columns(2)
with c13:
    st.plotly_chart(
        charts.campaign_response_by(df, dimension=campaign_dim),
        use_container_width=True,
    )
with c14:
    st.plotly_chart(
        charts.campaign_recency_vs_response(df), use_container_width=True
    )


# --------------------------------------------------------------------------- #
# 6. Cross-cuts (segment foreshadowing)
# --------------------------------------------------------------------------- #

st.divider()
st.subheader("Segment foreshadowing")
st.caption("Cross-cuts that hint at natural customer groups.")

c15, c16 = st.columns(2)
with c15:
    st.plotly_chart(charts.cross_spend_heatmap(df), use_container_width=True)
with c16:
    st.plotly_chart(charts.cross_top_decile_profile(df), use_container_width=True)

st.page_link(
    "pages/3_Cluster_Explorer.py",
    label="→ Explore the clustered customers",
)


# --------------------------------------------------------------------------- #
# Cleaning notes
# --------------------------------------------------------------------------- #

st.divider()
with st.expander("Cleaning notes — what changed vs. raw"):
    st.markdown(
        """
        - **Dropped constants** — `Z_CostContact` and `Z_Revenue` were removed; both had zero variance.
        - **`Income` cleanup** — one extreme outlier dropped; remaining 24 nulls imputed with the **median**.
        - **`Dt_Customer` → `datetime`** — parsed for time-based analysis.
        - **Age outliers (`>120`)** — two impossible records dropped, one mean-imputed.
        - **`Marital_Status` consolidated** — `Alone`, `Absurd`, `YOLO` merged into `Single`.
        - **Engineered features** — `Total_Spent`, `Total_Purchases`, `Highest_Spent`, `Age`.
        - See **Raw Data → Info** for the full narrative.
        """
    )
