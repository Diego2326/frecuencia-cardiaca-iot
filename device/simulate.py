"""Synthetic heart pulse, ambient readings, and optical PPG waveform."""
import math
import random
import time
from datetime import datetime, timezone
from common import Sender, SEND_INTERVAL, draw_oled, make_oled

def main():
    sender = Sender(); oled = make_oled(); bpm = 72.0; phase = 0.0
    while True:
        bpm += random.uniform(-0.5, 0.5); bpm = max(65, min(82, bpm))
        # A pulse-shaped optical waveform: rapid systolic upstroke, slower decay and small dicrotic notch.
        ppg = []
        for i in range(25):
            phase = (phase + bpm / 60 * SEND_INTERVAL / 25) % 1.0
            primary = math.exp(-((phase - 0.12) / 0.045) ** 2)
            decay = 0.24 * math.exp(-((phase - 0.34) / 0.13) ** 2)
            notch = 0.08 * math.exp(-((phase - 0.48) / 0.035) ** 2)
            ppg.append(round(50000 + 12000 * (primary + decay + notch) + random.gauss(0, 110)))
        packet = {"timestamp": datetime.now(timezone.utc).isoformat(), "bpm": round(bpm), "spo2": round(random.uniform(96, 99), 1), "temperature": round(random.uniform(22, 25), 1), "humidity": round(random.uniform(42, 55), 1), "ppg": ppg, "simulated": True}
        sender.send(packet); draw_oled(oled, packet["bpm"], packet["spo2"], ppg)
        time.sleep(SEND_INTERVAL)

if __name__ == "__main__": main()
