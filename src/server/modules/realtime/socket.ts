import type { Server } from 'socket.io';
import { snapshot, isFresh } from '../telemetry/store.js';
export function configureRealtime(io: Server): void {
  io.on('connection', socket => socket.emit('telemetry', { ...snapshot(), connected: isFresh() }));
  const timer = setInterval(() => io.emit('status', { connected: isFresh() }), 3000);
  timer.unref();
}
