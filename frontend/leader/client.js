// --- CONFIGURATION ---
// REPLACE THIS IP with your Google Cloud VM Public IP!
const SIGNALING_SERVER_URL = "wss://readytoserve.online/ws";

const ICE_SERVERS = {
    iceServers: [
        { urls: "stun:stun.l.google.com:19302" }
    ]
};

// --- GLOBAL VARIABLES ---
let pc;
let ws;
let role; // 'robot' or 'operator'
let dataChannel;

const videoElem = document.getElementById('mainVideo');

// --- 1. STARTUP FUNCTIONS ---

async function startAsRobot() {
    role = 'robot';
    log("🤖 Starting as ROBOT (Streamer)...");
    disableButtons();

    // 1. Get Camera
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        videoElem.srcObject = stream; // Show local view

        // 2. Initialize WebRTC
        setupPeerConnection();

        // 3. Add Stream to Connection
        stream.getTracks().forEach(track => pc.addTrack(track, stream));

        // 4. Connect to Signaling Server
        connectToSignaling();

    } catch (e) {
        log("Error accessing camera: " + e.message);
    }
}

function startAsOperator() {
    role = 'operator';
    log("Starting as OPERATOR (Controller)...");
    disableButtons();

    // 1. Initialize WebRTC
    setupPeerConnection();

    // 2. Ask for video to be received from streamer side
    pc.addTransceiver('video', { direction: 'recvonly' });

    // 2. Create Data Channel (Operator initiates this!)
    setupDataChannel();

    // 3. Connect to Signaling Server
    connectToSignaling();
}

// --- 2. WEBRTC SETUP ---

function setupPeerConnection() {
    pc = new RTCPeerConnection(ICE_SERVERS);

    // Handle ICE Candidates (Network Paths)
    pc.onicecandidate = (event) => {
        if (event.candidate) {
            sendSignal({ type: "candidate", candidate: event.candidate });
        }
    };

    // Handle Connection State Changes
    pc.onconnectionstatechange = () => {
        log(`⚡ Connection State: ${pc.connectionState}`);
    };

    // ROBOT SPECIFIC: Handle incoming Data Channel (for receiving actions)
    if (role === 'robot') {
        pc.ondatachannel = (event) => {
            const receiveChannel = event.channel;
            receiveChannel.onopen = () => log("✅ Data Channel OPEN (Robot)");
            receiveChannel.onmessage = (msg) => {
                // EXECUTE ROBOT ACTIONS HERE
                const action = JSON.parse(msg.data);
                log(`📥 Action Received: ${JSON.stringify(action)}`);
            };
        };
    }

    // OPERATOR SPECIFIC: Handle incoming Video
    if (role === 'operator') {
        pc.ontrack = (event) => {
            log("🎥 Video Stream Received!");
            videoElem.srcObject = event.streams[0];
        };
    }
}

function setupDataChannel() {
    // Only Operator creates the channel
    dataChannel = pc.createDataChannel("robot-control");

    dataChannel.onopen = () => {
        log("✅ Data Channel OPEN (Operator)");
        // Start sending dummy actions for testing
        setInterval(() => {
            if (dataChannel.readyState === 'open') {
                const action = { x: Math.random().toFixed(2), y: Math.random().toFixed(2) };
                dataChannel.send(JSON.stringify(action));
            }
        }, 1000);
    };
}

// --- 3. SIGNALING (WEBSOCKET) ---

function connectToSignaling() {
    log("Connecting to Signaling Server...");
    ws = new WebSocket(SIGNALING_SERVER_URL);

    ws.onopen = () => {
        log("📡 Connected to Signaling Server");
        // If Operator, start the call immediately
        if (role === 'operator') {
            createAndSendOffer();
        }
    };

    ws.onmessage = async (message) => {
        const data = JSON.parse(message.data);

        if (data.type === "offer" && role === 'robot') {
            log("📩 Received Offer");
            await pc.setRemoteDescription(new RTCSessionDescription(data.offer));
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            sendSignal({ type: "answer", answer: answer });
            log("fw Sent Answer");
        }
        else if (data.type === "answer" && role === 'operator') {
            log("📩 Received Answer");
            await pc.setRemoteDescription(new RTCSessionDescription(data.answer));
        }
        else if (data.type === "candidate") {
            // log("❄️ Added ICE Candidate");
            await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
        }
    };

    ws.onerror = (e) => log("❌ WebSocket Error. Check IP/Port/Firewall.");
}

async function createAndSendOffer() {
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    sendSignal({ type: "offer", offer: offer });
    console.log("offer", offer)
    log("fw Sent Offer");
}

function sendSignal(data) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

// --- UTILS ---

function log(msg) {
    const logs = document.getElementById('logs');
    logs.innerHTML += `<div>${new Date().toLocaleTimeString()} - ${msg}</div>`;
    logs.scrollTop = logs.scrollHeight;
    console.log(msg);
}

function disableButtons() {
    document.getElementById('roleSelection').style.display = 'None';
}

