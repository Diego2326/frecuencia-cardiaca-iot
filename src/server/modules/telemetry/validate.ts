import type { Request, Response, NextFunction } from 'express';
import type { Telemetry } from './types.js';

const nullableNumber = (value: unknown, min: number, max: number): value is number | null => value === null || (typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max);
export function validateTelemetry(req: Request, res: Response, next: NextFunction): void {
  const body = req.body as Partial<Telemetry> | undefined;
  if (!body || typeof body !== 'object' || !Array.isArray(body.ppg) || body.ppg.length > 500 ||
      !body.ppg.every(v => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1_000_000) ||
      !nullableNumber(body.bpm, 20, 250) || !nullableNumber(body.spo2, 50, 100) ||
      !nullableNumber(body.temperature, -40, 85) || !nullableNumber(body.humidity, 0, 100) || typeof body.simulated !== 'boolean' ||
      (body.timestamp !== undefined && (typeof body.timestamp !== 'string' || !Number.isFinite(Date.parse(body.timestamp))))) {
    res.status(400).json({ error: 'Invalid telemetry payload' }); return;
  }
  next();
}
