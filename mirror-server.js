const http = require('http');
const fs = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');

const PORT = 3847;
const CODE_TTL_MS = 15 * 60 * 1000;

/** @type {Map<string, { createdAt: number, host: import('ws').WebSocket | null, client: import('ws').WebSocket | null }>} */
const rooms = new Map();

function randomCode() {
  let code;
  do {
    code = String(Math.floor(100 + Math.random() * 900));
  } while (rooms.has(code));
  return code;
}

function purgeExpired() {
  const now = Date.now();
  for (const [code, room] of rooms) {
    if (now - room.createdAt > CODE_TTL_MS) {
      room.host?.close();
      room.client?.close();
      rooms.delete(code);
    }
  }
}

setInterval(purgeExpired, 60_000);

function send(ws, msg) {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify(msg));
}

function relay(from, room, payload) {
  const target = from === room.host ? room.client : room.host;
  send(target, payload);
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
};

const server = http.createServer((req, res) => {
  const url = new URL(req.url || '/', `http://localhost:${PORT}`);

  if (url.pathname === '/api/create-code' && req.method === 'POST') {
    purgeExpired();
    const code = randomCode();
    rooms.set(code, { createdAt: Date.now(), host: null, client: null });
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ code }));
    return;
  }

  if (url.pathname.startsWith('/api/room/') && req.method === 'GET') {
    const code = url.pathname.slice('/api/room/'.length);
    const room = rooms.get(code);
    const valid = room && Date.now() - room.createdAt <= CODE_TTL_MS;
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: !!valid, hasHost: !!(valid && room.host) }));
    return;
  }

  let filePath = url.pathname === '/' ? '/index.html' : url.pathname;
  filePath = path.join(__dirname, path.normalize(filePath).replace(/^(\.\.(\/|\\|$))+/, ''));
  if (!filePath.startsWith(__dirname)) {
    res.writeHead(403);
    res.end();
    return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    const ext = path.extname(filePath);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(data);
  });
});

const wss = new WebSocketServer({ server, path: '/ws' });

wss.on('connection', (ws, req) => {
  const url = new URL(req.url || '', `http://localhost:${PORT}`);
  const code = url.searchParams.get('code');
  const role = url.searchParams.get('role');

  if (!code || !rooms.has(code) || (role !== 'host' && role !== 'client')) {
    ws.close(4000, 'invalid');
    return;
  }

  const room = rooms.get(code);
  if (Date.now() - room.createdAt > CODE_TTL_MS) {
    ws.close(4001, 'expired');
    return;
  }

  if (role === 'host') {
    if (room.host) {
      ws.close(4002, 'host_busy');
      return;
    }
    room.host = ws;
  } else {
    if (room.client) {
      ws.close(4003, 'client_busy');
      return;
    }
    room.client = ws;
  }

  send(ws, { type: 'joined', role, peerReady: !!(role === 'host' ? room.client : room.host) });
  const peer = role === 'host' ? room.client : room.host;
  if (peer) {
    send(peer, { type: 'peer-joined', role });
    send(ws, { type: 'peer-joined', role: role === 'host' ? 'client' : 'host' });
  }

  ws.on('message', (raw) => {
    let msg;
    try {
      msg = JSON.parse(String(raw));
    } catch {
      return;
    }
    if (['offer', 'answer', 'ice', 'hangup'].includes(msg.type)) {
      relay(ws, room, msg);
    }
  });

  ws.on('close', () => {
    if (room.host === ws) room.host = null;
    if (room.client === ws) room.client = null;
    const other = room.host || room.client;
    send(other, { type: 'peer-left' });
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Mirror: http://0.0.0.0:${PORT}/code.html`);
  console.log(`Sur le tel, ouvre la même adresse (Wi‑Fi du PC) puis Saisir code.`);
});
