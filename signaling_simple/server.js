const WebSocket = require('ws');
const http = require('http');
const express = require('express');

const app = express();
const PORT = 8080;
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok',
        connections: wss.clients.size,
        timestamp: new Date().toISOString()
    });
});

// Simple broadcast - relay all messages to all other clients
wss.on('connection', (ws, req) => {
    const ip = req.socket.remoteAddress;
    console.log(`[${new Date().toISOString()}] ✅ Client connected from ${ip}`);
    console.log(`Total clients: ${wss.clients.size}`);
    
    ws.isAlive = true;
    ws.on('pong', () => { ws.isAlive = true; });
    
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            console.log(`📨 Received ${data.type} - broadcasting to ${wss.clients.size - 1} other clients`);
            
            // Broadcast to all OTHER clients
            wss.clients.forEach(client => {
                if (client !== ws && client.readyState === WebSocket.OPEN) {
                    client.send(message);
                }
            });
        } catch (err) {
            console.error('❌ Error processing message:', err);
        }
    });
    
    ws.on('close', () => {
        console.log(`👋 Client disconnected. Remaining: ${wss.clients.size}`);
    });
    
    ws.on('error', (err) => {
        console.error('WebSocket error:', err);
    });
});

// Heartbeat
const heartbeat = setInterval(() => {
    wss.clients.forEach(ws => {
        if (!ws.isAlive) {
            console.log('💀 Terminating dead connection');
            return ws.terminate();
        }
        ws.isAlive = false;
        ws.ping();
    });
}, 30000);

wss.on('close', () => clearInterval(heartbeat));

server.listen(PORT, '0.0.0.0', () => {
    console.log(`✅ Signaling server running on port ${PORT}`);
    console.log(`📡 WebSocket endpoint: ws://localhost:${PORT}`);
});
