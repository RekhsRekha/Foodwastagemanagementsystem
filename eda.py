import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# ==========================================
# STREAMLIT PAGE INITIALIZATION
# ==========================================
st.set_page_config(page_title="Local Food Wastage Management System", layout="wide")
sns.set_theme(style="whitegrid")

# Modifying global font sizes to make text highly readable across all plots
plt.rcParams.update({
    'axes.labelsize': 11,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10
})

# ==========================================
# 1. DATA LOADING & NULL VALUE ANALYSIS
# ==========================================
@st.cache_data
def load_and_clean_data():
    df_p = pd.read_csv('providers_data.csv')
    df_r = pd.read_csv('receivers_data.csv')
    df_l = pd.read_csv('food_listings_data.csv')  
    df_c = pd.read_csv('claims_data.csv')
    
    df_p.columns = df_p.columns.str.strip()
    df_r.columns = df_r.columns.str.strip()
    df_l.columns = df_l.columns.str.strip()
    df_c.columns = df_c.columns.str.strip()
    
    if 'Type' in df_p.columns:
        df_p.rename(columns={'Type': 'Provider_Type'}, inplace=True)
    if 'Name' in df_p.columns:
        df_p.rename(columns={'Name': 'Provider_Name'}, inplace=True)
    if 'Name' in df_r.columns:
        df_r.rename(columns={'Name': 'Receiver_Name'}, inplace=True)
    if 'Location' in df_l.columns:
        df_l.rename(columns={'Location': 'City'}, inplace=True)
    if 'Listing_ID' in df_c.columns and 'Food_ID' not in df_c.columns:
        df_c.rename(columns={'Listing_ID': 'Food_ID'}, inplace=True)
    if 'Status' in df_c.columns:
        df_c.rename(columns={'Status': 'Claim_Status'}, inplace=True)
    
    if 'Contact' in df_p.columns:
        df_p['Contact'] = df_p['Contact'].fillna('Not Provided')
    if 'Address' in df_p.columns:
        df_p['Address'] = df_p['Address'].fillna('Unknown Address')
    if 'Contact' in df_r.columns:
        df_r['Contact'] = df_r['Contact'].fillna('Private/Hidden')
    if 'Expiry_Date' in df_l.columns:
        df_l['Expiry_Date'] = df_l['Expiry_Date'].fillna('Not Stated')
    if 'Quantity' in df_l.columns:
        df_l['Quantity'] = df_l.groupby('Food_Type')['Quantity'].transform(lambda x: x.fillna(x.median()))
    
    df_c['Claim_Status'] = df_c['Claim_Status'].fillna('Incomplete/Pending')
    if 'Timestamp' in df_c.columns:
        df_c['Timestamp'] = df_c['Timestamp'].fillna('Pending Process')
    
    df_listings_prov = df_l.merge(df_p, on='Provider_ID', how='left', suffixes=('', '_prov'))
    df_full_claims = df_c.merge(df_l, on='Food_ID', how='left') \
                         .merge(df_p, on='Provider_ID', how='left', suffixes=('', '_prov')) \
                         .merge(df_r, on='Receiver_ID', how='left', suffixes=('', '_recv'))
                         
    return df_p, df_r, df_l, df_c, df_listings_prov, df_full_claims

df_providers, df_receivers, df_listings, df_claims, df_listings_prov, df_full_claims = load_and_clean_data()

# ==========================================
# 2. STREAMLIT INTERACTIVE FILTERS
# ==========================================
st.sidebar.title("Dashboard Filters")

cities = df_listings['City'].dropna().unique() if 'City' in df_listings.columns else []
provider_types = df_providers['Provider_Type'].dropna().unique() if 'Provider_Type' in df_providers.columns else []
meal_types = df_listings['Meal_Type'].dropna().unique() if 'Meal_Type' in df_listings.columns else []
food_types = df_listings['Food_Type'].dropna().unique() if 'Food_Type' in df_listings.columns else []

selected_cities = st.sidebar.multiselect("Select City", options=cities, default=cities)
selected_prov_types = st.sidebar.multiselect("Select Provider Type", options=provider_types, default=provider_types)
selected_meals = st.sidebar.multiselect("Select Meal Type", options=meal_types, default=meal_types)
selected_foods = st.sidebar.multiselect("Select Food Type", options=food_types, default=food_types)

