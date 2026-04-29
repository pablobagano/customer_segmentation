"""
charts.py — figure factories for the Cleaned Data business dashboard.

Every public function in this module takes the cleaned customer dataframe and
returns a Plotly ``Figure`` (or, for KPI helpers, a ``dict`` of metric values).
All functions are *pure*: they do NOT call any ``st.*`` APIs. Page modules
(e.g. ``pages/2_Cleaned_Data.py``) are responsible for layout, filters, and
rendering.

Naming convention
-----------------
    kpi_*       — top-of-page KPI scorecard helpers (return dict)
    demo_*      — customer demographics
    spend_*     — spending behavior and product mix
    channel_*   — purchase channels
    campaign_*  — marketing campaign performance
    cross_*     — cross-cuts that foreshadow the clustering page

Each chart function ends with ``return _apply_theme(fig)`` so the dashboard
keeps a consistent house style.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# --------------------------------------------------------------------------- #
# Theme + palette
# --------------------------------------------------------------------------- #

PLOTLY_TEMPLATE = "plotly_white"

# Stable color mappings — apply consistently across every chart that uses
# these dimensions so a reader's eye learns "blue = Married" once.
COLOR_BY_MARITAL = {
    "Married": "#1f77b4",
    "Together": "#aec7e8",
    "Single": "#ff7f0e",
    "Divorced": "#d62728",
    "Widow": "#9467bd",
}

COLOR_BY_EDUCATION = {
    "Graduation": "#1f77b4",
    "PhD": "#2ca02c",
    "Master": "#ff7f0e",
    "2n Cycle": "#d62728",
    "Basic": "#9467bd",
}

# RFM segment ordering — used everywhere segments are sorted or colored.
SEGMENT_ORDER = ["Inactive", "Occasional", "Moderate", "Loyal", "Premium"]

# Stable palette mapping segment → color (low tier → cool/gray, high tier → warm).
SEGMENT_PALETTE = {
    "Inactive": "#bdbdbd",
    "Occasional": "#aec7e8",
    "Moderate": "#1f77b4",
    "Loyal": "#ff7f0e",
    "Premium": "#d62728",
}

# Used for product-category charts (Wines / Fruits / Meat / Fish / Sweet / Gold).
PRODUCT_PALETTE = px.colors.qualitative.Plotly

# Channel column → display label.
CHANNEL_COLS = {
    "NumDealsPurchases": "Deals",
    "NumWebPurchases": "Web",
    "NumCatalogPurchases": "Catalog",
    "NumStorePurchases": "Store",
}

# Product columns (for revenue-share / dominance charts).
PRODUCT_COLS = [
    "MntWines",
    "MntFruits",
    "MntMeatProducts",
    "MntFishProducts",
    "MntSweetProducts",
    "MntGoldProds",
]

# All campaign columns including the last-campaign Response.
CAMPAIGN_COLS = [
    "AcceptedCmp1",
    "AcceptedCmp2",
    "AcceptedCmp3",
    "AcceptedCmp4",
    "AcceptedCmp5",
    "Response",
]


def _apply_theme(fig: go.Figure, *, height: int = 360) -> go.Figure:
    """Apply the project's house style to any Plotly figure."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
    )
    return fig


def _color_map_for(dimension: str) -> dict | None:
    """Return the project's stable color map for a dimension, or None."""
    if dimension == "Marital_Status":
        return COLOR_BY_MARITAL
    if dimension == "Education":
        return COLOR_BY_EDUCATION
    if dimension == "Segmentation":
        return SEGMENT_PALETTE
    return None


