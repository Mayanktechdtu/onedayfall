import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Define the Nifty 50 stock symbols
nifty_50_symbols = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "HINDUNILVR.NS", "HDFC.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "SBIN.NS",
    # Add more Nifty 50 symbols as required
]

# Function to fetch data from Yahoo Finance
def fetch_data(symbols, start_date, end_date):
    data = {}
    for symbol in symbols:
        try:
            stock_data = yf.download(symbol, start=start_date, end=end_date)
            if not stock_data.empty:
                data[symbol] = stock_data
            else:
                st.warning(f"No data found for {symbol}.")
        except Exception as e:
            st.error(f"Error fetching data for {symbol}: {e}")
    return data

# Function to analyze significant falls and their aftermath
def analyze_falls(data, days_after):
    results = []
    for symbol, df in data.items():
        # Ensure the DataFrame contains required columns
        if 'Close' not in df.columns:
            st.warning(f"Missing 'Close' column for {symbol}. Skipping analysis.")
            continue

        try:
            df['Fall%'] = df['Close'].pct_change() * 100
            df = df.dropna(subset=['Close', 'Fall%'])  # Drop rows with NaN values in relevant columns
            falls = df[df['Fall%'] <= -5]

            for index, row in falls.iterrows():
                after_fall_df = df.loc[index:].copy()
                after_fall_df['Below Fall'] = after_fall_df['Close'] < row['Close']
                continuous_fall_days = (
                    after_fall_df['Below Fall'].cumsum() - 
                    after_fall_df['Below Fall'].cumsum().where(~after_fall_df['Below Fall']).ffill().fillna(0)
                ).max()

                # Maximum consecutive days below fall price
                max_days_below_fall = 0
                count_below_fall = 0
                for close in after_fall_df['Close']:
                    if close < row['Close']:
                        count_below_fall += 1
                    else:
                        count_below_fall = 0
                    max_days_below_fall = max(max_days_below_fall, count_below_fall)

                percent_below_fall = ((after_fall_df['Close'].min() - row['Close']) / row['Close']) * 100
                
                analysis = {
                    'Symbol': symbol,
                    'Date': index,
                    'Close on Fall': row['Close'],
                    'Fall%': row['Fall%'],
                    'Continuous Fall Days': continuous_fall_days,
                    'Max Days Below Fall': max_days_below_fall,
                    'Percent Below Fall': percent_below_fall,
                    'After 1 Day': df['Close'].shift(-1).loc[index],
                    'After 1 Day % Change': ((df['Close'].shift(-1).loc[index] - row['Close']) / row['Close']) * 100,
                    'After 3 Days': df['Close'].shift(-3).loc[index],
                    'After 3 Days % Change': ((df['Close'].shift(-3).loc[index] - row['Close']) / row['Close']) * 100,
                    'After 5 Days': df['Close'].shift(-5).loc[index],
                    'After 5 Days % Change': ((df['Close'].shift(-5).loc[index] - row['Close']) / row['Close']) * 100,
                    f'After {days_after} Days': df['Close'].shift(-days_after).loc[index],
                    f'After {days_after} Days % Change': ((df['Close'].shift(-days_after).loc[index] - row['Close']) / row['Close']) * 100
                }
                results.append(analysis)
        except Exception as e:
            st.error(f"Error processing data for {symbol}: {e}")
    return pd.DataFrame(results)

# Function to calculate maximum fall and other metrics
def calculate_max_fall(data):
    results = []
    for symbol, df in data.items():
        if df.empty:
            st.warning(f"No data available for {symbol}. Skipping.")
            continue

        try:
            df['Fall%'] = df['Close'].pct_change() * 100
            max_fall_start_date = df['Close'].idxmax()
            max_fall_start_open = df['Open'].loc[max_fall_start_date]
            max_fall_period = df[df['Close'] < max_fall_start_open]
            max_fall_end_date = max_fall_period.index[-1] if not max_fall_period.empty else df.index[-1]
            max_fall_percent = ((df['Close'].loc[max_fall_end_date] - max_fall_start_open) / max_fall_start_open) * 100
            max_fall_start_price = df['Close'].loc[max_fall_start_date]
            max_fall_end_price = df['Close'].loc[max_fall_end_date]
            
            # Determine red and green candles in the max fall period
            max_fall_period = df.loc[max_fall_start_date:max_fall_end_date]
            red_candles = (max_fall_period['Close'] < max_fall_period['Open']).sum()
            green_candles = (max_fall_period['Close'] > max_fall_period['Open']).sum()

            # Determine maximum number of back-to-back red candles
            max_red_streak = 0
            current_red_streak = 0
            for close, open_ in zip(max_fall_period['Close'], max_fall_period['Open']):
                if close < open_:
                    current_red_streak += 1 
                    max_red_streak = max(max_red_streak, current_red_streak)
                else:
                    current_red_streak = 0

            results.append({
                'Symbol': symbol,
                'Max Fall%': max_fall_percent,
                'Max Fall Start Date': max_fall_start_date,
                'Max Fall Start Price': max_fall_start_price,
                'Max Fall End Date': max_fall_end_date,
                'Max Fall End Price': max_fall_end_price,
                'Red Candles': red_candles,
                'Green Candles': green_candles,
                'Max Red Candles': max_red_streak
            })
        except Exception as e:
            st.error(f"Error processing max fall data for {symbol}: {e}")
    return pd.DataFrame(results)

# Streamlit dashboard
st.title('Nifty 50 Stocks Analysis')
st.subheader('Stocks with Falls Greater than 5% in a Day for the Year 2023')

# User input for days after fall
days_after = st.slider("Select days after fall for analysis", min_value=1, max_value=30, value=7)

# Fetch historical data for the year 2023
data_2023 = fetch_data(nifty_50_symbols, '2023-01-01', '2023-12-31')

# Analyze the falls greater than 5% for 2023
fall_analysis_2023 = analyze_falls(data_2023, days_after)

if not fall_analysis_2023.empty:
    st.subheader('Detailed Analysis of Falls and Aftermath')
    st.write(fall_analysis_2023)
else:
    st.warning("No significant falls were found in the data.")

# Select year for maximum fall analysis
year = st.selectbox("Select year for maximum fall analysis", [2021, 2022, 2023])

# Fetch historical data for the selected year
start_date = f"{year}-01-01"
end_date = f"{year}-12-31"
data = fetch_data(nifty_50_symbols, start_date, end_date)

# Calculate maximum fall and other metrics for the selected year
max_fall_analysis = calculate_max_fall(data)

st.subheader(f'Maximum Fall Analysis for {year}')
if not max_fall_analysis.empty:
    st.write(max_fall_analysis)
else:
    st.warning(f"No maximum fall data available for {year}.")
