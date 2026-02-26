import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

// Setup file paths for ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Your Twelve Data API Key
const API_KEY = '3dca03d1de204312874e027e212e654d';

app.use(cors());
app.use(express.static('public'));

app.get('/api/stock', async (req, res) => {
    try {
        const { symbol, years } = req.query;

        if (!symbol) return res.status(400).json({ error: 'Symbol is required' });

        const startDate = new Date();
        startDate.setFullYear(startDate.getFullYear() - (parseInt(years) || 1));
        const dateStr = startDate.toISOString().split('T')[0];

        console.log(`Processing: ${symbol} (History: ${years}y)`);

        // Fetch Price and Earnings in parallel
        const priceUrl = `https://api.twelvedata.com/time_series?symbol=${symbol}&interval=1week&start_date=${dateStr}&apikey=${API_KEY}`;
        const earningsUrl = `https://api.twelvedata.com/earnings?symbol=${symbol}&outputsize=100&apikey=${API_KEY}`;

        const [priceRes, earningsRes] = await Promise.all([
            fetch(priceUrl),
            fetch(earningsUrl)
        ]);

        const priceData = await priceRes.json();
        const earningsData = await earningsRes.json();

        // Check for API Failures (Rate Limits, Invalid Symbol)
        if (priceData.status === 'error') {
            throw new Error(`Price API Error: ${priceData.message}`);
        }
        
        // Note: We don't throw on Earnings error, because some stocks (ETFs) just don't have them.
        // We just log it and proceed with empty earnings.
        if (earningsData.status === 'error') {
            console.warn(`Earnings API Warning for ${symbol}: ${earningsData.message}`);
        }

        // Prepare Data
        // 1. Price Data (Newest -> Oldest from API, we reverse to Oldest -> Newest)
        const history = (priceData.values || []).reverse();
        
        // 2. Earnings Data (Newest -> Oldest from API, we reverse to Oldest -> Newest)
        const rawEarnings = earningsData.earnings || [];
        const earningsList = rawEarnings.reverse();

        console.log(`Found ${history.length} price points and ${earningsList.length} earnings reports.`);

        const labels = [];
        const prices = [];
        const peRatios = [];

        // Loop through weekly price data to calculate TTM P/E for that specific week
        history.forEach(point => {
            const date = point.datetime;
            const closePrice = parseFloat(point.close);
            const pointDate = new Date(date);

            labels.push(date);
            prices.push(closePrice);

            // Filter earnings that happened BEFORE this specific week
            const pastEarnings = earningsList.filter(e => new Date(e.date) <= pointDate);

            // We need exactly 4 quarters (Trailing Twelve Months)
            if (pastEarnings.length >= 4) {
                // Get the most recent 4 reports relative to this date
                const last4 = pastEarnings.slice(-4);
                
                // Sum the EPS (Earnings Per Share)
                // parseFloat might return NaN if data is missing, so we default to 0
                const ttmEps = last4.reduce((sum, e) => sum + (parseFloat(e.eps_actual) || 0), 0);

                // Calculate P/E
                if (ttmEps !== 0) {
                    // Allow negative P/E (for companies losing money)
                    peRatios.push((closePrice / ttmEps).toFixed(2));
                } else {
                    // EPS is 0, cannot divide by zero
                    peRatios.push(null);
                }
            } else {
                // Not enough history yet
                peRatios.push(null);
            }
        });

        res.json({ labels, prices, peRatios });

    } catch (error) {
        console.error("Server Error:", error.message);
        // Send the specific error message to the frontend
        res.status(500).json({ error: error.message });
    }
});

app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});