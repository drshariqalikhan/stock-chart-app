import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/api/stock')
def get_stock_data():
    try:
        symbol = request.args.get('symbol', 'AAPL').upper()
        years = int(request.args.get('years', '3'))
        
        # 1. Fetch Ticker
        ticker = yf.Ticker(symbol)
        
        # 2. Fetch Weekly Price History (fetch extra for TTM window)
        hist = ticker.history(period=f"{years + 2}y", interval="1wk")
        if hist.empty:
            return jsonify({'error': f'No price data found for {symbol}'}), 404

        # 3. Fetch Quarterly Income Statement
        income_stmt = ticker.quarterly_income_stmt
        
        # Default: No P/E data available
        pe_list = [None] * len(hist)

        if income_stmt is not None and not income_stmt.empty:
            # 4. Extract EPS (Earnings Per Share)
            # Try to find common EPS keys in the index
            eps_keys = ['Diluted EPS', 'Basic EPS', 'EPS Basic', 'EPS Diluted']
            eps_row = None
            for key in eps_keys:
                if key in income_stmt.index:
                    eps_row = income_stmt.loc[key]
                    break
            
            if eps_row is not None:
                eps_series = eps_row.sort_index() # Oldest to newest
                
                # 5. Calculate TTM P/E for each price point
                pe_list = []
                for date, row in hist.iterrows():
                    # Filter for earnings reported BEFORE or ON this specific price date
                    past_eps = eps_series[eps_series.index <= date]
                    
                    if len(past_eps) >= 4:
                        # Sum last 4 reported quarters
                        ttm_eps = past_eps.tail(4).sum()
                        if ttm_eps != 0 and not pd.isna(ttm_eps):
                            pe_val = row['Close'] / ttm_eps
                            pe_list.append(round(pe_val, 2))
                        else:
                            pe_list.append(None)
                    else:
                        pe_list.append(None)

        hist['PE'] = pe_list

        # 6. Filter to requested timeframe and format
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
        final_df = hist[hist.index >= cutoff].replace({np.nan: None})

        return jsonify({
            'labels': final_df.index.strftime('%Y-%m-%d').tolist(),
            'prices': final_df['Close'].round(2).tolist(),
            'peRatios': final_df['PE'].tolist()
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({'error': str(e)}), 500

# --- Serve Frontend Routes ---
@app.route('/')
def serve_index():
    # Looking for static/index.html
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)