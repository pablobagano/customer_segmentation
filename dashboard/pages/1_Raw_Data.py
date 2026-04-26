"""
Raw data explorer — browse the original marketing_campaign.csv with filters.
"""

import streamlit as st
import pandas as pd
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

st.info(
    "This page is under construction. It will load `data/marketing_campaign.csv` "
    "and provide column filters, search, and basic descriptive statistics."
)
