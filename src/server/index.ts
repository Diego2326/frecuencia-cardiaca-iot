import express from 'express';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import helmet from 'helmet';
import cors from 'cors';
import { Server } from 'socket.io';
import { telemetryRouter } from './modules/telemetry/routes.js';
import { configureRealtime } from './modules/realtime/socket.js';

const token = process.env.DEVICE_TOKEN;
if (!token) throw new Error('DEVICE_TOKEN must be configured');
const app = express();
const server = http.createServer(app);
const origins = process.env.CORS_ORIGIN?.split(',').map(s => s.trim()) ?? ['*'];
const io = new Server(server, { cors: { origin: origins.includes('*') ? '*' : origins, methods: ['GET', 'POST'] }, transports: ['websocket', 'polling'] });
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({ origin: origins.includes('*') ? true : origins }));
app.use(express.json({ limit: '64kb' }));
app.get('/api/health', (_req, res) => res.json({ ok: true }));
app.use('/api/telemetry', (req, res, next) => {
  if (req.method === 'POST' && req.header('authorization') !== `Bearer ${token}`) { res.status(401).json({ error: 'Unauthorized' }); return; }
  next();
}, telemetryRouter(io));

const here = path.dirname(fileURLToPath(import.meta.url));
const clientDir = path.resolve(here, '../client');
app.use(express.static(clientDir));
app.get('*', (_req, res) => res.sendFile(path.join(clientDir, 'index.html')));
const port = Number(process.env.PORT) || 8080;
configureRealtime(io);
server.listen(port, '0.0.0.0', () => console.log(`Monitor listening on ${port}`));
