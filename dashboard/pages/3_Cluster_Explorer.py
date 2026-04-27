"""
Cluster Explorer — RFM-based customer segmentation.

Four tabs: Methodology (pedagogy), 3D Cluster View (RFM space + pairwise),
Segment Dashboard (per-segment business view), Compare Segments (side-by-side).
"""

import streamlit as st
import pandas as pd

import charts
from data_paths import SEGMENTED_DATA


# --------------------------------------------------------------------------- #
# Page setup
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="Cluster explorer", layout="wide")

st.title("Cluster explorer")
st.caption(
    "RFM-based customer segmentation — methodology, 3D view, "
    "and per-segment business dashboards."
)


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(SEGMENTED_DATA)
    df["Dt_Customer"] = pd.to_datetime(df["Dt_Customer"])
    return df


df = load_data()

tab_method, tab_3d, tab_segment, tab_compare = st.tabs([
    "Methodology",
    "3D Cluster View",
    "Segment Dashboard",
    "Compare Segments",
])


# --------------------------------------------------------------------------- #
# Tab 1 — Methodology
# --------------------------------------------------------------------------- #

with tab_method:
    st.markdown(
        """
        ### What is RFM?

        **RFM** is a customer-scoring framework used in CRM and marketing to
        rank customers on three behavioral dimensions:

        - **Recency** — how recently the customer last purchased. *Lower is better.*
        - **Frequency** — how often they purchase. *Higher is better.*
        - **Monetary** — how much they spend overall. *Higher is better.*

        Customers with strong scores across all three are your most valuable;
        weak scores across all three are churn risks. The three-way split also
        separates customer types that pure revenue ranking would conflate —
        e.g. a high-spend customer with stale recency behaves very differently
        from a high-spend customer with recent activity.

        #### How RFM maps to our dataset

        | RFM dimension | Source column     | Direction        |
        |---------------|-------------------|------------------|
        | Recency       | `Recency`         | lower is better  |
        | Frequency     | `Total_Purchases` | higher is better |
        | Monetary      | `Total_Spent`     | higher is better |

        `Total_Purchases` is the sum of all `Num*Purchases` channels (deals +
        web + catalog + store), and `Total_Spent` is the sum of all `Mnt*`
        product categories — both engineered during the cleaning phase.
        """
    )

    st.divider()

    st.markdown(
        """
        ### From clusters to a score

        **Why K-Means?** K-Means is an unsupervised algorithm that partitions
        data into `k` groups by minimizing within-cluster variance. It's a
        natural fit for RFM because each dimension has clear "tiers" of
        customer behavior that aren't pre-labeled.

        **Why three 1D models, not one 3D model?** This pipeline runs K-Means
        **once per RFM dimension** — three separate models on `Total_Purchases`,
        `Total_Spent`, and `Recency`. This avoids two pitfalls of joint 3D
        clustering:

        1. The three dimensions live on wildly different scales (days vs.
           dollars vs. counts), so joint clustering would require careful
           normalization.
        2. Each dimension has its own natural breakpoints — running K-Means
           independently respects them.

        **Hyperparameter search.** Each 1D model is tuned with
        `RandomizedSearchCV` over `n_clusters ∈ [2..4]`,
        `init ∈ {'k-means++', 'random'}`, `n_init ∈ [10..50]`,
        `max_iter ∈ [100..700]`. The cluster cap of 4 is deliberate: too many
        clusters per dimension makes the final segments hard to translate into
        marketing actions. All three searches converged on `k = 4`.

        **From cluster label to score.** The cluster ID itself is meaningless
        (K-Means assigns IDs arbitrarily), so each component's clusters are
        re-ranked by their average value:

        - `Frequency_Score` and `Monetary_Score` — clusters sorted ascending
          by average → scores `0 → 3`.
        - `Recency_Score` — clusters sorted **descending** by average →
          scores `0 → 3` *(recent = high score)*.

        **The final RFM score.** The three scores sum into a single
        `RMF_Score` from 0 to 9, which is bucketed into five business segments:

        | Score range | Segment    |
        |-------------|------------|
        | 0           | Inactive   |
        | 1–2         | Occasional |
        | 3–4         | Moderate   |
        | 5–6         | Loyal      |
        | 7–9         | Premium    |

        > **Worth flagging:** the final segments are not K-Means clusters in
        > 3D — they're score-bucket labels. A Premium customer is defined as
        > "RMF_Score ≥ 7," not "member of cluster X."
        """
    )


