import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json
import datetime
import plotly.express as px

# Constants
PORTFOLIO_DIR = "portfolios"
WATCHLIST_FILE = "watchlist.json"
BENCHMARK_TICKER = "^GSPC"  # S&P 500

# Ensure directories exist
os.makedirs(PORTFOLIO_DIR, exist_ok=True)

# Helper functions
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

def load_portfolio(name):
    try:
        with open(os.path.join(PORTFOLIO_DIR, f"{name}.json")) as f:
            return json.load(f)
    except:
        return {}

def save_portfolio(name, data):
    with open(os.path.join(PORTFOLIO_DIR, f"{name}.json"), "w") as f:
        json.dump(data, f)

def delete_portfolio(name):
    os.remove(os.path.join(PORTFOLIO_DIR, f"{name}.json"))

def rename_portfolio(old_name, new_name):
    os.rename(os.path.join(PORTFOLIO_DIR, f"{old_name}.json"),
              os.path.join(PORTFOLIO_DIR, f"{new_name}.json"))

def get_portfolio_names():
    return [f.replace(".json", "") for f in os.listdir(PORTFOLIO_DIR) if f.endswith(".json")]

def get_sector_allocation(tickers, shares):
    sectors = {}
    for ticker, qty in zip(tickers, shares):
        try:
            info = yf.Ticker(ticker).info
            sector = info.get("sector", "Unknown")
            price = info.get("regularMarketPrice", 0)
            value = price * qty
            sectors[sector] = sectors.get(sector, 0) + value
        except:
            continue
    return sectors

