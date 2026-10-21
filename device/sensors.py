"""MAX30102 + AHT10 reader. Requires I2C enabled and sensor power at 3.3 V."""
import math
import os
import time
from collections import deque
from datetime import datetime, timezone
from smbus2 import SMBus
from common import Sender, SEND_INTERVAL, draw_oled, make_oled

BUS_NO = int(os.getenv("I2C_BUS", "0")); MAX_ADDR = int(os.getenv("MAX30102_ADDRESS", "0x57"), 0); AHT_ADDR = int(os.getenv("AHT10_ADDRESS", "0x38"), 0)

class AHT10:
    def __init__(self, bus): self.bus = bus
    def read(self):
        self.bus.write_i2c_block_data(AHT_ADDR, 0xAC, [0x33, 0x00]); time.sleep(.08)
        data = self.bus.read_i2c_block_data(AHT_ADDR, 0, 6)
        if data[0] & 0x80: raise RuntimeError("AHT10 calibration incomplete")
        raw_h = ((data[1] << 12) | (data[2] << 4) | (data[3] >> 4))
        raw_t = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]
        return round(raw_t * 200 / 1048576 - 50, 1), round(raw_h * 100 / 1048576, 1)

class MAX30102:
    def __init__(self, bus):
        self.bus = bus
        self.write(0x09, 0x40); time.sleep(.05) # reset
        self.write(0x08, 0x4F) # FIFO averaging 4, rollover
        self.write(0x09, 0x03) # SpO2 mode, red + IR
        self.write(0x0A, 0x27) # 4096 nA, 100 Hz, 411 us
        self.write(0x0C, 0x24); self.write(0x0D, 0x24) # LED currents
        self.write(0x04, 0); self.write(0x05, 0); self.write(0x06, 0)
    def write(self, reg, value): self.bus.write_byte_data(MAX_ADDR, reg, value)
    def read_samples(self):
        count = (self.bus.read_byte_data(MAX_ADDR, 0x04) - self.bus.read_byte_data(MAX_ADDR, 0x06)) & 0x1F
        result = []
        for _ in range(min(count, 32)):
            d = self.bus.read_i2c_block_data(MAX_ADDR, 0x07, 6)
            red = ((d[0]&3)<<16)|(d[1]<<8)|d[2]; ir = ((d[3]&3)<<16)|(d[4]<<8)|d[5]
            result.append((red, ir))
        return result

class PulseEstimator:
    """Peak timing and ratio-of-ratios SpO2 estimate from red/IR samples."""
    def __init__(self): self.ir = deque(maxlen=400); self.red = deque(maxlen=400); self.peaks = deque(maxlen=8); self.last_peak = 0.0
    def add(self, red, ir, now):
        self.red.append(red); self.ir.append(ir)
        if len(self.ir) < 20: return None, None
        mean = sum(self.ir)/len(self.ir); threshold = mean + max(100, (max(self.ir)-min(self.ir))*.18)
        if self.ir[-2] < self.ir[-1] and self.ir[-1] >= self.ir[-3] and self.ir[-1] > threshold and now-self.last_peak > .3:
            if self.last_peak: self.peaks.append(now-self.last_peak)
            self.last_peak = now
        bpm = None
        intervals = [x for x in self.peaks if .3 < x < 2]
        if intervals: bpm = round(60/(sum(intervals)/len(intervals)))
        # Estimate over recent pulsatile AC / DC ratio. This is indicative, not clinical-grade.
        rdc, idc = sum(self.red)/len(self.red), sum(self.ir)/len(self.ir)
        rac, iac = (max(self.red)-min(self.red))/2, (max(self.ir)-min(self.ir))/2
        ratio = (rac/max(rdc,1))/(iac/max(idc,1))
        spo2 = round(max(70, min(100, 110 - 25*ratio)), 1) if iac > 0 else None
        return (bpm if bpm and 30 <= bpm <= 220 else None), (spo2 if spo2 and iac > 20 else None)

def main():
    sender = Sender(); oled = make_oled(); estimator = PulseEstimator(); ppg_window = deque(maxlen=25)
    with SMBus(BUS_NO) as bus:
        sensor = MAX30102(bus); aht = AHT10(bus)
        while True:
            started = time.monotonic(); values = sensor.read_samples(); bpm = spo2 = None
            for red, ir in values:
                bpm, spo2 = estimator.add(red, ir, time.monotonic()); ppg_window.append(ir)
            temperature = humidity = None
            try: temperature, humidity = aht.read()
            except OSError as exc: print(f"AHT10 read failed: {exc}", flush=True)
            packet = {"timestamp": datetime.now(timezone.utc).isoformat(), "bpm": bpm, "spo2": spo2, "temperature": temperature, "humidity": humidity, "ppg": list(ppg_window), "simulated": False}
            sender.send(packet); draw_oled(oled, bpm, spo2, list(ppg_window), temperature, humidity)
            time.sleep(max(0, SEND_INTERVAL-(time.monotonic()-started)))

if __name__ == "__main__": main()