# --------------------------------------------------------------------------- #
# Tab 2 — 3D Cluster View
# --------------------------------------------------------------------------- #

with tab_3d:
    st.subheader("RFM space")
    st.caption(
        "Each point is a customer plotted on the three RFM dimensions. "
        "Toggle segments on/off and rotate to explore."
    )

    f1, f2 = st.columns([2, 3])
    with f1:
        color_choice = st.radio(
            "Color by",
            options=["Segmentation", "Cluster_Recency", "Cluster_Frequency", "Cluster_Monetary"],
            horizontal=False,
            key="3d_color",
            help=(
                "Segmentation = the final score-bucket labels. "
                "Cluster_* = the per-component K-Means labels — these form "
                "horizontal slabs in 3D, visually proving K-Means ran on "
                "one dimension at a time."
            ),
        )
    with f2:
        if color_choice == "Segmentation":
            selected_segments = st.multiselect(
                "Show segments",
                options=charts.SEGMENT_ORDER,
                default=charts.SEGMENT_ORDER,
                key="3d_segments",
            )
        else:
            selected_segments = charts.SEGMENT_ORDER  # no segment filter

    df_3d = df[df["Segmentation"].isin(selected_segments)]
    if len(df_3d) == 0:
        st.warning("Select at least one segment to display.")
    else:
        st.plotly_chart(
            charts.cluster_3d_scatter(df_3d, color_by=color_choice),
            use_container_width=True,
        )

    st.divider()

    st.subheader("2D pairwise projections")
    st.caption(
        "Three pairwise views of the same RFM space — easier to read densities "
        "than the 3D view alone."
    )

    p1, p2, p3 = st.columns(3)
    with p1:
        st.plotly_chart(
            charts.cluster_pairwise_2d(df, "Total_Purchases", "Recency"),
            use_container_width=True,
        )
    with p2:
        st.plotly_chart(
            charts.cluster_pairwise_2d(df, "Total_Purchases", "Total_Spent"),
            use_container_width=True,
        )
    with p3:
        st.plotly_chart(
            charts.cluster_pairwise_2d(df, "Recency", "Total_Spent"),
            use_container_width=True,
        )

    st.divider()

    st.plotly_chart(charts.segment_count_bar(df), use_container_width=True)


# --------------------------------------------------------------------------- #
# Tab 3 — Segment Dashboard
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