filtered_listings = df_listings[
    df_listings['City'].isin(selected_cities) & 
    df_listings['Meal_Type'].isin(selected_meals) & 
    df_listings['Food_Type'].isin(selected_foods)
]

filtered_listings_prov = df_listings_prov[
    df_listings_prov['City'].isin(selected_cities) & 
    df_listings_prov['Provider_Type'].isin(selected_prov_types) &
    df_listings_prov['Meal_Type'].isin(selected_meals) & 
    df_listings_prov['Food_Type'].isin(selected_foods)
]

filtered_claims = df_full_claims[
    df_full_claims['City'].isin(selected_cities) &
    df_full_claims['Meal_Type'].isin(selected_meals) & 
    df_full_claims['Food_Type'].isin(selected_foods)
]

st.title("🛡️ Local Food Wastage Management System Analytics")
st.markdown("---")

# ==========================================
# 3. UNIVARIATE ANALYSIS
# ==========================================
st.header("1. Univariate Analysis (Categorical Distributions)")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Provider Type Distribution")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.countplot(data=df_providers, x='Provider_Type', order=df_providers['Provider_Type'].value_counts().index, palette='viridis', ax=ax)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

    st.subheader("Food Type Distribution")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.countplot(data=filtered_listings, x='Food_Type', order=filtered_listings['Food_Type'].value_counts().index, palette='crest', ax=ax)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

with col2:
    st.subheader("Receiver Type Distribution")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if 'Receiver_Type' in df_receivers.columns:
        sns.countplot(data=df_receivers, x='Receiver_Type', order=df_receivers['Receiver_Type'].value_counts().index, palette='rocket', ax=ax)
        plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

    st.subheader("Meal Type Distribution")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.countplot(data=filtered_listings, x='Meal_Type', order=filtered_listings['Meal_Type'].value_counts().index, palette='magma', ax=ax)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

st.markdown("---")

# ==========================================
# 4. BIVARIATE ANALYSIS
# ==========================================
st.header("2. Bivariate Analysis (Categories vs Volume/Listings)")
col3, col4 = st.columns(2)

with col3:
    st.subheader("Top 10 Cities vs Food Listings Count")
    fig, ax = plt.subplots(figsize=(8, 5))
    top_10_cities = filtered_listings['City'].value_counts().nlargest(10).index
    df_top_cities = filtered_listings[filtered_listings['City'].isin(top_10_cities)]
    
    sns.countplot(data=df_top_cities, x='City', order=top_10_cities, palette='cubehelix', ax=ax)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

    st.subheader("Food Type vs Quantity Volume (Sorted)")
    fig, ax = plt.subplots(figsize=(8, 5))
    food_qty_order = filtered_listings.groupby('Food_Type')['Quantity'].sum().sort_values(ascending=False).index
    sns.barplot(data=filtered_listings, x='Food_Type', y='Quantity', order=food_qty_order, estimator=sum, errorbar=None, palette='Greens_r', ax=ax)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

with col4:
    st.subheader("Provider Type vs Quantity Volume (Sorted)")
    fig, ax = plt.subplots(figsize=(8, 5))
    prov_qty_order = filtered_listings_prov.groupby('Provider_Type')['Quantity'].sum().sort_values(ascending=False).index
    sns.barplot(data=filtered_listings_prov, x='Provider_Type', y='Quantity', order=prov_qty_order, estimator=sum, errorbar=None, palette='Blues_r', ax=ax)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

    st.subheader("Meal Type vs Quantity Volume (Sorted)")
    fig, ax = plt.subplots(figsize=(8, 5))
    meal_qty_order = filtered_listings.groupby('Meal_Type')['Quantity'].sum().sort_values(ascending=False).index
    sns.barplot(data=filtered_listings, x='Meal_Type', y='Quantity', order=meal_qty_order, estimator=sum, errorbar=None, palette='Oranges_r', ax=ax)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

st.markdown("---")

# ==========================================
# 5. MULTIVARIATE ANALYSIS
# ==========================================
st.header("3. Multivariate Analysis")

