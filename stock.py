import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json
import datetime
import matplotlib.pyplot as plt

# Set up page
st.set_page_config(page_title="Advanced Portfolio Tracker", layout="wide")
st.title("📈 Advanced Personal Share Portfolio Tracker")

# Constants
PORTFOLIO_DIR = "portfolios"
WATCHLIST_FILE = "watchlist.json"
BASE_CURRENCIES = ["GBP", "USD", "EUR", "CAD", "JPY"]
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
    path = os.path.join(PORTFOLIO_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_portfolio(name, data):
    path = os.path.join(PORTFOLIO_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f)

def delete_portfolio(name):
    path = os.path.join(PORTFOLIO_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)

def rename_portfolio(old_name, new_name):
    old_path = os.path.join(PORTFOLIO_DIR, f"{old_name}.json")
    new_path = os.path.join(PORTFOLIO_DIR, f"{new_name}.json")
    if os.path.exists(old_path) and not os.path.exists(new_path):
        os.rename(old_path, new_path)

def get_portfolio_names():
    return [f.replace(".json", "") for f in os.listdir(PORTFOLIO_DIR) if f.endswith(".json")]

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    return []

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f)

# Sidebar - Portfolio Manager
st.sidebar.header("📁 Portfolio Manager")
portfolio_names = get_portfolio_names()
selected_portfolio = st.sidebar.selectbox("Select Portfolio", [""] + portfolio_names)
new_portfolio_name = st.sidebar.text_input("Create New Portfolio")
if st.sidebar.button("Create Portfolio") and new_portfolio_name:
    if new_portfolio_name not in portfolio_names:
        save_portfolio(new_portfolio_name, {"base_currency": "GBP", "stocks": []})
        st.sidebar.success(f"Portfolio '{new_portfolio_name}' created.")
    else:
        st.sidebar.warning("Portfolio already exists.")

if selected_portfolio:
    if st.sidebar.button("Delete Portfolio"):
        delete_portfolio(selected_portfolio)
        st.sidebar.success(f"Portfolio '{selected_portfolio}' deleted.")
        st.experimental_rerun()

    rename_to = st.sidebar.text_input("Rename Portfolio")
    if st.sidebar.button("Rename") and rename_to:
        rename_portfolio(selected_portfolio, rename_to)
        st.sidebar.success(f"Portfolio renamed to '{rename_to}'.")
        st.experimental_rerun()

# Load selected portfolio
portfolio_data = {}
if selected_portfolio:
    portfolio_data = load_portfolio(selected_portfolio)

# Base currency selection
base_currency = st.selectbox("Select Base Currency", BASE_CURRENCIES, index=BASE_CURRENCIES.index(portfolio_data.get("base_currency", "GBP")))
portfolio_data["base_currency"] = base_currency

# Editable stock table
st.subheader("📋 Portfolio Stocks")
stocks_df = pd.DataFrame(portfolio_data.get("stocks", []))
if stocks_df.empty:
    stocks_df = pd.DataFrame(columns=["Ticker", "Shares", "Buy Price (Base)"])
edited_df = st.data_editor(stocks_df, num_rows="dynamic", use_container_width=True)
portfolio_data["stocks"] = edited_df.dropna().to_dict(orient="records")

# Save portfolio
if selected_portfolio and st.button("💾 Save Portfolio"):
    save_portfolio(selected_portfolio, portfolio_data)
    st.success("Portfolio saved.")

