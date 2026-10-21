"""Checks for the shared 128×64 OLED frame renderer."""
import unittest

from common import render_oled_frame


class OledFrameTests(unittest.TestCase):
    def test_rendered_frame_matches_monochrome_oled_dimensions(self):
        frame = render_oled_frame(72, 98, [100, 120, 190, 110, 105])
        self.assertEqual(frame.size, (128, 64))
        self.assertEqual(frame.mode, "1")
        self.assertGreater(sum(frame.convert("L").getdata()), 0)

    def test_frame_shows_waiting_message_without_ppg_samples(self):
        frame = render_oled_frame(None, None, [])
        self.assertEqual(frame.size, (128, 64))
        self.assertGreater(sum(frame.convert("L").getdata()), 0)


if __name__ == "__main__":
    unittest.main()
