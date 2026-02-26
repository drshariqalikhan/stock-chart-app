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

// API Endpoint
app.get('/api/stock', async (req, res) => {
    try {
        const { symbol, years } = req.query;

        if (!symbol) {
            return res.status(400).json({ error: 'Symbol is required' });
        }

        // 1. Calculate Start Date
        // We want data starting from X years ago
        const startDate = new Date();
        startDate.setFullYear(startDate.getFullYear() - (parseInt(years) || 1));
        const dateStr = startDate.toISOString().split('T')[0]; // Format: YYYY-MM-DD

        // 2. Fetch Data from Twelve Data
        // Interval: 1week
        const url = `https://api.twelvedata.com/time_series?symbol=${symbol}&interval=1week&start_date=${dateStr}&apikey=${API_KEY}`;
        
        console.log(`Fetching: ${symbol} from ${dateStr}`);
        
        const response = await fetch(url);
        const data = await response.json();

        // 3. Handle Errors (Twelve Data returns 200 OK even on error, so check body)
        if (data.status === 'error' || !data.values) {
            throw new Error(data.message || 'Invalid symbol or API limit reached');
        }

        // 4. Format Data
        // Twelve Data returns newest first. Chart.js needs oldest first.
        const history = data.values.reverse();

        const chartData = {
            labels: history.map(item => item.datetime),
            prices: history.map(item => parseFloat(item.close))
        };

        res.json(chartData);

    } catch (error) {
        console.error("Stock Fetch Error:", error.message);
        res.status(500).json({ error: error.message });
    }
});

// Serve frontend for any other route
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});