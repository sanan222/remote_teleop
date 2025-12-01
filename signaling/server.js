const WebSocket = require('ws');
const https = require('https');
const http = require('http');
const fs = require('fs');
const express = require('express');
const app = express();
const PORT = process.env.PORT || 8080;
// For now, use HTTP (we'll add HTTPS in Step 4)
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });
// Room management (stores connected clients by room)
const rooms = new Map();
// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    rooms: rooms.size,
    timestamp: new Date().toISOString()
  });
});
wss.on('connection', (ws, req) => {
  const clientIp = req.socket.remoteAddress;
  console.log(`[${new Date().toISOString()}] Client connected from ${clientIp}`);
  
  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });
  
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      const { type, roomId, senderId, payload } = data;
      
      console.log(`[${roomId}] Received ${type} from ${senderId || 'unknown'}`);
      
      // Handle room joining
      if (type === 'join-room') {
        if (!rooms.has(roomId)) {
          rooms.set(roomId, new Set());
        }
        rooms.get(roomId).add(ws);
        ws.roomId = roomId;
        ws.senderId = senderId;
        
        console.log(`[${roomId}] ${senderId} joined (${rooms.get(roomId).size} peers in room)`);
        
        // Notify client they joined successfully
        ws.send(JSON.stringify({
          type: 'joined',
          roomId,
          peersInRoom: rooms.get(roomId).size
        }));
      }
      
      // Relay signaling messages (offer, answer, ice-candidate)
      if (['offer', 'answer', 'ice-candidate'].includes(type)) {
        const room = rooms.get(roomId);
        if (room) {
          room.forEach(client => {
            // Send to everyone except sender
            if (client !== ws && client.readyState === WebSocket.OPEN) {
              client.send(JSON.stringify(data));
              console.log(`[${roomId}] Relayed ${type} to peer`);
            }
          });
        }
      }
      
    } catch (err) {
      console.error('Error processing message:', err);
    }
  });
  
  ws.on('close', () => {
    console.log(`[${ws.roomId || 'unknown'}] Client disconnected`);
    
    // Clean up room
    if (ws.roomId && rooms.has(ws.roomId)) {
      rooms.get(ws.roomId).delete(ws);
      
      // Delete empty rooms
      if (rooms.get(ws.roomId).size === 0) {
        rooms.delete(ws.roomId);
        console.log(`[${ws.roomId}] Room deleted (empty)`);
      }
    }
  });
  
  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
  });
});
// Heartbeat to detect dead connections
const heartbeat = setInterval(() => {
  wss.clients.forEach(ws => {
    if (!ws.isAlive) {
      console.log('Terminating dead connection');
      return ws.terminate();
    }
    ws.isAlive = false;
    ws.ping();
  });
}, 30000); // Every 30 seconds
wss.on('close', () => {
  clearInterval(heartbeat);
});
server.listen(PORT, '0.0.0.0', () => {
  console.log(`WebSocket signaling server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});
