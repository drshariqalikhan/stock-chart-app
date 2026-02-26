import os
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np

app = Flask(__name__, static_folder='static')
CORS(app)

# --- Service Worker Script as a String ---
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
        
        # Fetch data (extra history for TTM sum)
        hist = ticker.history(period=f"{years + 2}y", interval="1wk")
        if hist.empty: return jsonify({'error': 'No price data'}), 404

        income_stmt = ticker.quarterly_income_stmt
        pe_list = [None] * len(hist)

        if income_stmt is not None and not income_stmt.empty:
            eps_keys = ['Diluted EPS', 'Basic EPS', 'EPS Basic', 'EPS Diluted']
            eps_row = next((income_stmt.loc[k] for k in eps_keys if k in income_stmt.index), None)
            
            if eps_row is not None:
                eps_series = eps_row.sort_index()
                pe_list = []
                for date, row in hist.iterrows():
                    past_eps = eps_series[eps_series.index <= date]
                    if len(past_eps) >= 4:
                        ttm_eps = past_eps.tail(4).sum()
                        val = row['Close'] / ttm_eps if (ttm_eps and ttm_eps > 0) else None
                        pe_list.append(round(val, 2) if val else None)
                    else:
                        pe_list.append(None)

        hist['PE'] = pe_list
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
        final_df = hist[hist.index >= cutoff].replace({np.nan: None})

        return jsonify({
            'labels': final_df.index.strftime('%Y-%m-%d').tolist(),
            'prices': final_df['Close'].round(2).tolist(),
            'peRatios': final_df['PE'].tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)