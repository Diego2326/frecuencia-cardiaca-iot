import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';
import type { Telemetry } from '../../server/modules/telemetry/types';
import { PpgChart } from './PpgChart';

type Data = Telemetry & { connected?: boolean };
const empty: Data = { timestamp: '', bpm: null, spo2: null, temperature: null, humidity: null, ppg: [], simulated: false, connected: false };
const socket = io({ autoConnect: true, reconnection: true, reconnectionDelay: 1000, reconnectionDelayMax: 5000 });
const time = (date: string) => date ? new Date(date).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';

export function App() {
  const [data, setData] = useState<Data>(empty);
  const [online, setOnline] = useState(socket.connected);
  useEffect(() => {
    const onTelemetry = (value: Data) => setData(value);
    const onStatus = (status: { connected: boolean }) => setData(old => ({ ...old, connected: status.connected }));
    socket.on('connect', () => setOnline(true)); socket.on('disconnect', () => setOnline(false));
    socket.on('telemetry', onTelemetry); socket.on('status', onStatus);
    fetch('/api/telemetry/latest').then(r => r.ok ? r.json() : null).then(v => v && setData(v)).catch(() => undefined);
    return () => { socket.off('telemetry', onTelemetry); socket.off('status', onStatus); };
  }, []);
  return <main className="shell">
    <header className="topbar">
      <div className="brand">Monitor cardíaco</div>
      <div className="top-right">
        {data.simulated && <span className="simulation">Datos simulados</span>}
        <span className={`connection ${data.connected ? 'live' : ''}`}><i/>{data.connected ? 'Conectado' : online ? 'Esperando dispositivo' : 'Reconectando'}</span>
      </div>
    </header>
    <main>
      <section className="intro">
        <div><p className="eyebrow">LECTURA ACTUAL</p><h1>Frecuencia cardíaca</h1></div>
        <div className="updated"><span>Última medición</span><strong>{time(data.timestamp)}</strong></div>
      </section>
      <section className="readings">
        <article className="bpm-panel"><span className="label">Pulso</span><div className="bpm-value">{data.bpm ?? '—'}<small>{data.bpm === null ? '' : 'bpm'}</small></div></article>
        <Metric label="SpO₂" value={data.spo2} unit="%"/>
        <Metric label="Temperatura" value={data.temperature} unit="°C"/>
        <Metric label="Humedad" value={data.humidity} unit="%"/>
      </section>
      <section className="waveform-card">
        <div className="wave-head"><div><h2>Onda de pulso</h2><p>Señal óptica PPG · MAX30102</p></div><span className="sample-count">{data.ppg.length} muestras</span></div>
        <PpgChart samples={data.ppg}/>
        <div className="wave-foot">PPG muestra el pulso óptico; no es una señal ECG.</div>
      </section>
    </main>
    <footer><span>Orange Pi Zero 2W <b>·</b> MAX30102 <b>·</b> AHT10</span><span>Actualización en tiempo real</span></footer>
  </main>;
}

function Metric({ label, value, unit }: { label: string; value: number | null; unit: string }) {
  return <article className="metric"><span className="label">{label}</span><div className="metric-reading">{value === null ? '—' : value}<small>{value === null ? '' : unit}</small></div></article>;
}
