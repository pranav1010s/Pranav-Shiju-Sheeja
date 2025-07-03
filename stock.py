import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json

st.set_page_config(page_title="Portfolio Tracker", layout="wide")
st.title("📈 Personal Share Portfolio Tracker")

# Directory to store portfolios
PORTFOLIO_DIR = "portfolios"
os.makedirs(PORTFOLIO_DIR, exist_ok=True)

# Helper: get FX rate to GBP
def get_fx_rate_to_gbp(from_currency):
    if from_currency == "GBP":
        return 1.0
    fx_ticker = f"{from_currency}GBP=X"
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
    if st.sidebar.button("Delete Portfolio"):
        os.remove(os.path.join(PORTFOLIO_DIR, f"{selected_portfolio}.json"))
        st.success(f"Portfolio '{selected_portfolio}' deleted.")
        st.experimental_rerun()

# Load selected portfolio data
portfolio_data = {}
if selected_portfolio:
    try:
        with open(os.path.join(PORTFOLIO_DIR, f"{selected_portfolio}.json")) as f:
            portfolio_data = json.load(f)
        st.info(f"Loaded portfolio: **{selected_portfolio}**")
        if portfolio_data:
            st.write("### Current Portfolio Contents")
            df_preview = pd.DataFrame({
                "Ticker": portfolio_data.get("tickers", []),
                "Shares": portfolio_data.get("shares", []),
                "Buy Price (GBP)": portfolio_data.get("buy_prices", [])
            })
            st.dataframe(df_preview)
            st.caption("You can edit the fields below and click 'Save Portfolio' to update it.")
    except Exception:
        st.warning("Failed to load portfolio.")

# Input fields
tickers_input = st.text_input(
    "Enter stock/ETF ticker symbols separated by commas (e.g. AAPL, MSFT, SHEL.L, 0700.HK)",
    value=",".join(portfolio_data.get("tickers", []))
)

shares_input = st.text_area(
    "Enter number of shares for each ticker (decimals allowed), comma-separated, in the same order (e.g. 10, 5.5, 20.25)",
    value=",".join(map(str, portfolio_data.get("shares", [])))
)

buy_prices_input = st.text_area(
    "Enter your initial buy price for each ticker in GBP, comma-separated, in the same order (e.g. 120, 210, 25)",
    value=",".join(map(str, portfolio_data.get("buy_prices", [])))
)

# Save portfolio
if st.button("💾 Save Portfolio") and selected_portfolio:
    try:
        tickers = [t.strip().upper() for t in tickers_input.split(",")]
        shares = [float(s.strip()) for s in shares_input.split(",")]
        buy_prices = [float(p.strip()) for p in buy_prices_input.split(",")]
        if len(tickers) == len(shares) == len(buy_prices):
            portfolio_data = {
                "tickers": tickers,
                "shares": shares,
                "buy_prices": buy_prices
            }
            with open(os.path.join(PORTFOLIO_DIR, f"{selected_portfolio}.json"), "w") as f:
                json.dump(portfolio_data, f)
            st.success(f"Portfolio '{selected_portfolio}' saved.")
        else:
            st.error("Mismatch in number of tickers, shares, or buy prices.")
    except Exception as e:
        st.error(f"Error saving portfolio: {e}")

