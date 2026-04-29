"""
Customer Lookup — drill down on a single customer and compare them against
their assigned segment and the full population.

Selection: filter strip → selectbox of matching IDs, with a fallback
"Lookup by ID" number_input for direct entry.

Layout (single scrollable page):
    Hero block (segment badge + persona + tenure)
    Profile row (5 metric cards)
    RFM scorecard (4 metric cards with deltas vs segment median)
    Radar (customer / segment median / population median)
    Spend allocation (bar with segment + population mean overlays)
    Channel preference (bar with segment + population mean overlays)
    Campaign engagement (6 chips)
    Position in RFM space (3D scatter with customer highlighted)
    Recommended actions (from the segment's ACTIONS dict)
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import charts
from data_paths import SEGMENTED_DATA


# --------------------------------------------------------------------------- #
# Page setup + data
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="Customer lookup", layout="wide")

st.title("Customer lookup")
st.caption(
    "Pick a customer and see their RFM profile in context — versus their "
    "assigned segment and the full population."
)


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(SEGMENTED_DATA)
    df["Dt_Customer"] = pd.to_datetime(df["Dt_Customer"])
    return df


df = load_data()


# --------------------------------------------------------------------------- #
# Personas + recommended actions — kept in sync with 3_Cluster_Explorer.py
# --------------------------------------------------------------------------- #

PERSONAS = {
    "Premium": (
        "Recent, frequent, high-spend customers — your VIPs. Retention and "
        "reward programs are the priority."
    ),
    "Loyal": (
        "Frequent buyers with strong engagement, slightly below Premium spend. "
        "Upsell and cross-sell opportunities."
    ),
    "Moderate": (
        "Mid-tier across all RFM dimensions. The largest segment — biggest "
        "activation opportunity."
    ),
    "Occasional": (
        "Light buyers across all RFM dimensions — one step above Inactive. "
        "Reactivation and onboarding campaigns are the priority."
    ),
    "Inactive": (
        "Disengaged across all RFM dimensions. Win-back campaigns or "
        "churn-reason surveys."
    ),
}

ACTIONS = {
    "Premium": [
        "VIP perks: early access, exclusive products, dedicated account management",
        "Loyalty rewards tied to spend tier",
        "Cross-sell premium product lines",
        "Personalized concierge campaigns",
    ],
    "Loyal": [
        "Subscription or auto-replenishment programs",
        "Referral rewards (high engagement = good ambassadors)",
        "Targeted upsell into premium products",
        "Bundle offers to increase basket size",
    ],
    "Moderate": [
        "Surprise/delight campaigns to nudge into Loyal",
        "Targeted offers based on Highest_Spent category",
        "Email series to increase frequency",
        "Free shipping thresholds to lift basket size",
    ],
    "Occasional": [
        "Reactivation campaigns with low-friction first-step offers",
        "Onboarding email series for newer customers",
        "Repeat-purchase incentives (free shipping, second-purchase discount)",
        "Retargeting based on first-purchase category",
    ],
    "Inactive": [
        "Win-back campaigns with deep discounts",
        "Survey to understand churn reasons",
        "Re-engagement email series with curated content",
        "If unresponsive after 90 days, deprioritize from active marketing spend",
    ],
}

CAMPAIGN_LABELS = {
    "AcceptedCmp1": "Cmp 1",
    "AcceptedCmp2": "Cmp 2",
    "AcceptedCmp3": "Cmp 3",
    "AcceptedCmp4": "Cmp 4",
    "AcceptedCmp5": "Cmp 5",
    "Response": "Last (Response)",
}


# --------------------------------------------------------------------------- #
# Selection — filter strip + selectbox + ID input fallback
# --------------------------------------------------------------------------- #

st.subheader("Find a customer")

with st.container(border=True):
    fc1, fc2, fc3, fc4 = st.columns([1.2, 1.2, 1.2, 1])

    seg_filter = fc1.multiselect(
        "Segment",
        options=charts.SEGMENT_ORDER,
        default=charts.SEGMENT_ORDER,
    )
    edu_filter = fc2.multiselect(
        "Education",
        options=sorted(df["Education"].unique().tolist()),
        default=sorted(df["Education"].unique().tolist()),
    )
    mar_filter = fc3.multiselect(
        "Marital status",
        options=sorted(df["Marital_Status"].unique().tolist()),
        default=sorted(df["Marital_Status"].unique().tolist()),
    )
    kids_filter = fc4.selectbox(
        "Has kids at home",
        options=["Any", "Yes", "No"],
        index=0,
    )

    filtered = df[
        df["Segmentation"].isin(seg_filter)
        & df["Education"].isin(edu_filter)
        & df["Marital_Status"].isin(mar_filter)
    ]
    if kids_filter == "Yes":
        filtered = filtered[(filtered["Kidhome"] + filtered["Teenhome"]) > 0]
    elif kids_filter == "No":
        filtered = filtered[(filtered["Kidhome"] + filtered["Teenhome"]) == 0]

    sc1, sc2 = st.columns([2, 1])
    if len(filtered) == 0:
        sc1.warning("No customers match those filters. Loosen the filter strip.")
        st.stop()

    selected_id = sc1.selectbox(
        f"Customer ID — {len(filtered):,} match the filters",
        options=sorted(filtered["ID"].unique().tolist()),
        index=0,
    )
    typed_id = sc2.number_input(
        "Or look up by ID directly",
        min_value=int(df["ID"].min()),
        max_value=int(df["ID"].max()),
        value=int(selected_id),
        step=1,
        help="Overrides the selectbox above.",
    )

    customer_id = int(typed_id)
    if customer_id not in df["ID"].values:
        st.error(f"Customer ID {customer_id} not found in the dataset.")
        st.stop()


# --------------------------------------------------------------------------- #
# Compute KPIs once
# --------------------------------------------------------------------------- #

kpi = charts.lookup_kpis(df, customer_id)
segment = kpi["segmentation"]
seg_color = charts.SEGMENT_PALETTE.get(segment, "#1f77b4")


# --------------------------------------------------------------------------- #
# Hero block — segment badge + persona + tenure
# --------------------------------------------------------------------------- #

st.divider()

hc1, hc2 = st.columns([1, 3])
with hc1:
    st.markdown(
        f"""
        <div style="
            background-color: {seg_color};
            color: white;
            padding: 18px 14px;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
        ">
            <div style="font-size: 12px; opacity: 0.85;">SEGMENT</div>
            <div style="font-size: 26px; line-height: 1.1; margin-top: 4px;">
                {segment}
            </div>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 8px;">
                Customer #{kpi['id']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with hc2:
    st.info(f"**{segment}** — {PERSONAS[segment]}")
    enrolled = pd.Timestamp(kpi["dt_customer"]).date().isoformat()
    st.caption(
        f"Enrolled **{enrolled}** &nbsp;·&nbsp; "
        f"tenure **{kpi['tenure_years']:.1f} years**"
    )


