import unittest

from rc_audio import get_transcript_for_segment


class TestGetTranscriptForSegment(unittest.TestCase):

    def test_overlapping_segments(self):
        transcript = [
            {"offsets": {"from": 0, "to": 2000}, "text": "First part"},
            {"offsets": {"from": 2000, "to": 4000}, "text": "Second part"},
            {"offsets": {"from": 4000, "to": 6000}, "text": "Third part"},
        ]
        text, indices = get_transcript_for_segment(transcript, 1.0, 3.0)
        self.assertIn("First part", text)
        self.assertIn("Second part", text)
        self.assertNotIn("Third part", text)
        self.assertEqual(indices, [0, 1])

    def test_no_overlap(self):
        transcript = [
            {"offsets": {"from": 0, "to": 1000}, "text": "Before"},
            {"offsets": {"from": 5000, "to": 6000}, "text": "After"},
        ]
        text, indices = get_transcript_for_segment(transcript, 2.0, 4.0)
        self.assertEqual(text, "")
        self.assertEqual(indices, [])


if __name__ == '__main__':
    unittest.main()
