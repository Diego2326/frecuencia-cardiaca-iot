"""Hardware driver checks using a fake SMBus; safe to run without an Orange Pi."""
import math
import unittest

from sensors import AHT10, MAX30102, PulseEstimator


class FakeBus:
    def __init__(self, pointers=(0, 0), blocks=()):
        self.write_pointer, self.read_pointer = pointers
        self.blocks = list(blocks)
        self.writes = []

    def write_byte_data(self, address, register, value):
        self.writes.append((address, register, value))
        if register == 0x04:
            self.write_pointer = value
        elif register == 0x06:
            self.read_pointer = value

    def write_i2c_block_data(self, address, register, values):
        self.writes.append((address, register, values))

    def read_byte_data(self, address, register):
        return {0x04: self.write_pointer, 0x06: self.read_pointer}[register]

    def read_i2c_block_data(self, address, register, length):
        return self.blocks.pop(0)


class SensorDriverTests(unittest.TestCase):
    def test_max30102_initializes_fifo_and_spo2_mode(self):
        bus = FakeBus()
        MAX30102(bus)
        registers = [(register, value) for _, register, value in bus.writes if isinstance(value, int)]
        self.assertIn((0x09, 0x40), registers)  # Reset
        self.assertIn((0x08, 0x4F), registers)  # FIFO averaging and rollover
        self.assertIn((0x09, 0x03), registers)  # SpO2 mode
        self.assertIn((0x0A, 0x27), registers)  # 100 Hz, 411 us pulse width
        self.assertIn((0x04, 0), registers)
        self.assertIn((0x06, 0), registers)

    def test_aht10_converts_temperature_and_humidity(self):
        # Raw temperature 0x60000 = 25 C, raw humidity 0x80000 = 50%.
        bus = FakeBus(blocks=[[0, 0x80, 0, 0x06, 0, 0]])
        self.assertEqual(AHT10(bus).read(), (25.0, 50.0))
        self.assertEqual(bus.writes[0], (0x38, 0xAC, [0x33, 0x00]))

    def test_max30102_reads_existing_fifo_samples(self):
        bus = FakeBus(pointers=(3, 0), blocks=[
            [0x01, 0x23, 0x45, 0x02, 0x34, 0x56],
            [0x00, 0x00, 0x01, 0x00, 0x00, 0x02],
            [0x03, 0x21, 0x09, 0x01, 0x11, 0x10],
        ])
        sensor = MAX30102.__new__(MAX30102)
        sensor.bus = bus
        self.assertEqual(sensor.read_samples(), [
            (0x12345, 0x23456),
            (1, 2),
            (0x32109, 0x11110),
        ])

    def test_pulse_estimator_tracks_synthetic_75_bpm_wave(self):
        estimator = PulseEstimator()
        readings = []
        for index in range(800):
            now = index / 100
            phase = (now * 1.25) % 1
            pulse = math.exp(-((phase - 0.12) / 0.045) ** 2)
            pulse += 0.24 * math.exp(-((phase - 0.34) / 0.13) ** 2)
            pulse += 0.08 * math.exp(-((phase - 0.48) / 0.035) ** 2)
            value = 50_000 + round(pulse * 12_000)
            bpm, spo2 = estimator.add(value, value, now)
            if bpm is not None:
                readings.append((bpm, spo2))
        self.assertTrue(readings)
        self.assertEqual(readings[-1][0], 75)
        self.assertIsNotNone(readings[-1][1])


if __name__ == "__main__":
    unittest.main()