def _placeholder(name: str) -> go.Figure:
    """Return a styled empty figure for not-yet-implemented charts."""
    fig = go.Figure()
    fig.add_annotation(
        text=(
            f"<b>{name}</b><br>"
            "<span style='font-size:11px;color:#888'>not yet implemented</span>"
        ),
        showarrow=False,
        font=dict(size=14),
        xref="paper", yref="paper",
        x=0.5, y=0.5,
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _apply_theme(fig, height=300)


# --------------------------------------------------------------------------- #
# 1. KPI scorecard
# --------------------------------------------------------------------------- #

def kpi_scorecard(df: pd.DataFrame) -> dict:
    """
    Compute the headline KPIs for the top-of-page scorecard.

    Returns
    -------
    dict
        ``total_customers``, ``total_revenue``, ``avg_customer_value``,
        ``last_campaign_response`` (0–1), ``cumulative_acceptance`` (0–1),
        ``complaint_rate`` (0–1).
    """
    accepted_any = (df[CAMPAIGN_COLS].sum(axis=1) > 0).mean()
    return {
        "total_customers": int(len(df)),
        "total_revenue": float(df["Total_Spent"].sum()),
        "avg_customer_value": float(df["Total_Spent"].mean()),
        "last_campaign_response": float(df["Response"].mean()),
        "cumulative_acceptance": float(accepted_any),
        "complaint_rate": float(df["Complain"].mean()),
    }


# --------------------------------------------------------------------------- #
# 2. Customer demographics — "who are our customers?"
# --------------------------------------------------------------------------- #

def demo_age_hist(df: pd.DataFrame) -> go.Figure:
    """Age distribution histogram with mean and median annotation lines."""
    fig = px.histogram(df, x="Age", nbins=30)
    mean_age = df["Age"].mean()
    median_age = df["Age"].median()
    fig.add_vline(
        x=mean_age, line_dash="dash", line_color="#d62728",
        annotation_text=f"mean {mean_age:.0f}",
        annotation_position="top right",
    )
    fig.add_vline(
        x=median_age, line_dash="dot", line_color="#2ca02c",
        annotation_text=f"median {median_age:.0f}",
        annotation_position="top left",
    )
    fig.update_layout(
        title="Age distribution",
        xaxis_title="Age (years)",
        yaxis_title="Customers",
    )
    return _apply_theme(fig)


def demo_income_hist(df: pd.DataFrame) -> go.Figure:
    """Income distribution histogram (post-cleaning) with median line."""
    fig = px.histogram(df, x="Income", nbins=40)
    median_income = df["Income"].median()
    fig.add_vline(
        x=median_income, line_dash="dot", line_color="#2ca02c",
        annotation_text=f"median ${median_income:,.0f}",
        annotation_position="top right",
    )
    fig.update_layout(
        title="Income distribution",
        xaxis_title="Yearly household income (USD)",
        yaxis_title="Customers",
    )
    return _apply_theme(fig)


def demo_education_donut(df: pd.DataFrame) -> go.Figure:
    """Education breakdown as a donut chart."""
    counts = df["Education"].value_counts()
    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.5,
        marker=dict(colors=[COLOR_BY_EDUCATION.get(c, "#888") for c in counts.index]),
        textinfo="label+percent",
        sort=False,
    ))
    fig.update_layout(title="Education")
    return _apply_theme(fig)


def demo_marital_donut(df: pd.DataFrame) -> go.Figure:
    """Marital_Status breakdown as a donut chart (post-consolidation)."""
    counts = df["Marital_Status"].value_counts()
    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.5,
        marker=dict(colors=[COLOR_BY_MARITAL.get(c, "#888") for c in counts.index]),
        textinfo="label+percent",
        sort=False,
    ))
    fig.update_layout(title="Marital status")
    return _apply_theme(fig)


