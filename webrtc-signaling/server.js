// server.js
const WebSocket = require('ws');

// Use 8080 or another port you opened in the firewall
const WSS_PORT = 8080; 

const wss = new WebSocket.Server({ port: WSS_PORT });

console.log(`Signaling server listening on port ${WSS_PORT}`);

// Array to hold connected clients, for demonstration purposes
const clients = new Set(); 

wss.on('connection', function connection(ws) {
  // A new client (browser/robot) has connected
  clients.add(ws);
  console.log(`Client connected. Total clients: ${clients.size}`);
  
  // Handle incoming messages (SDP Offer/Answer, ICE Candidate)
  ws.on('message', function incoming(message) {
    const messageStr = message.toString();
    // console.log('received: %s', messageStr); // Uncomment for debugging
    
    // Relay the message to ALL other clients
    clients.forEach(client => {
      if (client !== ws && client.readyState === WebSocket.OPEN) {
        client.send(messageStr);
      }
    });
  });

  // Handle client disconnection
  ws.on('close', () => {
    clients.delete(ws);
    console.log(`Client disconnected. Total clients: ${clients.size}`);
  });
});
