import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Advanced Portfolio Tracker", layout="wide")
st.title("📈 Advanced Portfolio Tracker")

# Directory to store portfolios
PORTFOLIO_DIR = "portfolios"
os.makedirs(PORTFOLIO_DIR, exist_ok=True)

# Helper: get FX rate to base currency
def get_fx_rate(from_currency, to_currency):
    if from_currency == to_currency:
        return 1.0
    fx_ticker = f"{from_currency}{to_currency}=X"
    try:
        fx_data = yf.Ticker(fx_ticker).history(period="1d")
        if fx_data.empty:
            return 1.0
        return fx_data['Close'][-1]
    except Exception:
        return 1.0

# Sidebar: Portfolio Manager
st.sidebar.header("📁 Portfolio Manager")

def get_portfolio_names():
    return [f.replace(".json", "") for f in os.listdir(PORTFOLIO_DIR) if f.endswith(".json")]

portfolio_names = get_portfolio_names()
selected_portfolio = st.sidebar.selectbox("Select Portfolio", [""] + portfolio_names)
new_portfolio_name = st.sidebar.text_input("Create New Portfolio")

if st.sidebar.button("Create Portfolio") and new_portfolio_name:
    path = os.path.join(PORTFOLIO_DIR, f"{new_portfolio_name}.json")
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({}, f)
        st.success(f"Portfolio '{new_portfolio_name}' created.")
    else:
        st.warning("Portfolio already exists.")

if selected_portfolio:
    rename_portfolio = st.sidebar.text_input("Rename Portfolio", value=selected_portfolio)
    if st.sidebar.button("Rename"):
        old_path = os.path.join(PORTFOLIO_DIR, f"{selected_portfolio}.json")
        new_path = os.path.join(PORTFOLIO_DIR, f"{rename_portfolio}.json")
        if not os.path.exists(new_path):
            os.rename(old_path, new_path)
            st.success(f"Portfolio renamed to '{rename_portfolio}'")
            st.experimental_rerun()
        else:
            st.warning("A portfolio with that name already exists.")

    if st.sidebar.button("Delete Portfolio"):
        os.remove(os.path.join(PORTFOLIO_DIR, f"{selected_portfolio}.json"))
        st.success(f"Portfolio '{selected_portfolio}' deleted.")
        st.experimental_rerun()

# Base currency selection
base_currency = st.sidebar.selectbox("Base Currency", ["GBP", "USD", "EUR", "CAD", "JPY"])

# Load selected portfolio data
portfolio_data = {}
if selected_portfolio:
    try:
        with open(os.path.join(PORTFOLIO_DIR, f"{selected_portfolio}.json")) as f:
            portfolio_data = json.load(f)
        st.info(f"Loaded portfolio: **{selected_portfolio}**")
    except Exception:
        st.warning("Failed to load portfolio.")

# Editable table for portfolio
st.subheader("📝 Edit Portfolio")
default_rows = portfolio_data.get("rows", [{"Ticker": "", "Shares": 0.0, "Buy Price": 0.0}])
edited_rows = st.data_editor(pd.DataFrame(default_rows), num_rows="dynamic", key="portfolio_editor")

# Save portfolio
if st.button("💾 Save Portfolio") and selected_portfolio:
    try:
        rows = edited_rows.to_dict(orient="records")
        with open(os.path.join(PORTFOLIO_DIR, f"{selected_portfolio}.json"), "w") as f:
            json.dump({"rows": rows}, f)
        st.success(f"Portfolio '{selected_portfolio}' saved.")
    except Exception as e:
        st.error(f"Error saving portfolio: {e}")

