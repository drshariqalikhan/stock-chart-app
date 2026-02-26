import os
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np

app = Flask(__name__, static_folder='static')
CORS(app)

# Service Worker Script
SW_CODE = """
const CACHE_NAME = 'stock-pe-v1';
const ASSETS = ['/', '/index.html'];
self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(CACHE_NAME).then((c) => c.addAll(ASSETS)));
});
self.addEventListener('fetch', (e) => {
    if (e.request.url.includes('/api/')) {
        e.respondWith(fetch(e.request));
    } else {
        e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    }
});
"""

@app.route('/sw.js')
def serve_sw():
    return Response(SW_CODE, mimetype='application/javascript')

@app.route('/api/stock')
def get_stock_data():
    try:
        symbol = request.args.get('symbol', 'AAPL').upper()
        years = int(request.args.get('years', '3'))
        ticker = yf.Ticker(symbol)
        
        # 1. Fetch Price Data
        hist = ticker.history(period=f"{years + 2}y", interval="1wk")
        if hist.empty: return jsonify({'error': 'No price data'}), 404
        hist.index = hist.index.tz_localize(None).normalize()

        # 2. Fetch Earnings History (This goes back much further than Income Stmt)
        # We get the last 40 entries to ensure a deep history
        earnings_df = ticker.get_earnings_dates(limit=40)
        
        pe_list = [None] * len(hist)

        if earnings_df is not None and not earnings_df.empty:
            # We want 'Reported EPS'. We drop rows where it's NaN.
            # The index of earnings_df is the date the earnings were announced.
            eps_data = earnings_df['Reported EPS'].dropna().sort_index()
            eps_data.index = eps_data.index.tz_localize(None).normalize()
            
            pe_list = []
            for date, row in hist.iterrows():
                # Get earnings reported BEFORE or ON this specific price date
                past_eps = eps_data[eps_data.index <= date]
                
                if len(past_eps) >= 4:
                    # Sum the 4 most recent quarters relative to this date
                    ttm_eps = past_eps.tail(4).sum()
                    val = row['Close'] / ttm_eps if (ttm_eps and ttm_eps > 0) else None
                    pe_list.append(round(val, 2) if val else None)
                else:
                    pe_list.append(None)

        hist['PE'] = pe_list
        
        # 3. Final Filtering for the chart view
        cutoff = pd.Timestamp.now().normalize() - pd.DateOffset(years=years)
        final_df = hist[hist.index >= cutoff].replace({np.nan: None})

        return jsonify({
            'labels': final_df.index.strftime('%Y-%m-%d').tolist(),
            'prices': final_df['Close'].round(2).tolist(),
            'peRatios': final_df['PE'].tolist()
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)