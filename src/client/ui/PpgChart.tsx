import { useEffect, useRef } from 'react';
export function PpgChart({ samples }: { samples: number[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const data = useRef(samples);
  data.current = samples;
  useEffect(() => {
    const canvas = ref.current!; const ctx = canvas.getContext('2d')!; let frame = 0;
    const draw = () => {
      const dpr = window.devicePixelRatio || 1; const rect = canvas.getBoundingClientRect();
      if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) { canvas.width = rect.width * dpr; canvas.height = rect.height * dpr; }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); const w = rect.width, h = rect.height;
      ctx.clearRect(0, 0, w, h); ctx.strokeStyle = 'rgba(118,150,130,.10)'; ctx.lineWidth = 1;
      for (let x=0; x<w; x+=30) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,h); ctx.stroke(); }
      for (let y=0; y<h; y+=30) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(w,y); ctx.stroke(); }
      const values = data.current.slice(-Math.floor(w / 2));
      if (values.length > 1) {
        const min = Math.min(...values), max = Math.max(...values), span = max-min || 1;
        ctx.beginPath(); values.forEach((v,i) => { const x = w - ((values.length-1-i)*2) - (frame%2); const y = h*.5 - ((v-min)/span-.5)*h*.62; if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); });
        ctx.lineWidth=2.2; ctx.strokeStyle='#68ff94'; ctx.shadowColor='#38f575'; ctx.shadowBlur=10; ctx.stroke(); ctx.shadowBlur=0;
        ctx.beginPath(); ctx.moveTo(0,h*.5); ctx.lineTo(w,h*.5); ctx.strokeStyle='rgba(104,255,148,.10)'; ctx.stroke();
      } else {
        ctx.fillStyle='#63736a'; ctx.font='12px ui-monospace, monospace'; ctx.textAlign='center'; ctx.fillText('ESPERANDO MUESTRAS PPG', w/2,h/2);
      }
      frame++; raf = requestAnimationFrame(draw);
    };
    let raf = requestAnimationFrame(draw); const resize = () => { canvas.width=0; }; window.addEventListener('resize',resize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize',resize); };
  }, []);
  return <canvas className="wave-canvas" ref={ref} aria-label="Señal PPG en tiempo real"/>;
}
