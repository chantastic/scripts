import tempfile
import unittest

from rc_silence import load_silences, invert_silences


class TestLoadSilences(unittest.TestCase):

    def test_parses_silence_output(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("[silencedetect @ 0x1] silence_start: 1.5\n")
            f.write("[silencedetect @ 0x1] silence_end: 3.2 | silence_duration: 1.7\n")
            f.write("[silencedetect @ 0x1] silence_start: 5.0\n")
            f.write("[silencedetect @ 0x1] silence_end: 6.0 | silence_duration: 1.0\n")
            f.name
        result = load_silences(f.name)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]['start'], 1.5)
        self.assertAlmostEqual(result[0]['end'], 3.2)
        self.assertAlmostEqual(result[1]['start'], 5.0)
        self.assertAlmostEqual(result[1]['end'], 6.0)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
        result = load_silences(f.name)
        self.assertEqual(result, [])

    def test_unpaired_silence_start(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("[silencedetect @ 0x1] silence_start: 1.5\n")
        result = load_silences(f.name)
        self.assertEqual(result, [])


class TestInvertSilences(unittest.TestCase):

    def test_no_silences(self):
        result = invert_silences([], 10.0)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]['start'], 0.0)
        self.assertAlmostEqual(result[0]['end'], 10.0)
        self.assertAlmostEqual(result[0]['duration'], 10.0)

    def test_silence_at_start(self):
        silences = [{'start': 0.0, 'end': 2.0}]
        result = invert_silences(silences, 10.0)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]['start'], 2.0)
        self.assertAlmostEqual(result[0]['end'], 10.0)

    def test_silence_at_end(self):
        silences = [{'start': 8.0, 'end': 10.0}]
        result = invert_silences(silences, 10.0)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]['start'], 0.0)
        self.assertAlmostEqual(result[0]['end'], 8.0)

    def test_multiple_silences(self):
        silences = [
            {'start': 2.0, 'end': 3.0},
            {'start': 5.0, 'end': 6.0},
            {'start': 8.0, 'end': 9.0},
        ]
        result = invert_silences(silences, 10.0)
        self.assertEqual(len(result), 4)
        # 0-2, 3-5, 6-8, 9-10
        self.assertAlmostEqual(result[0]['start'], 0.0)
        self.assertAlmostEqual(result[0]['end'], 2.0)
        self.assertAlmostEqual(result[1]['start'], 3.0)
        self.assertAlmostEqual(result[1]['end'], 5.0)
        self.assertAlmostEqual(result[2]['start'], 6.0)
        self.assertAlmostEqual(result[2]['end'], 8.0)
        self.assertAlmostEqual(result[3]['start'], 9.0)
        self.assertAlmostEqual(result[3]['end'], 10.0)

    def test_adjacent_silences(self):
        silences = [
            {'start': 2.0, 'end': 3.0},
            {'start': 3.0, 'end': 4.0},
        ]
        result = invert_silences(silences, 10.0)
        # Gap between silences is 0, so no speech interval between them
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]['start'], 0.0)
        self.assertAlmostEqual(result[0]['end'], 2.0)
        self.assertAlmostEqual(result[1]['start'], 4.0)
        self.assertAlmostEqual(result[1]['end'], 10.0)

    def test_silence_covers_entire_duration(self):
        silences = [{'start': 0.0, 'end': 10.0}]
        result = invert_silences(silences, 10.0)
        self.assertEqual(result, [])

    def test_short_gaps_filtered(self):
        silences = [
            {'start': 2.0, 'end': 2.9},  # gap of 0.1s before next silence
            {'start': 3.0, 'end': 5.0},
        ]
        result = invert_silences(silences, 10.0, min_speech=0.3)
        # Gap between 2.9 and 3.0 is 0.1s, less than min_speech
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]['start'], 0.0)
        self.assertAlmostEqual(result[0]['end'], 2.0)
        self.assertAlmostEqual(result[1]['start'], 5.0)
        self.assertAlmostEqual(result[1]['end'], 10.0)

    def test_duration_field_present(self):
        silences = [{'start': 3.0, 'end': 7.0}]
        result = invert_silences(silences, 10.0)
        for seg in result:
            self.assertIn('duration', seg)
            self.assertAlmostEqual(seg['duration'], seg['end'] - seg['start'])


if __name__ == '__main__':
    unittest.main()