# --------------------------------------------------------------------------- #
# Profile row
# --------------------------------------------------------------------------- #

st.divider()
st.markdown("#### Profile")

p1, p2, p3, p4, p5 = st.columns(5)
p1.metric("Age", f"{kpi['age']}")
p2.metric("Income", f"${kpi['income']:,.0f}")
p3.metric("Education", kpi["education"])
p4.metric("Marital status", kpi["marital_status"])
p5.metric(
    "Kids at home",
    f"{kpi['total_kids']}",
    f"{kpi['kidhome']} kid · {kpi['teenhome']} teen",
    delta_color="off",
)


# --------------------------------------------------------------------------- #
# RFM scorecard — customer values with deltas vs segment median
# --------------------------------------------------------------------------- #

st.divider()
st.markdown("#### RFM scorecard")
st.caption(
    "Component scores are 0–3 each (cluster rank within their dimension). "
    "Combined RFM score is 0–9. Deltas compare against the customer's segment median."
)

r1, r2, r3, r4 = st.columns(4)
r1.metric(
    "Recency",
    f"{kpi['recency']} days",
    f"{kpi['recency'] - kpi['recency_seg_median']:+.0f} vs seg median",
    delta_color="inverse",  # lower recency is better
)
r2.metric(
    "Frequency",
    f"{kpi['frequency']} purchases",
    f"{kpi['frequency'] - kpi['frequency_seg_median']:+.1f} vs seg median",
)
r3.metric(
    "Monetary",
    f"${kpi['monetary']:,.0f}",
    f"{kpi['monetary'] - kpi['monetary_seg_median']:+,.0f} vs seg median",
)
r4.metric(
    "RFM score",
    f"{kpi['rfm_score']} / 9",
    f"{kpi['rfm_score'] - kpi['rfm_seg_median']:+.1f} vs seg median",
)