# Portfolio Analysis
if edited_rows is not None and not edited_rows.empty:
    portfolio_summary = []
    total_value = 0
    total_cost = 0
    sector_allocation = {}
    for row in edited_rows.itertuples(index=False):
        ticker = row.Ticker.strip().upper()
        shares = row.Shares
        buy_price = row._3  # Buy Price

        if not ticker or shares <= 0 or buy_price <= 0:
            continue

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            current_price = info.get("regularMarketPrice", 0)
            currency = info.get("currency", base_currency)
            fx_rate = get_fx_rate(currency, base_currency)
            current_price_base = current_price * fx_rate
            value = current_price_base * shares
            cost = buy_price * shares
            return_pct = (current_price_base - buy_price) / buy_price * 100 if buy_price > 0 else 0
            dividend_yield = info.get("dividendYield", 0.0) * 100 if info.get("dividendYield") else 0.0
            sector = info.get("sector", "Unknown")
            sector_allocation[sector] = sector_allocation.get(sector, 0) + value

            portfolio_summary.append({
                "Ticker": ticker,
                "Shares": shares,
                f"Buy Price ({base_currency})": buy_price,
                f"Current Price ({base_currency})": round(current_price_base, 2),
                f"Value ({base_currency})": round(value, 2),
                "Return (%)": round(return_pct, 2),
                "Dividend Yield (%)": round(dividend_yield, 2),
                "Sector": sector
            })

            total_value += value
            total_cost += cost

        except Exception as e:
            st.warning(f"Error fetching data for {ticker}: {e}")

    if portfolio_summary:
        df_summary = pd.DataFrame(portfolio_summary)
        st.subheader("📊 Portfolio Summary")
        st.dataframe(df_summary)

        total_return = (total_value - total_cost) / total_cost * 100 if total_cost > 0 else 0
        st.write(f"### 💰 Total Value ({base_currency}): {total_value:.2f}")
        st.write(f"### 🧾 Total Cost ({base_currency}): {total_cost:.2f}")
        st.write(f"### 📈 Total Return: {total_return:.2f}%")

        # Sector Allocation Pie Chart
        st.subheader("📌 Sector Allocation")
        sector_df = pd.DataFrame({
            'Sector': list(sector_allocation.keys()),
            'Value': list(sector_allocation.values())
        })
        fig = px.pie(sector_df, names='Sector', values='Value', title='Sector Allocation')
        st.plotly_chart(fig)

        # Benchmark Comparison
        st.subheader("📉 Benchmark Comparison (S&P 500 vs Portfolio)")
        benchmark = yf.Ticker("^GSPC")
        benchmark_hist = benchmark.history(period="1mo")["Close"]
        portfolio_hist = pd.Series(index=benchmark_hist.index, dtype=float)

        for row in edited_rows.itertuples(index=False):
            ticker = row.Ticker.strip().upper()
            shares = row.Shares
            if not ticker or shares <= 0:
                continue
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")["Close"]
            if hist.empty:
                continue
            info = stock.info
            currency = info.get("currency", base_currency)
            fx_rate = get_fx_rate(currency, base_currency)
            hist_base = hist * fx_rate * shares
            portfolio_hist = portfolio_hist.add(hist_base, fill_value=0)

        if not portfolio_hist.empty and not benchmark_hist.empty:
            compare_df = pd.DataFrame({
                "Portfolio": portfolio_hist,
                "S&P 500": benchmark_hist
            })
            st.line_chart(compare_df)

        # Export to CSV
        st.subheader("📤 Export Portfolio")
        csv = df_summary.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv, file_name="portfolio.csv", mime="text/csv")

# Watchlist
st.sidebar.subheader("👀 Watchlist")
watchlist_input = st.sidebar.text_input("Enter tickers (comma-separated)", value="AAPL, MSFT, TSLA")
watchlist = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
watchlist_data = []
for ticker in watchlist:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("regularMarketPrice", "N/A")
        currency = info.get("currency", base_currency)
        fx_rate = get_fx_rate(currency, base_currency)
        price_base = price * fx_rate if isinstance(price, (int, float)) else "N/A"
        watchlist_data.append({
            "Ticker": ticker,
            f"Price ({base_currency})": round(price_base, 2) if isinstance(price_base, (int, float)) else "N/A"
        })
    except Exception:
        watchlist_data.append({"Ticker": ticker, f"Price ({base_currency})": "Error"})

if watchlist_data:
    st.sidebar.dataframe(pd.DataFrame(watchlist_data))

# Sentiment Analysis (basic headlines)
st.subheader("📰 Sentiment Headlines")
for row in edited_rows.itertuples(index=False):
    ticker = row.Ticker.strip().upper()
    if not ticker:
        continue
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if news:
            st.write(f"**{ticker} News Headlines:**")
            for item in news[:3]:
                st.markdown(f"- [{item['title']}]({item['link']})")
    except Exception:
        st.write(f"No news available for {ticker}.")