def demo_household_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap of customer counts by Kidhome × Teenhome."""
    ct = pd.crosstab(df["Kidhome"], df["Teenhome"])
    fig = go.Figure(go.Heatmap(
        z=ct.values,
        x=[f"{c} teen" for c in ct.columns],
        y=[f"{i} kid" for i in ct.index],
        colorscale="Blues",
        text=ct.values,
        texttemplate="%{text}",
        showscale=False,
    ))
    fig.update_layout(
        title="Household composition (Kidhome × Teenhome)",
        xaxis_title="Teenagers in home",
        yaxis_title="Children in home",
    )
    return _apply_theme(fig)


def demo_acquisition_curve(df: pd.DataFrame) -> go.Figure:
    """Cumulative customer acquisition over Dt_Customer."""
    series = (
        df.assign(_one=1)
          .set_index("Dt_Customer")
          .sort_index()["_one"]
          .cumsum()
    )
    monthly = series.resample("ME").last().ffill()
    fig = go.Figure(go.Scatter(
        x=monthly.index, y=monthly.values,
        mode="lines",
        fill="tozeroy",
        line=dict(color="#1f77b4"),
        name="Cumulative customers",
    ))
    fig.update_layout(
        title="Cumulative customer acquisition",
        xaxis_title="Enrollment date",
        yaxis_title="Cumulative customers",
    )
    return _apply_theme(fig)


# --------------------------------------------------------------------------- #
# 3. Spending behavior — "what do they buy?"
# --------------------------------------------------------------------------- #

def spend_product_share(df: pd.DataFrame) -> go.Figure:
    """Share of total revenue per product category — horizontal bar chart."""
    totals = df[PRODUCT_COLS].sum().sort_values(ascending=True)
    labels = (
        totals.index
        .str.replace("Mnt", "")
        .str.replace("Products", "")
        .str.replace("Prods", "")
    )
    pct = (totals / totals.sum()) * 100
    fig = go.Figure(go.Bar(
        x=totals.values,
        y=labels,
        orientation="h",
        text=[f"{p:.1f}% (${v:,.0f})" for p, v in zip(pct, totals.values)],
        textposition="outside",
        marker_color=PRODUCT_PALETTE[: len(labels)][::-1],
    ))
    fig.update_layout(
        title="Revenue share by product category",
        xaxis_title="Total revenue (USD)",
        yaxis_title="Category",
    )
    return _apply_theme(fig)


def spend_highest_breakdown(df: pd.DataFrame) -> go.Figure:
    """Customer count per dominant product category (Highest_Spent)."""
    counts = df["Highest_Spent"].value_counts().sort_values(ascending=True)
    pct = (counts / counts.sum()) * 100
    fig = go.Figure(go.Bar(
        x=counts.values,
        y=counts.index,
        orientation="h",
        text=[f"{c} ({p:.1f}%)" for c, p in zip(counts.values, pct)],
        textposition="outside",
        marker_color=PRODUCT_PALETTE[: len(counts)][::-1],
    ))
    fig.update_layout(
        title="Customer count by dominant product category",
        xaxis_title="Customers",
        yaxis_title="Top spending category",
    )
    return _apply_theme(fig)


def spend_total_distribution(df: pd.DataFrame) -> go.Figure:
    """Total_Spent distribution histogram with median line."""
    fig = px.histogram(df, x="Total_Spent", nbins=40)
    median = df["Total_Spent"].median()
    fig.add_vline(
        x=median, line_dash="dot", line_color="#2ca02c",
        annotation_text=f"median ${median:,.0f}",
        annotation_position="top right",
    )
    fig.update_layout(
        title="Total spend per customer (last 2 years)",
        xaxis_title="Total_Spent (USD)",
        yaxis_title="Customers",
    )
    return _apply_theme(fig)


def spend_vs_income_scatter(
    df: pd.DataFrame,
    color_by: str = "Highest_Spent",
) -> go.Figure:
    """
    Scatter of ``Total_Spent`` vs ``Income``, colored by ``color_by``.
    Visually previews the natural customer clusters.
    """
    fig = px.scatter(
        df,
        x="Income", y="Total_Spent",
        color=color_by,
        color_discrete_map=_color_map_for(color_by),
        opacity=0.55,
        hover_data=["Age", "Highest_Spent", "Total_Purchases"],
    )
    fig.update_traces(marker=dict(size=7))
    fig.update_layout(
        title=f"Total Spent vs Income — colored by {color_by}",
        xaxis_title="Income (USD)",
        yaxis_title="Total Spent (USD)",
    )
    return _apply_theme(fig)


# --------------------------------------------------------------------------- #
# 4. Channels — "how do they buy?"
# --------------------------------------------------------------------------- #

def channel_mix(df: pd.DataFrame) -> go.Figure:
    """Total purchases by channel — vertical bar chart."""
    totals = df[list(CHANNEL_COLS.keys())].sum()
    pct = (totals / totals.sum()) * 100
    fig = go.Figure(go.Bar(
        x=[CHANNEL_COLS[c] for c in totals.index],
        y=totals.values,
        text=[f"{int(t):,} ({p:.1f}%)" for t, p in zip(totals.values, pct)],
        textposition="outside",
        marker_color=PRODUCT_PALETTE[: len(totals)],
    ))
    fig.update_layout(
        title="Total purchases by channel",
        xaxis_title="Channel",
        yaxis_title="Total purchases",
    )
    return _apply_theme(fig)


def channel_web_visits_vs_purchases(df: pd.DataFrame) -> go.Figure:
    """Scatter of NumWebVisitsMonth vs NumWebPurchases."""
    fig = px.scatter(
        df,
        x="NumWebVisitsMonth", y="NumWebPurchases",
        color="Total_Spent",
        color_continuous_scale="Viridis",
        opacity=0.6,
        hover_data=["Total_Spent", "Income"],
    )
    fig.update_traces(marker=dict(size=7))
    fig.update_layout(
        title="Web visits vs web purchases",
        xaxis_title="Web visits per month",
        yaxis_title="Web purchases (last 2y)",
    )
    return _apply_theme(fig)


def channel_preference_by(
    df: pd.DataFrame,
    dimension: str = "Education",
) -> go.Figure:
    """Average channel usage grouped by a categorical dimension — grouped bar."""
    grouped = (
        df.groupby(dimension)[list(CHANNEL_COLS.keys())]
          .mean()
          .rename(columns=CHANNEL_COLS)
    )
    long = grouped.reset_index().melt(
        id_vars=dimension, var_name="Channel", value_name="Avg purchases",
    )
    fig = px.bar(
        long,
        x="Channel", y="Avg purchases",
        color=dimension,
        color_discrete_map=_color_map_for(dimension),
        barmode="group",
    )
    fig.update_layout(
        title=f"Average purchases per channel, by {dimension}",
        xaxis_title="Channel",
        yaxis_title="Avg purchases per customer",
    )
    return _apply_theme(fig)


# --------------------------------------------------------------------------- #
# 5. Campaign performance — "are our campaigns working?"
# --------------------------------------------------------------------------- #

def campaign_response_rates(df: pd.DataFrame) -> go.Figure:
    """Acceptance rate per campaign — bar chart over Cmp1..5 and Response."""
    rates = df[CAMPAIGN_COLS].mean() * 100
    labels = ["Cmp1", "Cmp2", "Cmp3", "Cmp4", "Cmp5", "Last (Response)"]
    fig = go.Figure(go.Bar(
        x=labels,
        y=rates.values,
        text=[f"{r:.1f}%" for r in rates.values],
        textposition="outside",
        marker_color=["#aec7e8"] * 5 + ["#1f77b4"],
    ))
    fig.update_layout(
        title="Acceptance rate per campaign",
        xaxis_title="Campaign",
        yaxis_title="Acceptance rate (%)",
    )
    return _apply_theme(fig)


def campaign_acceptance_distribution(df: pd.DataFrame) -> go.Figure:
    """Distribution of total campaigns accepted per customer (0–6)."""
    n_accepted = df[CAMPAIGN_COLS].sum(axis=1)
    counts = n_accepted.value_counts().sort_index()
    pct = (counts / counts.sum()) * 100
    fig = go.Figure(go.Bar(
        x=counts.index.astype(str),
        y=counts.values,
        text=[f"{int(c)} ({p:.1f}%)" for c, p in zip(counts.values, pct)],
        textposition="outside",
        marker_color="#1f77b4",
    ))
    fig.update_layout(
        title="Number of campaigns accepted per customer",
        xaxis_title="Campaigns accepted (out of 6)",
        yaxis_title="Customers",
    )
    return _apply_theme(fig)


def campaign_response_by(
    df: pd.DataFrame,
    dimension: str = "Education",
) -> go.Figure:
    """Last-campaign Response rate grouped by a categorical dimension."""
    rate = df.groupby(dimension)["Response"].mean().sort_values() * 100
    cmap = _color_map_for(dimension)
    colors = [cmap.get(idx, "#888") for idx in rate.index] if cmap else "#1f77b4"
    fig = go.Figure(go.Bar(
        x=rate.values,
        y=rate.index,
        orientation="h",
        text=[f"{r:.1f}%" for r in rate.values],
        textposition="outside",
        marker_color=colors,
    ))
    fig.update_layout(
        title=f"Last-campaign response rate by {dimension}",
        xaxis_title="Response rate (%)",
        yaxis_title=dimension,
    )
    return _apply_theme(fig)


def campaign_recency_vs_response(df: pd.DataFrame) -> go.Figure:
    """Boxplot of Recency split by Response (0/1)."""
    fig = px.box(
        df, x="Response", y="Recency",
        color="Response",
        color_discrete_map={0: "#aec7e8", 1: "#1f77b4"},
        points="outliers",
    )
    fig.update_layout(
        title="Recency by last-campaign response",
        xaxis_title="Responded? (0 = no, 1 = yes)",
        yaxis_title="Recency (days)",
        showlegend=False,
    )
    return _apply_theme(fig)


# --------------------------------------------------------------------------- #
# 6. Cross-cuts — segment foreshadowing
# --------------------------------------------------------------------------- #

def cross_spend_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap of mean Total_Spent by Marital_Status × Education."""
    pivot = df.pivot_table(
        values="Total_Spent",
        index="Marital_Status",
        columns="Education",
        aggfunc="mean",
    )
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale="Viridis",
        text=pivot.round(0).values,
        texttemplate="%{text:,.0f}",
        colorbar=dict(title="Mean spend"),
    ))
    fig.update_layout(
        title="Mean Total Spent by Marital × Education",
        xaxis_title="Education",
        yaxis_title="Marital status",
    )
    return _apply_theme(fig)