st.subheader("Top 10 Cities + Provider Type + Quantity Breakdown")
fig, ax = plt.subplots(figsize=(14, 6))
df_mult_top_cities = filtered_listings_prov[filtered_listings_prov['City'].isin(top_10_cities)]

sns.barplot(data=df_mult_top_cities, x='City', y='Quantity', hue='Provider_Type', order=top_10_cities, estimator=sum, errorbar=None, palette='Set2', ax=ax)
plt.xticks(rotation=45, ha='right')
plt.legend(bbox_to_anchor=(1.01, 1), loc='upper left')
plt.tight_layout()
st.pyplot(fig)

col5, col6 = st.columns(2)
with col5:
    st.subheader("Heatmap: Food Type + Meal Type + Quantity")
    if not filtered_listings.empty:
        pivot_table = filtered_listings.pivot_table(values='Quantity', index='Food_Type', columns='Meal_Type', aggfunc='sum', fill_value=0)
        pivot_table = pivot_table.loc[pivot_table.sum(axis=1).sort_values(ascending=False).index]
        fig, ax = plt.subplots(figsize=(8, 5.5))
        sns.heatmap(pivot_table, annot=True, fmt=".0f", cmap="YlGnBu", ax=ax, cbar_kws={'label': 'Total Quantity'})
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("No data available for heatmap based on selected filters.")

with col6:
    st.subheader("Top 10 Provider Claim Breakdown")
    if not filtered_claims.empty and 'Provider_Name' in filtered_claims.columns:
        fig, ax = plt.subplots(figsize=(9, 5.5))
        
        top_10_providers = filtered_claims.groupby('Provider_Name')['Quantity'].sum().nlargest(10).index
        df_top_claims = filtered_claims[filtered_claims['Provider_Name'].isin(top_10_providers)]
        
        sns.barplot(data=df_top_claims, x='Provider_Name', y='Quantity', hue='Claim_Status', order=top_10_providers, estimator=sum, errorbar=None, ax=ax)
        plt.xticks(rotation=45, ha='right')
        plt.legend(bbox_to_anchor=(1.01, 1), loc='upper left')
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("No active provider claim breakdown matching filters.")

st.markdown("---")

# ==========================================
# 6. CLAIM ANALYSIS (FIXED FOR PERFECT CLARITY)
# ==========================================
st.header("4. System Claim & Delivery Efficiency Analysis")
col7, col8, col9 = st.columns(3)

with col7:
    st.subheader("Claim Status Distribution")
    if not df_claims.empty:
        fig, ax = plt.subplots(figsize=(5, 5))
        status_counts = df_claims['Claim_Status'].value_counts()
        ax.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', colors=['#4CAF50', '#FFC107', '#F44336'], startangle=140)
        plt.tight_layout()
        st.pyplot(fig)

with col8:
    st.subheader("Top 10 Providers (by Donated Vol)")
    if not df_full_claims.empty and 'Provider_Name' in df_full_claims.columns:
        fig, ax = plt.subplots(figsize=(6, 5))
        top_prov = df_full_claims.groupby('Provider_Name')['Quantity'].sum().nlargest(10).reset_index()
        # FIXED: Swapped x and y variables to make this a highly clean horizontal chart
        sns.barplot(data=top_prov, y='Provider_Name', x='Quantity', order=top_prov['Provider_Name'], palette='YlOrRd_r', ax=ax)
        plt.tight_layout()
        st.pyplot(fig)

with col9:
    st.subheader("Top 10 Receivers (by Claimed Vol)")
    if not df_full_claims.empty and 'Receiver_Name' in df_full_claims.columns:
        fig, ax = plt.subplots(figsize=(6, 5))
        top_recv = df_full_claims.groupby('Receiver_Name')['Quantity'].sum().nlargest(10).reset_index()
        # FIXED: Swapped x and y variables to make this a highly clean horizontal chart
        sns.barplot(data=top_recv, y='Receiver_Name', x='Quantity', order=top_recv['Receiver_Name'], palette='GnBu_r', ax=ax)
        plt.tight_layout()
        st.pyplot(fig)