def get_dividend_yield(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get("dividendYield", 0.0)
    except:
        return 0.0

def get_sentiment(ticker):
    try:
        news = yf.Ticker(ticker).news
        if not news:
            return "Neutral"
        headlines = [item['title'] for item in news[:5]]
        positive = sum("up" in h.lower() or "gain" in h.lower() for h in headlines)
        negative = sum("down" in h.lower() or "loss" in h.lower() for h in headlines)
        if positive > negative:
            return "Positive"
        elif negative > positive:
            return "Negative"
        else:
            return "Neutral"
    except:
        return "Neutral"

# Streamlit UI
st.set_page_config(page_title="Portfolio Tracker", layout="wide")
st.title("📈 Personal Share Portfolio Tracker")

# Sidebar: Portfolio Manager
st.sidebar.header("📁 Portfolio Manager")
portfolio_names = get_portfolio_names()
selected_portfolio = st.sidebar.selectbox("Select Portfolio", [""] + portfolio_names)
new_portfolio_name = st.sidebar.text_input("Create New Portfolio")

if st.sidebar.button("Create Portfolio") and new_portfolio_name:
    if new_portfolio_name not in portfolio_names:
        save_portfolio(new_portfolio_name, {})
        st.success(f"Portfolio '{new_portfolio_name}' created.")
    else:
        st.warning("Portfolio already exists.")

if selected_portfolio:
    if st.sidebar.button("Delete Portfolio"):
        delete_portfolio(selected_portfolio)
        st.success(f"Portfolio '{selected_portfolio}' deleted.")
        st.experimental_rerun()

    rename_to = st.sidebar.text_input("Rename Portfolio")
    if st.sidebar.button("Rename") and rename_to:
        rename_portfolio(selected_portfolio, rename_to)
        st.success(f"Portfolio renamed to '{rename_to}'")
        st.experimental_rerun()

# Base currency selection
base_currency = st.sidebar.selectbox("Base Currency", ["GBP", "USD", "EUR", "CAD", "JPY"])

# Load portfolio
portfolio_data = load_portfolio(selected_portfolio) if selected_portfolio else {}
df_editor = pd.DataFrame(portfolio_data) if portfolio_data else pd.DataFrame(columns=["Ticker", "Shares", "Buy Price"])

st.subheader("📋 Edit Portfolio")
edited_df = st.data_editor(df_editor, num_rows="dynamic", key="portfolio_editor")

if selected_portfolio and st.button("💾 Save Portfolio"):
    save_portfolio(selected_portfolio, edited_df.to_dict(orient="list"))
    st.success("Portfolio saved.")

# Export to CSV
if not edited_df.empty:
    csv = edited_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export Portfolio to CSV", csv, "portfolio.csv", "text/csv")

# Portfolio Analysis
if not edited_df.empty:
    st.subheader("📊 Portfolio Analysis")
    tickers = edited_df["Ticker"].tolist()
    shares = edited_df["Shares"].tolist()
    buy_prices = edited_df["Buy Price"].tolist()

    analysis = []
    total_value = 0
    total_cost = 0

    for ticker, qty, buy_price in zip(tickers, shares, buy_prices):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get("regularMarketPrice", 0)
            currency = info.get("currency", base_currency)
            fx_rate = get_fx_rate(currency, base_currency)
            price_base = price * fx_rate
            value = price_base * qty
            cost = buy_price * qty
            ret = (price_base - buy_price) / buy_price * 100 if buy_price else 0
            dividend = get_dividend_yield(ticker)
            sentiment = get_sentiment(ticker)

            analysis.append({
                "Ticker": ticker,
                "Shares": qty,
                "Buy Price": buy_price,
                "Current Price": round(price_base, 2),
                "Value": round(value, 2),
                "Cost": round(cost, 2),
                "Return (%)": round(ret, 2),
                "Dividend Yield": f"{dividend*100:.2f}%",
                "Sentiment": sentiment
            })

            total_value += value
            total_cost += cost
        except:
            continue

    df_analysis = pd.DataFrame(analysis)
    st.dataframe(df_analysis)

    total_return = (total_value - total_cost) / total_cost * 100 if total_cost else 0
    st.metric("Total Portfolio Value", f"{base_currency} {total_value:,.2f}")
    st.metric("Total Cost Basis", f"{base_currency} {total_cost:,.2f}")
    st.metric("Overall Return", f"{total_return:.2f}%")

    # Sector Allocation
    st.subheader("📌 Sector Allocation")
    sectors = get_sector_allocation(tickers, shares)
    if sectors:
        sector_df = pd.DataFrame(list(sectors.items()), columns=["Sector", "Value"])
        fig = px.pie(sector_df, names="Sector", values="Value", title="Sector Allocation")
        st.plotly_chart(fig)

    # Benchmark Comparison
    st.subheader("📈 Benchmark Comparison (S&P 500)")
    try:
        combined_df = pd.DataFrame()
        for ticker, qty in zip(tickers, shares):
            hist = yf.Ticker(ticker).history(period="1mo")[["Close"]]
            if hist.empty:
                continue
            hist = hist.rename(columns={"Close": ticker})
            hist[ticker] = hist[ticker] * qty
            combined_df = combined_df.join(hist, how="outer") if not combined_df.empty else hist

        if not combined_df.empty:
            combined_df.fillna(method="ffill", inplace=True)
            combined_df["Portfolio"] = combined_df.sum(axis=1)

            benchmark = yf.Ticker(BENCHMARK_TICKER).history(period="1mo")[["Close"]]
            benchmark = benchmark.rename(columns={"Close": "S&P 500"})
            combined_df = combined_df.join(benchmark, how="outer")
            combined_df.fillna(method="ffill", inplace=True)

            st.line_chart(combined_df[["Portfolio", "S&P 500"]])
    except:
        st.warning("Benchmark data unavailable.")

# Watchlist
st.sidebar.subheader("👀 Watchlist")
watchlist = []
if os.path.exists(WATCHLIST_FILE):
    with open(WATCHLIST_FILE) as f:
        watchlist = json.load(f)

new_watch = st.sidebar.text_input("Add to Watchlist")
if st.sidebar.button("Add"):
    if new_watch and new_watch not in watchlist:
        watchlist.append(new_watch)
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(watchlist, f)

if watchlist:
    st.sidebar.write("Your Watchlist:")
    for ticker in watchlist:
        try:
            info = yf.Ticker(ticker).info
            price = info.get("regularMarketPrice", "N/A")
            st.sidebar.write(f"{ticker}: {price}")
        except:
            st.sidebar.write(f"{ticker}: N/A")