def cross_top_decile_profile(df: pd.DataFrame) -> go.Figure:
    """
    Radar chart contrasting the top 10% of spenders against the rest on
    normalized features.
    """
    threshold = df["Total_Spent"].quantile(0.9)
    is_top = df["Total_Spent"] >= threshold

    features = [
        "Income",
        "Age",
        "Total_Spent",
        "Total_Purchases",
        "NumWebVisitsMonth",
        "Recency",
    ]

    means_top = df.loc[is_top, features].mean()
    means_rest = df.loc[~is_top, features].mean()

    overall_min = df[features].min()
    overall_max = df[features].max()
    rng = (overall_max - overall_min).replace(0, 1)
    norm_top = (means_top - overall_min) / rng
    norm_rest = (means_rest - overall_min) / rng

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=list(norm_top.values) + [norm_top.values[0]],
        theta=features + [features[0]],
        fill="toself",
        name="Top 10% spenders",
        line=dict(color="#d62728"),
    ))
    fig.add_trace(go.Scatterpolar(
        r=list(norm_rest.values) + [norm_rest.values[0]],
        theta=features + [features[0]],
        fill="toself",
        name="Rest of customers",
        line=dict(color="#aec7e8"),
    ))
    fig.update_layout(
        title="Top 10% spenders vs the rest (normalized 0–1)",
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    )
    return _apply_theme(fig)


