import { Router } from 'express';
import { saveTelemetry, snapshot, isFresh } from './store.js';
import { validateTelemetry } from './validate.js';
import type { Server } from 'socket.io';

export function telemetryRouter(io: Server): Router {
  const router = Router();
  router.get('/latest', (_req, res) => res.json({ ...snapshot(), connected: isFresh() }));
  router.post('/ingest', validateTelemetry, (req, res) => {
    const data = saveTelemetry(req.body);
    io.emit('telemetry', { ...data, connected: true });
    res.status(202).json({ accepted: true });
  });
  return router;
}
