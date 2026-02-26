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

        // 1. Calculate Start Date
        const startDate = new Date();
        startDate.setFullYear(startDate.getFullYear() - (parseInt(years) || 1));
        const dateStr = startDate.toISOString().split('T')[0];

        console.log(`Fetching Data for: ${symbol}`);

        // 2. Parallel API Calls (Price + Earnings)
        // We fetch 100 earnings reports to ensure we have enough history for the TTM calculation
        const priceUrl = `https://api.twelvedata.com/time_series?symbol=${symbol}&interval=1week&start_date=${dateStr}&apikey=${API_KEY}`;
        const earningsUrl = `https://api.twelvedata.com/earnings?symbol=${symbol}&outputsize=100&apikey=${API_KEY}`;

        const [priceRes, earningsRes] = await Promise.all([
            fetch(priceUrl),
            fetch(earningsUrl)
        ]);

        const priceData = await priceRes.json();
        const earningsData = await earningsRes.json();

        // 3. Error Handling
        if (priceData.status === 'error') throw new Error(priceData.message);
        // Note: Earnings might be empty for ETFs/Crypto, handle gracefully
        const earningsList = (earningsData.earnings || []).reverse(); // Sort Oldest -> Newest

        // 4. Process Data
        // Twelve Data prices come Newest -> Oldest. Reverse them for the chart.
        const history = (priceData.values || []).reverse();

        const labels = [];
        const prices = [];
        const peRatios = [];

        // 5. Calculate P/E TTM for each week
        history.forEach(point => {
            const date = point.datetime;
            const closePrice = parseFloat(point.close);
            const pointDate = new Date(date);

            labels.push(date);
            prices.push(closePrice);

            // Find earnings reported strictly BEFORE or ON this week's date
            const pastEarnings = earningsList.filter(e => new Date(e.date) <= pointDate);

            // We need the last 4 quarters (TTM)
            if (pastEarnings.length >= 4) {
                const last4 = pastEarnings.slice(-4);
                
                // Sum EPS (Earnings Per Share)
                const ttmEps = last4.reduce((sum, e) => sum + (parseFloat(e.eps_actual) || 0), 0);

                if (ttmEps > 0) {
                    peRatios.push((closePrice / ttmEps).toFixed(2));
                } else {
                    peRatios.push(null); // Negative or zero earnings (P/E undefined or negative)
                }
            } else {
                peRatios.push(null); // Not enough data
            }
        });

        res.json({ labels, prices, peRatios });

    } catch (error) {
        console.error("API Error:", error.message);
        res.status(500).json({ error: error.message || 'Failed to fetch data' });
    }
});

app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});