# --------------------------------------------------------------------------- #
# 7. Cluster Explorer — RFM segmentation views
# --------------------------------------------------------------------------- #

def cluster_3d_scatter(
    df: pd.DataFrame,
    color_by: str = "Segmentation",
) -> go.Figure:
    """
    3D scatter of customers in RFM space.

    Axes are fixed: ``Total_Purchases`` (Frequency) → x, ``Recency`` → y,
    ``Total_Spent`` (Monetary) → z. ``color_by`` accepts ``Segmentation`` or
    any per-component cluster column (``Cluster_Recency``,
    ``Cluster_Frequency``, ``Cluster_Monetary``).
    """
    plot_df = df.copy()

    # Cluster_* columns are integer labels — cast to str so px treats them
    # as discrete categories rather than a continuous color scale.
    if color_by.startswith("Cluster_"):
        plot_df[color_by] = plot_df[color_by].astype(str)

    color_map = _color_map_for(color_by)
    category_orders = (
        {color_by: SEGMENT_ORDER} if color_by == "Segmentation" else None
    )

    fig = px.scatter_3d(
        plot_df,
        x="Total_Purchases",
        y="Recency",
        z="Total_Spent",
        color=color_by,
        color_discrete_map=color_map,
        category_orders=category_orders,
        opacity=0.55,
        hover_data=["ID", "RMF_Score", "Age", "Income"],
    )
    fig.update_traces(marker=dict(size=4))
    fig.update_layout(
        title=f"RFM space — {len(plot_df):,} customers, colored by {color_by}",
        scene=dict(
            xaxis_title="Frequency (Total_Purchases)",
            yaxis_title="Recency (days)",
            zaxis_title="Monetary (Total_Spent)",
        ),
    )
    return _apply_theme(fig, height=600)


def cluster_pairwise_2d(
    df: pd.DataFrame,
    x_dim: str,
    y_dim: str,
    color_by: str = "Segmentation",
) -> go.Figure:
    """
    2D scatter for one pair of RFM dimensions, colored by ``color_by``.
    Page typically calls this three times (R-F, R-M, F-M) for pairwise views.
    """
    axis_labels = {
        "Total_Purchases": "Frequency",
        "Recency": "Recency (days)",
        "Total_Spent": "Monetary",
    }
    color_map = _color_map_for(color_by)
    category_orders = (
        {color_by: SEGMENT_ORDER} if color_by == "Segmentation" else None
    )

    fig = px.scatter(
        df,
        x=x_dim, y=y_dim,
        color=color_by,
        color_discrete_map=color_map,
        category_orders=category_orders,
        opacity=0.5,
    )
    fig.update_traces(marker=dict(size=6))
    fig.update_layout(
        title=f"{axis_labels.get(x_dim, x_dim)} × {axis_labels.get(y_dim, y_dim)}",
        xaxis_title=axis_labels.get(x_dim, x_dim),
        yaxis_title=axis_labels.get(y_dim, y_dim),
    )
    return _apply_theme(fig)


def segment_count_bar(df: pd.DataFrame) -> go.Figure:
    """Customer count per segment, ordered Inactive → Premium."""
    counts = df["Segmentation"].value_counts().reindex(SEGMENT_ORDER, fill_value=0)
    pct = counts / counts.sum() * 100
    fig = go.Figure(go.Bar(
        x=counts.index.tolist(),
        y=counts.values,
        text=[f"{int(c):,} ({p:.1f}%)" for c, p in zip(counts.values, pct)],
        textposition="outside",
        marker_color=[SEGMENT_PALETTE[s] for s in counts.index],
    ))
    fig.update_layout(
        title="Customers per segment",
        xaxis_title="Segment",
        yaxis_title="Customers",
    )
    return _apply_theme(fig)


