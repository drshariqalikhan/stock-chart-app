import logging
import yfinance as yf
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serves the single-file PWA from the static folder."""
    logger.info("Event: Frontend requested.")
    file_path = os.path.join("static", "index.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Error: {file_path} not found.")
        raise HTTPException(status_code=404, detail="Frontend file not found.")

@app.get("/api/earnings/{ticker}")
async def get_earnings(ticker: str):
    """Fetches historical earnings data for the given ticker."""
    ticker = ticker.upper()
    logger.info(f"Event: Fetching earnings data for {ticker}")
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.get_earnings_dates(limit=12)
        
        if df is None or df.empty:
            raise ValueError(f"No earnings data available for {ticker}.")

        # Yahoo Finance often changes its formatting. 
        # We check if the expected columns exist to prevent crashes.
        if 'Reported EPS' not in df.columns or 'EPS Estimate' not in df.columns:
            raise ValueError(f"Yahoo Finance is missing EPS columns for {ticker}.")

        # Safely clean the data
        df = df.dropna(subset=['Reported EPS', 'EPS Estimate'])
        
        if df.empty:
             raise ValueError(f"Earnings data for {ticker} contains blank values.")

        df = df.sort_index() # Sort chronologically
        
        # Extract data to lists
        dates = df.index.strftime('%Y-%m-%d').tolist()
        reported_eps = df['Reported EPS'].tolist()
        estimated_eps = df['EPS Estimate'].tolist()

        logger.info(f"Event: Successfully retrieved {len(dates)} records for {ticker}")
        
        return {
            "ticker": ticker,
            "dates": dates,
            "reported": reported_eps,
            "estimate": estimated_eps
        }

    except Exception as e:
        # Instead of crashing the server, gracefully send the error to the UI logs
        error_msg = str(e)
        logger.error(f"Error fetching data for {ticker}: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)