# Portfolio Analysis
if tickers_input:
    tickers = [t.strip().upper() for t in tickers_input.split(",")]

    try:
        shares = [float(s.strip()) for s in shares_input.split(",")]
    except Exception:
        st.error("Error parsing shares. Please enter valid decimal numbers separated by commas.")
        st.stop()

    try:
        buy_prices_gbp = [float(p.strip()) for p in buy_prices_input.split(",")]
    except Exception:
        st.error("Error parsing buy prices. Please enter valid decimal numbers separated by commas.")
        st.stop()

    if len(shares) != len(tickers) or len(buy_prices_gbp) != len(tickers):
        st.error("The number of shares and buy prices must match the number of tickers.")
        st.stop()

    portfolio_data = []
    total_value_gbp = 0
    total_cost_gbp = 0

    for ticker, qty, buy_price_gbp in zip(tickers, shares, buy_prices_gbp):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            current_price_raw = info.get('regularMarketPrice')
            currency = info.get('currency', 'GBP')
            exchange = info.get('exchange', '')

            if current_price_raw is None:
                st.warning(f"No current price found for {ticker}. Skipping.")
                continue

            if exchange == "LSE":
                current_price_native = current_price_raw / 100.0
            else:
                current_price_native = current_price_raw

            fx_rate = get_fx_rate_to_gbp(currency)
            current_price_gbp = current_price_native * fx_rate

            value_gbp = current_price_gbp * qty
            cost_gbp = buy_price_gbp * qty

            returns = (current_price_gbp - buy_price_gbp) / buy_price_gbp * 100 if buy_price_gbp > 0 else 0

            pe_ratio = info.get('trailingPE', None)
            analyst_rating_raw = info.get('recommendationKey', 'N/A')
            rating_map = {
                'buy': 'Buy',
                'hold': 'Hold',
                'sell': 'Sell',
                'strong_buy': 'Strong Buy',
                'strong_sell': 'Strong Sell',
                None: 'N/A'
            }
            analyst_rating = rating_map.get(analyst_rating_raw, 'N/A')

            portfolio_data.append({
                "Ticker": ticker,
                "Shares": qty,
                "Buy Price (GBP)": buy_price_gbp,
                "Current Price (native)": current_price_native,
                "Current Price (GBP)": current_price_gbp,
                "Currency": currency,
                "Value (GBP)": value_gbp,
                "Cost Basis (GBP)": cost_gbp,
                "Return (%)": returns,
                "P/E Ratio": pe_ratio if pe_ratio is not None else "N/A",
                "Analyst Rating": analyst_rating
            })

            total_value_gbp += value_gbp
            total_cost_gbp += cost_gbp

        except Exception as e:
            st.warning(f"Failed to fetch data for {ticker}: {e}")

    if portfolio_data:
        df = pd.DataFrame(portfolio_data)

        df_display = df.copy()
        df_display["Buy Price (GBP)"] = df_display["Buy Price (GBP)"].map("£{:.2f}".format)
        df_display["Current Price (native)"] = df_display["Current Price (native)"].map("${:.2f}".format)
        df_display["Current Price (GBP)"] = df_display["Current Price (GBP)"].map("£{:.2f}".format)
        df_display["Value (GBP)"] = df_display["Value (GBP)"].map("£{:.2f}".format)
        df_display["Cost Basis (GBP)"] = df_display["Cost Basis (GBP)"].map("£{:.2f}".format)
        df_display["Return (%)"] = df_display["Return (%)"].map("{:.2f}%".format)
        df_display["P/E Ratio"] = df_display["P/E Ratio"].apply(lambda x: f"{x:.2f}" if isinstance(x, (float, int)) else x)

        st.subheader("📊 Portfolio Summary")
        st.dataframe(df_display)

        total_return = (total_value_gbp - total_cost_gbp) / total_cost_gbp * 100 if total_cost_gbp > 0 else 0
        st.write(f"### 💰 Total portfolio value (GBP): £{total_value_gbp:.2f}")
        st.write(f"### 🧾 Total cost basis (GBP): £{total_cost_gbp:.2f}")
        st.write(f"### 📈 Overall portfolio return: {total_return:.2f}%")

        st.subheader("📉 Portfolio Combined Price Chart (Weighted Close Price in GBP, 1 Month)")

        combined_df = pd.DataFrame()
        for ticker, qty in zip(tickers, shares):
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")[['Close']]
            if hist.empty:
                continue
            hist = hist.copy()

            info = stock.info
            currency = info.get('currency', 'GBP')
            exchange = info.get('exchange', '')

            if exchange == "LSE":
                hist['Close'] = hist['Close'] / 100.0

            fx_rate = get_fx_rate_to_gbp(currency)
            hist['CloseGBP'] = hist['Close'] * fx_rate
            hist[ticker] = hist['CloseGBP'] * qty
            hist = hist[[ticker]]

            if combined_df.empty:
                combined_df = hist
            else:
                combined_df = combined_df.join(hist, how="outer")

        if not combined_df.empty:
            combined_df.fillna(method='ffill', inplace=True)
            combined_df['Total Value GBP'] = combined_df.sum(axis=1)
            st.line_chart(combined_df['Total Value GBP'])

