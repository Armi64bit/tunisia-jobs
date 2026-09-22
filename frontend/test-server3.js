const http = require('http');
const server = http.createServer((req, res) => {
  console.log('Request received:', req.method, req.url);
  res.writeHead(200);
  res.end('Hello World');
});
server.listen(3000, '0.0.0.0', () => console.log('Server running on port 3000'));

// Keep process alive
setInterval(() => {}, 1000);