export type Telemetry = {
  timestamp: string;
  bpm: number | null;
  spo2: number | null;
  temperature: number | null;
  humidity: number | null;
  ppg: number[];
  simulated: boolean;
};