# Portfolio Analysis
if not edited_df.empty:
    st.subheader("📊 Portfolio Analysis")
    analysis_data = []
    total_value = 0
    total_cost = 0
    sector_allocation = {}

    for row in portfolio_data["stocks"]:
        ticker = row["Ticker"].strip().upper()
        shares = float(row["Shares"])
        buy_price = float(row["Buy Price (Base)"])
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get("regularMarketPrice", 0)
            currency = info.get("currency", base_currency)
            fx_rate = get_fx_rate(currency, base_currency)
            price_base = price * fx_rate
            value = price_base * shares
            cost = buy_price * shares
            returns = (price_base - buy_price) / buy_price * 100 if buy_price > 0 else 0
            dividend_yield = info.get("dividendYield", 0) or 0
            sector = info.get("sector", "Unknown")
            sector_allocation[sector] = sector_allocation.get(sector, 0) + value

            analysis_data.append({
                "Ticker": ticker,
                "Shares": shares,
                "Buy Price": buy_price,
                "Current Price": round(price_base, 2),
                "Value": round(value, 2),
                "Return (%)": round(returns, 2),
                "Dividend Yield": f"{dividend_yield*100:.2f}%",
                "Sector": sector
            })
            total_value += value
            total_cost += cost
        except Exception as e:
            st.warning(f"Error fetching data for {ticker}: {e}")

    df_analysis = pd.DataFrame(analysis_data)
    st.dataframe(df_analysis, use_container_width=True)
    st.write(f"**Total Value ({base_currency})**: {total_value:.2f}")
    st.write(f"**Total Cost ({base_currency})**: {total_cost:.2f}")
    st.write(f"**Total Return (%)**: {((total_value - total_cost) / total_cost * 100):.2f}" if total_cost > 0 else "N/A")

    # Sector Allocation Pie Chart
    st.subheader("📌 Sector Allocation")
    if sector_allocation:
        fig, ax = plt.subplots()
        ax.pie(sector_allocation.values(), labels=sector_allocation.keys(), autopct='%1.1f%%')
        ax.axis("equal")
        st.pyplot(fig)

    # Benchmark Comparison
    st.subheader("📈 Benchmark Comparison (S&P 500)")
    try:
        benchmark = yf.Ticker(BENCHMARK_TICKER).history(period="1mo")["Close"]
        portfolio_hist = pd.Series(index=benchmark.index, dtype=float)
        for row in portfolio_data["stocks"]:
            ticker = row["Ticker"].strip().upper()
            shares = float(row["Shares"])
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")["Close"]
            info = stock.info
            currency = info.get("currency", base_currency)
            fx_rate = get_fx_rate(currency, base_currency)
            hist_base = hist * fx_rate * shares
            portfolio_hist = portfolio_hist.add(hist_base, fill_value=0)
        combined = pd.DataFrame({
            "Portfolio": portfolio_hist,
            "S&P 500": benchmark / benchmark.iloc[0] * portfolio_hist.iloc[0]
        })
        st.line_chart(combined)
    except Exception as e:
        st.warning(f"Benchmark comparison failed: {e}")

    # Export to CSV
    st.download_button("📤 Export Portfolio to CSV", df_analysis.to_csv(index=False), file_name="portfolio.csv")

# Watchlist
st.sidebar.subheader("👀 Watchlist")
watchlist = load_watchlist()
new_watch = st.sidebar.text_input("Add Ticker to Watchlist")
if st.sidebar.button("Add to Watchlist") and new_watch:
    if new_watch.upper() not in watchlist:
        watchlist.append(new_watch.upper())
        save_watchlist(watchlist)
if st.sidebar.button("Clear Watchlist"):
    watchlist = []
    save_watchlist(watchlist)

if watchlist:
    st.sidebar.write("### Watchlist Prices")
    for ticker in watchlist:
        try:
            price = yf.Ticker(ticker).info.get("regularMarketPrice", "N/A")
            st.sidebar.write(f"{ticker}: {price}")
        except:
            st.sidebar.write(f"{ticker}: Error")

# Sentiment Analysis (News Headlines)
st.subheader("📰 Sentiment Analysis (News Headlines)")
for row in portfolio_data.get("stocks", []):
    ticker = row["Ticker"].strip().upper()
    st.write(f"**{ticker} News**")
    try:
        news = yf.Ticker(ticker).news[:3]
        for item in news:
            st.markdown(f"- [{item['title']}]({item['link']})")
    except:
        st.write("No news available.")



