import type { Telemetry } from './types.js';

const maxSamples = Math.max(100, Number(process.env.MAX_PPG_SAMPLES) || 1200);
let latest: Omit<Telemetry, 'ppg'> | null = null;
const samples: number[] = [];

export function saveTelemetry(input: Telemetry): Telemetry {
  const now = new Date().toISOString();
  latest = { timestamp: input.timestamp || now, bpm: input.bpm, spo2: input.spo2, temperature: input.temperature, humidity: input.humidity, simulated: input.simulated };
  for (const sample of input.ppg) samples.push(sample);
  if (samples.length > maxSamples) samples.splice(0, samples.length - maxSamples);
  return snapshot();
}

export function snapshot(): Telemetry {
  return { timestamp: latest?.timestamp ?? '', bpm: latest?.bpm ?? null, spo2: latest?.spo2 ?? null, temperature: latest?.temperature ?? null, humidity: latest?.humidity ?? null, simulated: latest?.simulated ?? false, ppg: [...samples] };
}

export function isFresh(): boolean {
  if (!latest) return false;
  const age = Date.now() - Date.parse(latest.timestamp);
  return Number.isFinite(age) && age >= -60_000 && age <= (Number(process.env.STALE_AFTER_MS) || 15_000);
}