s1, s2, s3, s4 = st.columns(4)
s1.metric("Recency score", f"{kpi['recency_score']} / 3")
s2.metric("Frequency score", f"{kpi['frequency_score']} / 3")
s3.metric("Monetary score", f"{kpi['monetary_score']} / 3")
s4.metric(
    "Avg purchase value",
    f"${kpi['apv']:,.2f}",
    f"{kpi['apv'] - kpi['apv_seg_median']:+,.2f} vs seg median",
)


# --------------------------------------------------------------------------- #
# Radar — customer vs segment median vs population median
# --------------------------------------------------------------------------- #

st.divider()
st.markdown("#### Customer vs segment vs population")
st.caption(
    "All axes normalized 0–1 against the full population. Recency is **inverted** "
    "so every axis reads *higher is better*."
)
st.plotly_chart(
    charts.lookup_radar(df, customer_id),
    use_container_width=True,
)


# --------------------------------------------------------------------------- #
# Spend allocation
# --------------------------------------------------------------------------- #

st.divider()
st.markdown("#### Spend allocation")
st.caption(
    f"Bars = customer's spend per category. Diamond = {segment} mean. "
    "X = population mean."
)
st.plotly_chart(
    charts.lookup_spend_vs_segment(df, customer_id),
    use_container_width=True,
)


# --------------------------------------------------------------------------- #
# Channel preference
# --------------------------------------------------------------------------- #

st.divider()
st.markdown("#### Channel preference")
st.caption(
    f"Bars = customer's purchases per channel. Diamond = {segment} mean. "
    "X = population mean."
)
st.plotly_chart(
    charts.lookup_channels_vs_segment(df, customer_id),
    use_container_width=True,
)


# --------------------------------------------------------------------------- #
# Campaign engagement — 6 chips
# --------------------------------------------------------------------------- #

st.divider()
st.markdown("#### Campaign engagement")

row = df.loc[df["ID"] == customer_id].iloc[0]
chip_cols = st.columns(6)
for col, (cmp_col, label) in zip(chip_cols, CAMPAIGN_LABELS.items()):
    accepted = bool(row[cmp_col])
    bg = "#2ca02c" if accepted else "#e0e0e0"
    fg = "white" if accepted else "#666"
    badge = "Accepted" if accepted else "Declined"
    col.markdown(
        f"""
        <div style="
            background-color: {bg};
            color: {fg};
            padding: 14px 8px;
            border-radius: 8px;
            text-align: center;
            font-weight: 600;
        ">
            <div style="font-size: 11px; opacity: 0.85;">{label}</div>
            <div style="font-size: 16px; margin-top: 4px;">{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.caption(
    f"**{kpi['campaigns_accepted']} / 6** campaigns accepted overall."
)


# --------------------------------------------------------------------------- #
# Position in RFM space
# --------------------------------------------------------------------------- #

st.divider()
st.markdown("#### Position in RFM space")
st.caption(
    "Black diamond marks this customer against the full segmented cloud. "
    "Center of their segment cluster vs. edge tells you whether they're a "
    "typical example or a borderline case."
)
st.plotly_chart(
    charts.lookup_3d_highlight(df, customer_id),
    use_container_width=True,
)


# --------------------------------------------------------------------------- #
# Recommended actions
# --------------------------------------------------------------------------- #

st.divider()
st.markdown(f"#### Recommended actions for {segment} customers")

ac1, ac2 = st.columns(2)
half = (len(ACTIONS[segment]) + 1) // 2
for i, action in enumerate(ACTIONS[segment]):
    (ac1 if i < half else ac2).markdown(f"- {action}")

st.caption(
    "Generic per-segment playbook. The radar above plus the spend/channel "
    "overlays give the per-customer twist."
)
