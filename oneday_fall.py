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
        df['Fall%'] = df['Close'].pct_change() * 100
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
    return pd.DataFrame(results)

# Function to calculate maximum fall and other metrics
def calculate_max_fall(data):
    results = []
    for symbol, df in data.items():
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
    return pd.DataFrame(results)

# Function to plot stock performance
def plot_stock_performance(data, symbol, fall_dates, range_after):
    fig = go.Figure()
    for date in fall_dates:
        date = pd.to_datetime(date)
        start_date = date - pd.Timedelta(days=5)
        end_date = date + pd.Timedelta(days=range_after)
        
        stock_data = data[symbol][start_date:end_date]
        
        fig.add_trace(go.Scatter(
            x=stock_data.index,
            y=stock_data['Close'],
            mode='lines+markers',
            line=dict(color='blue'),
            name=f'Performance near {date.date()}',
            text=[f'Date: {dt.date()}<br>Close: {price:.2f}' for dt, price in zip(stock_data.index, stock_data['Close'])],
            hoverinfo='text'
        ))

        # Add red dot for falling date
        fig.add_trace(go.Scatter(
            x=[date],
            y=[data[symbol]['Close'].loc[date]],
            mode='markers',
            marker=dict(color='red', size=10),
            name=f'Fall on {date.date()}',
            text=[f'Date: {date.date()}<br>Close: {data[symbol]["Close"].loc[date]:.2f}'],
            hoverinfo='text'
        ))

    fig.update_layout(
        title=f'Stock Performance of {symbol} around Significant Falls',
        xaxis_title='Date',
        yaxis_title='Close Price',
        hovermode='x unified'
    )
    st.plotly_chart(fig)

# Fetch historical data for the year 2023
data_2023 = fetch_data(nifty_50_symbols, '2023-01-01', '2023-12-31')

# Streamlit dashboard
st.title('Nifty 50 Stocks Analysis')
st.subheader('Stocks with Falls Greater than 5% in a Day for the Year 2023')

# User input for days after fall
days_after = st.slider("Select days after fall for analysis", min_value=1, max_value=30, value=7)

# Analyze the falls greater than 5% for 2023
fall_analysis_2023 = analyze_falls(data_2023, days_after)

# Calculate frequency of falls for 2023
fall_frequency_2023 = fall_analysis_2023['Symbol'].value_counts().reset_index()
fall_frequency_2023.columns = ['Symbol', 'Frequency']
st.write(fall_frequency_2023)

st.subheader('Detailed Analysis of Falls and Aftermath for 2023')
st.write(fall_analysis_2023)

# Plot stock performance for selected stock
st.subheader('Stock Performance After Significant Falls for 2023')
selected_stock_2023 = st.selectbox('Select a Stock', fall_frequency_2023['Symbol'].unique(), key='stock_2023')
range_after_2023 = st.slider("Select range of days to display after the fall", min_value=5, max_value=60, value=30, key='range_2023')
selected_fall_dates_2023 = fall_analysis_2023[fall_analysis_2023['Symbol'] == selected_stock_2023]['Date']
plot_stock_performance(data_2023, selected_stock_2023, selected_fall_dates_2023, range_after_2023)

# Select year for maximum fall analysis
year = st.selectbox("Select year for maximum fall analysis", [2021, 2022, 2023])

# Fetch historical data for the selected year
start_date = f"{year}-01-01"
end_date = f"{year}-12-31"
data = fetch_data(nifty_50_symbols, start_date, end_date)

# Calculate maximum fall and other metrics for the selected year
max_fall_analysis = calculate_max_fall(data)

st.subheader(f'Maximum Fall Analysis for {year}')
st.write(max_fall_analysis)

# Plot stock performance for selected stock in maximum fall analysis
st.subheader(f'Stock Performance for Maximum Fall in {year}')
selected_stock_max_fall = st.selectbox('Select a Stock', max_fall_analysis['Symbol'].unique(), key='stock_max_fall')
range_after_max_fall = st.slider("Select range of days to display after the fall", min_value=5, max_value=60, value=30, key='range_max_fall')
selected_fall_dates_max_fall = max_fall_analysis[max_fall_analysis['Symbol'] == selected_stock_max_fall][['Max Fall Start Date', 'Max Fall End Date']]
plot_stock_performance(data, selected_stock_max_fall, selected_fall_dates_max_fall.values.flatten(), range_after_max_fall)
