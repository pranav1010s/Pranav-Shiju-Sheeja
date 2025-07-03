import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Supplier Performance Dashboard", layout="wide")
st.title("📦 Supplier Performance Dashboard + AI Risk Alerts")

uploaded_file = st.file_uploader("Upload Supplier Performance CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Calculate performance metrics
    df["On-Time %"] = (df["On-Time Deliveries"] / df["Total Deliveries"]) * 100

    # Display table
    st.subheader("📋 Supplier Data")
    st.dataframe(df)

    # Visuals
    st.subheader("📊 On-Time Delivery Rate")
    fig1 = px.bar(df, x="Supplier", y="On-Time %", color="On-Time %", color_continuous_scale="Blues")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("💰 Average Cost per Supplier")
    fig2 = px.bar(df, x="Supplier", y="Avg Cost", color="Avg Cost", color_continuous_scale="Greens")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("⚠️ Defect Rate")
    fig3 = px.bar(df, x="Supplier", y="Defect Rate (%)", color="Defect Rate (%)", color_continuous_scale="Reds")
    st.plotly_chart(fig3, use_container_width=True)

    # AI-style risk alerts
    st.subheader("🧠 AI Risk Alerts")
    for _, row in df.iterrows():
        alerts = []
        if row["On-Time %"] < 85:
            alerts.append("Low on-time delivery rate")
        if row["Defect Rate (%)"] > 3:
            alerts.append("High defect rate")
        if row["Avg Cost"] > df["Avg Cost"].mean() * 1.2:
            alerts.append("Above-average cost")

        if alerts:
            st.warning(f"**{row['Supplier']}**: " + ", ".join(alerts))
        else:
            st.success(f"**{row['Supplier']}**: No major risks detected ✅")