def segment_scorecard(
    segment_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
) -> dict:
    """
    Per-segment KPIs returned as raw values alongside the baseline (overall
    population) values — the page formats and renders deltas via ``st.metric``.

    Returns
    -------
    dict
        ``customers``, ``baseline_customers``, plus paired
        ``avg_*`` / ``avg_*_baseline`` values for ``rfm``, ``total_spent``,
        ``total_purchases``, ``recency``, ``apv``, and ``response_rate``.
    """
    return {
        "customers": int(len(segment_df)),
        "baseline_customers": int(len(baseline_df)),
        "avg_rfm": float(segment_df["RMF_Score"].mean()),
        "avg_rfm_baseline": float(baseline_df["RMF_Score"].mean()),
        "avg_total_spent": float(segment_df["Total_Spent"].mean()),
        "avg_total_spent_baseline": float(baseline_df["Total_Spent"].mean()),
        "avg_total_purchases": float(segment_df["Total_Purchases"].mean()),
        "avg_total_purchases_baseline": float(baseline_df["Total_Purchases"].mean()),
        "avg_recency": float(segment_df["Recency"].mean()),
        "avg_recency_baseline": float(baseline_df["Recency"].mean()),
        "avg_apv": float(segment_df["APV"].mean()),
        "avg_apv_baseline": float(baseline_df["APV"].mean()),
        "response_rate": float(segment_df["Response"].mean()),
        "response_rate_baseline": float(baseline_df["Response"].mean()),
    }


