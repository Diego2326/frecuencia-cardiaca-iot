import { useEffect, useMemo, useState } from 'react';
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
  const beatStyle = useMemo(() => ({ animationDuration: `${data.bpm && data.bpm > 0 ? 60 / data.bpm : 1}s`, animationPlayState: data.bpm ? 'running' as const : 'paused' as const }), [data.bpm]);
  return <main className="shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">P</span><span>PULSE<span className="slash"> / </span>MONITOR</span></div><div className="top-right">{data.simulated && <span className="simulation"><i/> SIMULACIÓN</span>}<span className={`connection ${data.connected ? 'live' : ''}`}><i/>{data.connected ? 'DISPOSITIVO EN LÍNEA' : 'SIN SEÑAL'}</span></div></header>
    <section className="intro"><div><div className="eyebrow">MONITOREO EN TIEMPO REAL <span>·</span> PPG</div><h1>Signos vitales</h1></div><div className="updated"><span>ÚLTIMA MEDICIÓN</span><strong>{time(data.timestamp)}</strong></div></section>
    <section className="primary-grid">
      <article className="card heart-card"><div className="card-label">FRECUENCIA CARDÍACA <span className="unit">BPM</span></div><div className="heart-reading"><div className="heart-icon" style={beatStyle}>♥</div><div className="big-number">{data.bpm ?? '—'}</div></div><div className="reading-foot"><span className="pulse-dot"/> PULSO ACTUAL <span className="muted">·</span> {data.bpm ? 'DETECTADO' : 'ESPERANDO DATOS'}</div></article>
      <article className="card metric-card"><Metric icon="◉" label="SpO₂" value={data.spo2} unit="%" note="SATURACIÓN ESTIMADA"/><div className="metric-divider"/><Metric icon="⌁" label="Temperatura" value={data.temperature} unit="°C" note="AMBIENTE"/><div className="metric-divider"/><Metric icon="◌" label="Humedad" value={data.humidity} unit="%" note="AMBIENTE"/></article>
    </section>
    <section className="card waveform-card"><div className="wave-head"><div><div className="card-label">ONDA DE PULSO <span className="wave-live"><i/> EN VIVO</span></div><div className="wave-subtitle">Fotopletismografía · señal óptica del MAX30102</div></div><div className="wave-scale">PPG <span>●</span></div></div><PpgChart samples={data.ppg}/><div className="wave-foot"><span>AMPLITUD RELATIVA</span><span>La señal PPG representa el pulso óptico, no un ECG.</span><span>{data.ppg.length} MUESTRAS</span></div></section>
    <footer><span>ORANGE PI ZERO 2W <b>·</b> MAX30102 <b>·</b> AHT10</span><span className="footer-status"><i className={data.connected ? 'ok' : ''}/>{data.connected ? 'TRANSMISIÓN ACTIVA' : online ? 'ESPERANDO DISPOSITIVO' : 'RECONECTANDO'}</span></footer>
  </main>;
}

function Metric({ icon, label, value, unit, note }: { icon: string; label: string; value: number | null; unit: string; note: string }) {
  return <div className="metric"><div className="metric-title"><span className="metric-icon">{icon}</span><span>{label}</span></div><div className="metric-reading">{value === null ? '—' : value}<small>{value === null ? '' : unit}</small></div><div className="metric-note">{note}</div></div>;
}
