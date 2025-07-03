# Regenerate the corrected Streamlit script with proper initialization of edited_df
script_content = """
import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json
import plotly.express as px

st.set_page_config(page_title="Portfolio Tracker", layout="wide")
st.title("📈 Personal Share Portfolio Tracker")

PORTFOLIO_DIR = "portfolios"
os.makedirs(PORTFOLIO_DIR, exist_ok=True)

def get_fx_rate_to_gbp(from_currency, base_currency="GBP"):
    if from_currency == base_currency:
        return 1.0
    fx_ticker = f"{from_currency}{base_currency}=X"
    try:
        fx_data = yf.Ticker(fx_ticker).history(period="1d")
        if fx_data.empty:
            return 1.0
        return fx_data['Close'][-1]
    except Exception:
        return 1.0

def get_portfolio_names():
    return [f.replace(".json", "") for f in os.listdir(PORTFOLIO_DIR) if f.endswith(".json")]

st.sidebar.header("📁 Portfolio Manager")
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

portfolio_data = {}
edited_df = pd.DataFrame(columns=["Ticker", "Shares", "Buy Price"])
if selected_portfolio:
    try:
        with open(os.path.join(PORTFOLIO_DIR, f"{selected_portfolio}.json")) as f:
            portfolio_data = json.load(f)
        st.info(f"Loaded portfolio: **{selected_portfolio}**")
        if portfolio_data:
            df_preview = pd.DataFrame({
                "Ticker": portfolio_data.get("tickers", []),
                "Shares": portfolio_data.get("shares", []),
                "Buy Price": portfolio_data.get("buy_prices", [])
            })
            edited_df = st.data_editor(df_preview, num_rows="dynamic", use_container_width=True)
    except Exception:
        st.warning("Failed to load portfolio.")

if st.button("💾 Save Portfolio") and selected_portfolio:
    try:
        if not edited_df.empty:
            tickers = edited_df["Ticker"].astype(str).str.upper().tolist()
            shares = edited_df["Shares"].astype(float).tolist()
            buy_prices = edited_df["Buy Price"].astype(float).tolist()
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

if not edited_df.empty:
    tickers = edited_df["Ticker"].astype(str).str.upper().tolist()
    shares = edited_df["Shares"].astype(float).tolist()
    buy_prices_gbp = edited_df["Buy Price"].astype(float).tolist()

    portfolio_data = []
    total_value_gbp = 0
    total_cost_gbp = 0
    sector_allocation = {}

    for ticker, qty, buy_price_gbp in zip(tickers, shares, buy_prices_gbp):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            current_price_raw = info.get('regularMarketPrice')
            currency = info.get('currency', 'GBP')
            exchange = info.get('exchange', '')
            sector = info.get('sector', 'Unknown')
            dividend_yield = info.get('dividendYield', 0.0)

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
                "Analyst Rating": analyst_rating,
                "Dividend Yield": f"{dividend_yield*100:.2f}%" if dividend_yield else "N/A",
                "Sector": sector
            })

            total_value_gbp += value_gbp
            total_cost_gbp += cost_gbp
            sector_allocation[sector] = sector_allocation.get(sector, 0) + value_gbp

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

        if sector_allocation:
            st.subheader("📌 Sector Allocation")
            sector_df = pd.DataFrame({
                'Sector': list(sector_allocation.keys()),
                'Value': list(sector_allocation.values())
            })
            fig = px.pie(sector_df, names='Sector', values='Value', title='Sector Allocation')
            st.plotly_chart(fig)
"""

with open("portfolio_tracker.py", "w") as f:
    f.write(script_content)

"portfolio_tracker.py"