def segments_comparison_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-segment summary DataFrame for tabular display. Returns the raw frame —
    the page applies ``.style`` formatting and conditional gradients.
    """
    grouped = df.groupby("Segmentation").agg(
        Customers=("ID", "count"),
        Avg_RFM_Score=("RMF_Score", "mean"),
        Avg_Recency=("Recency", "mean"),
        Avg_Frequency=("Total_Purchases", "mean"),
        Avg_Monetary=("Total_Spent", "mean"),
        Avg_APV=("APV", "mean"),
        Response_Rate=("Response", "mean"),
    ).reindex(SEGMENT_ORDER)

    grouped.insert(1, "Share", grouped["Customers"] / grouped["Customers"].sum())
    return grouped


def segments_parallel_coords(df: pd.DataFrame) -> go.Figure:
    """
    Parallel coordinates plot showing how segments differ across RFM features
    simultaneously. Each line is a customer, colored by segment tier.
    """
    segment_to_int = {s: i for i, s in enumerate(SEGMENT_ORDER)}
    plot_df = df[
        ["RMF_Score", "Recency", "Total_Purchases", "Total_Spent", "APV", "Segmentation"]
    ].copy()
    plot_df["Segment_Code"] = plot_df["Segmentation"].map(segment_to_int)

    # Build a 5-stop continuous color scale that lines up with SEGMENT_ORDER.
    n = len(SEGMENT_ORDER)
    colorscale = [
        [i / (n - 1), SEGMENT_PALETTE[s]]
        for i, s in enumerate(SEGMENT_ORDER)
    ]

    fig = px.parallel_coordinates(
        plot_df,
        dimensions=["Recency", "Total_Purchases", "Total_Spent", "APV", "RMF_Score"],
        color="Segment_Code",
        color_continuous_scale=colorscale,
    )
    fig.update_layout(
        title="Segment trajectories across RFM features",
        coloraxis=dict(
            colorbar=dict(
                title="Segment",
                tickvals=list(range(n)),
                ticktext=SEGMENT_ORDER,
            ),
        ),
    )
    return _apply_theme(fig, height=500)


# --------------------------------------------------------------------------- #
# 8. Customer Lookup — single-customer drill-down
# --------------------------------------------------------------------------- #

# Radar axes used for customer-vs-segment-vs-population comparison.
# Recency is *inverted* during normalization so all axes read "higher is better".
LOOKUP_RADAR_FEATURES = [
    "Recency",
    "Total_Purchases",
    "Total_Spent",
    "Income",
    "APV",
    "Campaigns_Accepted",
]
LOOKUP_RADAR_LABELS = {
    "Recency": "Recency<br>(inverted)",
    "Total_Purchases": "Frequency",
    "Total_Spent": "Monetary",
    "Income": "Income",
    "APV": "Avg purchase<br>value",
    "Campaigns_Accepted": "Campaigns<br>accepted",
}


def _customer_row(df: pd.DataFrame, customer_id: int) -> pd.Series:
    """Return the single customer row, or raise ``KeyError``."""
    matches = df.loc[df["ID"] == customer_id]
    if len(matches) == 0:
        raise KeyError(f"Customer ID {customer_id} not found")
    return matches.iloc[0]


def lookup_kpis(df: pd.DataFrame, customer_id: int) -> dict:
    """
    Profile + RFM scorecard values for a single customer, plus segment-median
    baselines so the page can render ``st.metric`` deltas.

    Returns
    -------
    dict
        Identity (``id``, ``age``, ``income``, ``education``, ``marital_status``,
        ``kidhome``, ``teenhome``, ``total_kids``, ``dt_customer``,
        ``tenure_years``), segment label (``segmentation``), RFM raw values
        and component scores, ``apv``, ``campaigns_accepted``, and
        ``*_seg_median`` / ``*_pop_median`` baselines for Recency, Frequency,
        Monetary, APV, RFM, and Income.
    """
    row = _customer_row(df, customer_id)
    seg = row["Segmentation"]
    seg_df = df[df["Segmentation"] == seg]
    campaigns_accepted = int(row[CAMPAIGN_COLS].sum())

    # Tenure relative to the latest enrollment date in the dataset.
    tenure_days = (df["Dt_Customer"].max() - row["Dt_Customer"]).days
    tenure_years = tenure_days / 365.25

    return {
        # Identity
        "id": int(row["ID"]),
        "age": int(row["Age"]),
        "income": float(row["Income"]),
        "education": str(row["Education"]),
        "marital_status": str(row["Marital_Status"]),
        "kidhome": int(row["Kidhome"]),
        "teenhome": int(row["Teenhome"]),
        "total_kids": int(row["Kidhome"] + row["Teenhome"]),
        "dt_customer": row["Dt_Customer"],
        "tenure_years": float(tenure_years),
        # Segment
        "segmentation": seg,
        # RFM raw + component scores
        "recency": int(row["Recency"]),
        "recency_score": int(row["Recency_Score"]),
        "frequency": int(row["Total_Purchases"]),
        "frequency_score": int(row["Frequency_Score"]),
        "monetary": float(row["Total_Spent"]),
        "monetary_score": int(row["Monetary_Score"]),
        "rfm_score": int(row["RMF_Score"]),
        "apv": float(row["APV"]),
        "campaigns_accepted": campaigns_accepted,
        # Segment baselines (median for robustness)
        "recency_seg_median": float(seg_df["Recency"].median()),
        "frequency_seg_median": float(seg_df["Total_Purchases"].median()),
        "monetary_seg_median": float(seg_df["Total_Spent"].median()),
        "apv_seg_median": float(seg_df["APV"].median()),
        "rfm_seg_median": float(seg_df["RMF_Score"].median()),
        "income_seg_median": float(seg_df["Income"].median()),
        # Population baselines
        "recency_pop_median": float(df["Recency"].median()),
        "frequency_pop_median": float(df["Total_Purchases"].median()),
        "monetary_pop_median": float(df["Total_Spent"].median()),
        "apv_pop_median": float(df["APV"].median()),
        "rfm_pop_median": float(df["RMF_Score"].median()),
        "income_pop_median": float(df["Income"].median()),
    }


def _normalize_for_radar(df: pd.DataFrame, values: pd.Series) -> pd.Series:
    """
    Min-max normalize each radar feature against the full population so that
    every axis reads 0–1 with "higher is better". ``Recency`` is inverted.
    """
    norm = pd.Series(index=values.index, dtype=float)
    for feat in values.index:
        col = df[feat]
        lo, hi = col.min(), col.max()
        rng = hi - lo if hi > lo else 1.0
        v = (values[feat] - lo) / rng
        if feat == "Recency":
            v = 1 - v  # lower recency → higher on the radar
        norm[feat] = v
    return norm


def lookup_radar(df: pd.DataFrame, customer_id: int) -> go.Figure:
    """
    Radar chart with three traces: the customer, their segment median, and the
    population median — all normalized 0–1 against the full population.
    Recency is inverted so every axis reads "higher is better".
    """
    row = _customer_row(df, customer_id)
    seg = row["Segmentation"]
    seg_df = df[df["Segmentation"] == seg]

    # Build per-customer Campaigns_Accepted on the fly.
    work = df.copy()
    work["Campaigns_Accepted"] = work[CAMPAIGN_COLS].sum(axis=1)
    seg_work = work[work["Segmentation"] == seg]
    customer_vals = work.loc[work["ID"] == customer_id, LOOKUP_RADAR_FEATURES].iloc[0]

    seg_median = seg_work[LOOKUP_RADAR_FEATURES].median()
    pop_median = work[LOOKUP_RADAR_FEATURES].median()

    norm_customer = _normalize_for_radar(work, customer_vals)
    norm_segment = _normalize_for_radar(work, seg_median)
    norm_population = _normalize_for_radar(work, pop_median)

    theta_labels = [LOOKUP_RADAR_LABELS[f] for f in LOOKUP_RADAR_FEATURES]
    theta_closed = theta_labels + [theta_labels[0]]

    seg_color = SEGMENT_PALETTE.get(seg, "#1f77b4")

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=list(norm_population.values) + [norm_population.values[0]],
        theta=theta_closed,
        fill="toself",
        name="Population median",
        line=dict(color="#bdbdbd"),
        opacity=0.55,
    ))
    fig.add_trace(go.Scatterpolar(
        r=list(norm_segment.values) + [norm_segment.values[0]],
        theta=theta_closed,
        fill="toself",
        name=f"{seg} median",
        line=dict(color=seg_color),
        opacity=0.55,
    ))
    fig.add_trace(go.Scatterpolar(
        r=list(norm_customer.values) + [norm_customer.values[0]],
        theta=theta_closed,
        fill="toself",
        name=f"Customer #{int(row['ID'])}",
        line=dict(color="#222", width=2),
        opacity=0.85,
    ))
    fig.update_layout(
        title=f"Customer #{int(row['ID'])} vs {seg} median vs population median",
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    )
    return _apply_theme(fig, height=460)


def _bar_with_segment_marker(
    customer_vals: pd.Series,
    segment_means: pd.Series,
    population_means: pd.Series,
    *,
    title: str,
    x_title: str,
    color: str,
    label_map: dict | None = None,
) -> go.Figure:
    """
    Horizontal bar of the customer's values, with diamond markers for the
    segment mean and X markers for the population mean on each row.
    """
    labels = (
        [label_map[c] for c in customer_vals.index]
        if label_map
        else list(customer_vals.index)
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=customer_vals.values,
        y=labels,
        orientation="h",
        name="Customer",
        marker_color=color,
        text=[f"{v:,.0f}" for v in customer_vals.values],
        textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        x=segment_means.values,
        y=labels,
        mode="markers",
        name="Segment mean",
        marker=dict(symbol="diamond", size=12, color="#222",
                    line=dict(color="white", width=1)),
    ))
    fig.add_trace(go.Scatter(
        x=population_means.values,
        y=labels,
        mode="markers",
        name="Population mean",
        marker=dict(symbol="x", size=11, color="#888"),
    ))
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title="",
        bargap=0.35,
    )
    return _apply_theme(fig, height=380)


def lookup_spend_vs_segment(df: pd.DataFrame, customer_id: int) -> go.Figure:
    """
    Customer's spend per product category, with segment-mean and population-mean
    overlay markers.
    """
    row = _customer_row(df, customer_id)
    seg = row["Segmentation"]
    seg_df = df[df["Segmentation"] == seg]

    label_map = {c: c.replace("Mnt", "").replace("Products", "").replace("Prods", "")
                 for c in PRODUCT_COLS}

    return _bar_with_segment_marker(
        customer_vals=row[PRODUCT_COLS],
        segment_means=seg_df[PRODUCT_COLS].mean(),
        population_means=df[PRODUCT_COLS].mean(),
        title=f"Spend per category — customer vs {seg} mean vs population",
        x_title="Spend (USD, last 2y)",
        color=SEGMENT_PALETTE.get(seg, "#1f77b4"),
        label_map=label_map,
    )


def lookup_channels_vs_segment(df: pd.DataFrame, customer_id: int) -> go.Figure:
    """
    Customer's purchases per channel, with segment-mean and population-mean
    overlay markers.
    """
    row = _customer_row(df, customer_id)
    seg = row["Segmentation"]
    seg_df = df[df["Segmentation"] == seg]
    cols = list(CHANNEL_COLS.keys())

    return _bar_with_segment_marker(
        customer_vals=row[cols],
        segment_means=seg_df[cols].mean(),
        population_means=df[cols].mean(),
        title=f"Purchases per channel — customer vs {seg} mean vs population",
        x_title="Purchases (last 2y)",
        color=SEGMENT_PALETTE.get(seg, "#1f77b4"),
        label_map=CHANNEL_COLS,
    )


def lookup_3d_highlight(
    df: pd.DataFrame,
    customer_id: int,
    color_by: str = "Segmentation",
) -> go.Figure:
    """
    Reuses ``cluster_3d_scatter`` and adds a single large diamond marker for
    the looked-up customer, so the user can see where that customer sits
    relative to their segment cloud.
    """
    fig = cluster_3d_scatter(df, color_by=color_by)
    row = _customer_row(df, customer_id)
    fig.add_trace(go.Scatter3d(
        x=[row["Total_Purchases"]],
        y=[row["Recency"]],
        z=[row["Total_Spent"]],
        mode="markers",
        name=f"Customer #{int(row['ID'])}",
        marker=dict(
            symbol="diamond",
            size=10,
            color="#000",
            line=dict(color="white", width=2),
        ),
        hovertemplate=(
            f"<b>Customer #{int(row['ID'])}</b><br>"
            f"Segment: {row['Segmentation']}<br>"
            f"Recency: {int(row['Recency'])} days<br>"
            f"Frequency: {int(row['Total_Purchases'])}<br>"
            f"Monetary: ${row['Total_Spent']:,.0f}<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=f"RFM space — customer #{int(row['ID'])} highlighted",
    )
    return fig