with tab_segment:
    selected = st.selectbox(
        "Select segment",
        options=charts.SEGMENT_ORDER,
        index=charts.SEGMENT_ORDER.index("Premium"),
    )

    seg_df = df[df["Segmentation"] == selected]
    if len(seg_df) == 0:
        st.warning(f"No customers in the {selected} segment.")
        st.stop()

    kpi = charts.segment_scorecard(seg_df, df)

    # Persona summary
    st.info(f"**{selected}** — {PERSONAS[selected]}")

    # Scorecard
    st.divider()
    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    k1.metric(
        "Customers",
        f"{kpi['customers']:,}",
        f"{kpi['customers'] / kpi['baseline_customers'] * 100:.1f}% of base",
        delta_color="off",
    )
    k2.metric(
        "Avg RFM score",
        f"{kpi['avg_rfm']:.1f}",
        f"{kpi['avg_rfm'] - kpi['avg_rfm_baseline']:+.1f} vs avg",
    )
    k3.metric(
        "Avg Total Spent",
        f"${kpi['avg_total_spent']:,.0f}",
        f"{kpi['avg_total_spent'] - kpi['avg_total_spent_baseline']:+,.0f} vs avg",
    )
    k4.metric(
        "Avg Purchases",
        f"{kpi['avg_total_purchases']:.1f}",
        f"{kpi['avg_total_purchases'] - kpi['avg_total_purchases_baseline']:+.1f} vs avg",
    )
    k5.metric(
        "Avg Recency (days)",
        f"{kpi['avg_recency']:.0f}",
        f"{kpi['avg_recency'] - kpi['avg_recency_baseline']:+.0f} vs avg",
        delta_color="inverse",  # lower recency = better
    )
    k6.metric(
        "Avg APV",
        f"${kpi['avg_apv']:.2f}",
        f"{kpi['avg_apv'] - kpi['avg_apv_baseline']:+.2f} vs avg",
    )
    k7.metric(
        "Response rate",
        f"{kpi['response_rate'] * 100:.1f}%",
        f"{(kpi['response_rate'] - kpi['response_rate_baseline']) * 100:+.1f}pp",
    )

    # Demographics — reuse charts.py factories on the segment slice
    st.divider()
    st.subheader("Demographics")

    d1, d2 = st.columns(2)
    with d1:
        st.plotly_chart(charts.demo_age_hist(seg_df), use_container_width=True)
    with d2:
        st.plotly_chart(charts.demo_income_hist(seg_df), use_container_width=True)

    d3, d4 = st.columns(2)
    with d3:
        st.plotly_chart(charts.demo_education_donut(seg_df), use_container_width=True)
    with d4:
        st.plotly_chart(charts.demo_marital_donut(seg_df), use_container_width=True)

    # Spending & channels
    st.divider()
    st.subheader("Spending & channels")

    s1, s2 = st.columns(2)
    with s1:
        st.plotly_chart(charts.spend_product_share(seg_df), use_container_width=True)
    with s2:
        st.plotly_chart(charts.spend_highest_breakdown(seg_df), use_container_width=True)

    st.plotly_chart(charts.channel_mix(seg_df), use_container_width=True)

    # Campaign response
    st.divider()
    st.subheader("Campaign response")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.campaign_response_rates(seg_df), use_container_width=True)
    with c2:
        st.plotly_chart(
            charts.campaign_acceptance_distribution(seg_df), use_container_width=True
        )

    # Recommended actions
    st.divider()
    with st.expander(f"Recommended marketing actions — {selected}", expanded=True):
        for action in ACTIONS[selected]:
            st.markdown(f"- {action}")


# --------------------------------------------------------------------------- #
# Tab 4 — Compare Segments
# --------------------------------------------------------------------------- #

with tab_compare:
    st.subheader("Side-by-side segment comparison")
    st.caption(
        "Conditional formatting: green = better on each metric. "
        "Recency uses an inverted scale (lower days = better)."
    )

    comp = charts.segments_comparison_df(df)

    higher_better = [
        "Avg_RFM_Score", "Avg_Frequency", "Avg_Monetary", "Avg_APV", "Response_Rate",
    ]
    lower_better = ["Avg_Recency"]

    styled = (
        comp.style.format({
            "Customers": "{:,}",
            "Share": "{:.1%}",
            "Avg_RFM_Score": "{:.1f}",
            "Avg_Recency": "{:.0f} days",
            "Avg_Frequency": "{:.1f}",
            "Avg_Monetary": "${:,.0f}",
            "Avg_APV": "${:.2f}",
            "Response_Rate": "{:.1%}",
        })
        .background_gradient(subset=higher_better, cmap="RdYlGn")
        .background_gradient(subset=lower_better, cmap="RdYlGn_r")
    )

    st.dataframe(styled, use_container_width=True)

    st.divider()

    st.subheader("Segment trajectories — parallel coordinates")
    st.caption(
        "Each line is a customer; line color encodes segment tier "
        "(gray = Inactive → red = Premium). Drag the axis ranges to filter."
    )
    st.plotly_chart(charts.segments_parallel_coords(df), use_container_width=True)
