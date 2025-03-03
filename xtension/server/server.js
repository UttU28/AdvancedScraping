const express = require('express');
const app = express();
const port = 3000;

app.use(express.json());

app.post('/api/endpoint', (req, res) => {
  const { url } = req.body;
  console.log('URL received:', url);

  // Return some mock data or process the URL as needed.
  res.json({ message: `Data received from URL: ${url}`, success: true });
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
