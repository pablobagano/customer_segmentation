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
