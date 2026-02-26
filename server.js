const express = require('express');
const cors = require('cors');
const yahooFinance = require('yahoo-finance2').default;
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.static('public'));

// API Endpoint to get stock history
app.get('/api/stock', async (req, res) => {
    try {
        const { symbol, years } = req.query;

        if (!symbol) {
            return res.status(400).json({ error: 'Symbol is required' });
        }

        const queryOptions = { period1: '2020-01-01', interval: '1wk' };
        
        // Calculate start date based on years requested
        const endDate = new Date();
        const startDate = new Date();
        startDate.setFullYear(endDate.getFullYear() - (parseInt(years) || 1));

        const result = await yahooFinance.historical(symbol, {
            period1: startDate,
            period2: endDate,
            interval: '1wk' // Weekly data
        });

        // Format data for Chart.js
        const chartData = {
            labels: result.map(quote => new Date(quote.date).toLocaleDateString()),
            prices: result.map(quote => quote.close)
        };

        res.json(chartData);

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Failed to fetch stock data. Check the ticker symbol.' });
    }
});

// Serve the PWA
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});