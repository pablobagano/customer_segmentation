"""
Raw data explorer — browse the original marketing_campaign.csv with filters.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_paths import MARKETING_CAMPAIGN
from helpers import dataset_info

st.set_page_config(page_title="Raw data", layout="wide")

st.title("Raw data explorer")
st.caption("Browse and filter the original Customer Personality Analysis dataset.")

df = pd.read_csv(MARKETING_CAMPAIGN, sep="\t")
n_rows = df.shape[0]
n_cols = df.shape[1]
columns = list(df.columns)
n_nulls = df.isna().sum().sum()

tab1, tab2, tab3 = st.tabs(['Overview', 'Info', 'EDA'])

with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric('Number of rows', n_rows)
    with col2:
        st.metric('Number of columns', n_cols)
    with col3:
        st.metric('Number of NaN', n_nulls)

    st.dataframe(df)

    st.header('Feature Description')

    data_dictionary = {
    "ID": "Customer's unique identifier",
    "Year_Birth": "Customer's birth year",
    "Education": "Customer's education level",
    "Marital_Status": "Customer's marital status",
    "Income": "Customer's yearly household income",
    "Kidhome": "Number of children in customer's household",
    "Teenhome": "Number of teenagers in customer's household",
    "Dt_Customer": "Date of customer's enrollment with the company",
    "Recency": "Number of days since customer's last purchase",
    "Complain": "1 if the customer complained in the last 2 years, 0 otherwise",
    "MntWines": "Amount spent on wine in last 2 years",
    "MntFruits": "Amount spent on fruits in last 2 years",
    "MntMeatProducts": "Amount spent on meat in last 2 years",
    "MntFishProducts": "Amount spent on fish in last 2 years",
    "MntSweetProducts": "Amount spent on sweets in last 2 years",
    "MntGoldProds": "Amount spent on gold in last 2 years",
    "NumDealsPurchases": "Number of purchases made with a discount",
    "AcceptedCmp1": "1 if customer accepted the offer in the 1st campaign, 0 otherwise",
    "AcceptedCmp2": "1 if customer accepted the offer in the 2nd campaign, 0 otherwise",
    "AcceptedCmp3": "1 if customer accepted the offer in the 3rd campaign, 0 otherwise",
    "AcceptedCmp4": "1 if customer accepted the offer in the 4th campaign, 0 otherwise",
    "AcceptedCmp5": "1 if customer accepted the offer in the 5th campaign, 0 otherwise",
    "Response": "1 if customer accepted the offer in the last campaign, 0 otherwise",
    "NumWebPurchases": "Number of purchases made through the company’s website",
    "NumCatalogPurchases": "Number of purchases made using a catalogue",
    "NumStorePurchases": "Number of purchases made directly in stores",
    "NumWebVisitsMonth": "Number of visits to company’s website in the last month"
    }

    description_df = pd.Series(data_dictionary).to_frame(name='Features')
    st.dataframe(description_df)

with tab2:

    info_df = dataset_info(df)

    st.dataframe(info_df)

    age = (2026 - df['Year_Birth']).dropna()
    income = df['Income'].dropna()

    st.header('Outliers - Age & Income')

    fig = make_subplots(rows=1, cols=2, subplot_titles=('Age', 'Income'))
    fig.add_trace(go.Box(y=age, name='Age', marker_color='steelblue'), row=1, col=1)
    fig.add_trace(go.Box(y=income, name='Income', marker_color='coral'), row=1, col=2)
    fig.update_layout(showlegend=False, height=450)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
    """
    ### What changed vs. the raw dataset

    - **Dropped constants** — `Z_CostContact` and `Z_Revenue` were removed; both had zero variance and no information gain.
    - **`Income` cleanup** — the column had 24 missing values *and* one extreme high outlier that was distorting the `Age × Income` regression. The outlier row was dropped first, then nulls were imputed with the **median** (robust to residual skew).
    - **`Dt_Customer` → `datetime`** — parsed with `pd.to_datetime(..., dayfirst=True)` so it can be filtered, sorted, and used for time-based features.
        - *Note:* `Year_Birth` was **kept as `int`** and used to derive a new `Age` column (`current_year - Year_Birth`).
    - **Age outliers (`>120`)** — three biologically impossible records surfaced. Two (rows `192`, `239`) were dropped: impossible age combined with near-zero spending pointed to ghost records. The third belonged to an active customer (`ID 1150`) and was kept, with the age replaced by the population mean to preserve their behavioral signal.
    - **`Marital_Status` consolidated** — the noise categories `Alone`, `Absurd`, and `YOLO` (each <0.1% of rows) were merged into `Single`.
    - **Engineered features**
        - `Total_Spent` — sum across all `Mnt*` product columns.
        - `Total_Purchases` — sum across all `Num*Purchases` channels.
        - `Highest_Spent` — categorical: the dominant product category per customer.
        - `Age` — derived from `Year_Birth`.
    - **Outliers in `Total_Spent` / `Total_Purchases`** — flagged by the IQR rule but **left untreated**. Their deviation from the upper whisker is negligible, so removing them would hurt data integrity without any modeling benefit.
    """
    )

with tab3:
    st.subheader("Discovery: issues hiding in the raw data")
    st.caption(
        "Every visual on this tab maps to a fix applied on the Cleaned Data page — "
        "these are the findings that motivated the cleaning pipeline."
    )

    # 1. Statistical summary
    st.markdown("#### Statistical summary")
    st.caption(
        "Three red flags hide in plain sight: `Year_Birth` minimum predates 1900, "
        "`Income` maximum runs into the hundreds of thousands, and `Z_CostContact` "
        "/ `Z_Revenue` show zero standard deviation."
    )
    st.dataframe(df.describe().T, use_container_width=True)

    st.divider()

    # 2. Missing values
    st.markdown("#### Missing values")
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0].sort_values()
    if len(nulls) == 0:
        st.success("No missing values detected.")
    else:
        fig_nulls = px.bar(
            x=nulls.values,
            y=nulls.index,
            orientation="h",
            labels={"x": "Null count", "y": "Column"},
            text=nulls.values,
        )
        fig_nulls.update_layout(
            height=200 + 40 * len(nulls),
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig_nulls, use_container_width=True)
        st.caption(
            f"Only **{', '.join(nulls.index)}** has nulls "
            f"({int(nulls.sum())} of {n_rows} rows). "
            "Median imputation is applied on the Cleaned Data page."
        )

    st.divider()

    # 3. Constant columns
    st.markdown("#### Zero-variance columns")
    constants = [c for c in df.columns if df[c].nunique(dropna=False) == 1]
    if constants:
        st.warning(
            f"Found {len(constants)} constant column(s): "
            f"**{', '.join(constants)}** — dropped during cleaning since they carry no information."
        )
        st.dataframe(
            pd.DataFrame({
                "Column": constants,
                "Unique value": [df[c].iloc[0] for c in constants],
            }),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.success("No constant columns detected.")

    st.divider()

    # 4. Income — boxplot + histogram side-by-side
    st.markdown("#### `Income` — outlier and skew")
    col_a, col_b = st.columns(2)
    with col_a:
        fig_income_box = px.box(
            df, x="Income",
            points="outliers",
            title="Boxplot — outlier dominates the scale",
        )
        fig_income_box.update_layout(
            height=320, margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_income_box, use_container_width=True)
    with col_b:
        fig_income_hist = px.histogram(
            df, x="Income", nbins=50,
            title="Histogram — bulk crushed into a thin sliver",
        )
        fig_income_hist.update_layout(
            height=320, margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_income_hist, use_container_width=True)
    st.caption(
        f"Maximum income: **{df['Income'].max():,.0f}** — removed during cleaning. "
        "Once the outlier is gone, the remaining 24 nulls are imputed with the median."
    )

    st.divider()

    # 5. Age outliers (derived inline from Year_Birth)
    st.markdown("#### Age distribution (derived from `Year_Birth`)")
    current_year = pd.Timestamp.now().year
    age_raw = current_year - df["Year_Birth"]
    fig_age = px.box(
        x=age_raw,
        labels={"x": "Age (years)"},
        points="outliers",
    )
    fig_age.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_age, use_container_width=True)
    n_extreme = int((age_raw >= 120).sum())
    st.caption(
        f"**{n_extreme} customers** appear to be 120+ years old. "
        "Two are dropped, one is mean-imputed during cleaning."
    )

    st.divider()

    # 6. Categorical breakdowns — Marital_Status & Education
    st.markdown("#### Categorical breakdowns")
    col_c, col_d = st.columns(2)
    with col_c:
        marital_counts = df["Marital_Status"].value_counts().reset_index()
        marital_counts.columns = ["Marital_Status", "Count"]
        fig_marital = px.bar(
            marital_counts,
            x="Count", y="Marital_Status",
            orientation="h",
            text="Count",
            title="Marital_Status",
        )
        fig_marital.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=40, b=10),
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_marital, use_container_width=True)
        noise = ["Alone", "Absurd", "YOLO"]
        present = [c for c in noise if c in df["Marital_Status"].unique()]
        if present:
            st.caption(
                f"Noise categories present: **{', '.join(present)}** — "
                "merged into `Single` during cleaning."
            )
    with col_d:
        edu_counts = df["Education"].value_counts().reset_index()
        edu_counts.columns = ["Education", "Count"]
        fig_edu = px.bar(
            edu_counts,
            x="Count", y="Education",
            orientation="h",
            text="Count",
            title="Education",
        )
        fig_edu.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=40, b=10),
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_edu, use_container_width=True)


