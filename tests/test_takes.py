import unittest

from rc_takes import get_first_words, detect_takes


class TestGetFirstWords(unittest.TestCase):

    def test_extracts_first_n_words(self):
        text = "Hello world this is a test"
        result = get_first_words(text, 3)
        self.assertEqual(result, "hello world this")

    def test_handles_punctuation(self):
        text = "Hello, world! How are you?"
        result = get_first_words(text, 3)
        self.assertEqual(result, "hello world how")

    def test_fewer_words_than_n(self):
        text = "Hello"
        result = get_first_words(text, 3)
        self.assertEqual(result, "hello")

    def test_empty_string(self):
        result = get_first_words("", 3)
        self.assertEqual(result, "")


class TestDetectTakes(unittest.TestCase):

    def test_detects_duplicate_takes(self):
        intervals = [
            {'text': 'Hello world test one', 'start': 0, 'end': 1},
            {'text': 'Hello world test two', 'start': 2, 'end': 3},
            {'text': 'Hello world test final', 'start': 4, 'end': 5},
            {'text': 'Different content here now', 'start': 6, 'end': 7},
        ]
        removes, markers = detect_takes(intervals, min_matching_words=2)
        self.assertIn(0, removes)
        self.assertIn(1, removes)
        self.assertNotIn(2, removes)
        self.assertNotIn(3, removes)
        self.assertEqual(markers[2]['removed_count'], 2)

    def test_empty_intervals(self):
        removes, markers = detect_takes([], min_matching_words=3)
        self.assertEqual(len(removes), 0)
        self.assertEqual(len(markers), 0)

    def test_no_duplicates(self):
        intervals = [
            {'text': 'First sentence about something', 'start': 0, 'end': 1},
            {'text': 'Second sentence about other', 'start': 2, 'end': 3},
            {'text': 'Third sentence entirely different', 'start': 4, 'end': 5},
        ]
        removes, markers = detect_takes(intervals, min_matching_words=3)
        self.assertEqual(len(removes), 0)

    def test_short_segments_skipped(self):
        intervals = [
            {'text': 'Hi', 'start': 0, 'end': 1},
            {'text': 'Hi', 'start': 2, 'end': 3},
            {'text': 'OK then goodbye', 'start': 4, 'end': 5},
        ]
        removes, markers = detect_takes(intervals, min_matching_words=3)
        self.assertEqual(len(removes), 0)

    def test_keeps_last_take(self):
        intervals = [
            {'text': 'Today we are going to talk', 'start': 0, 'end': 1},
            {'text': 'Today we are going to discuss', 'start': 2, 'end': 3},
        ]
        removes, markers = detect_takes(intervals, min_matching_words=3)
        self.assertIn(0, removes)
        self.assertNotIn(1, removes)

    def test_filler_between_takes(self):
        """Short filler segments between takes shouldn't break detection"""
        intervals = [
            {'text': 'Today we are going to talk about', 'start': 0, 'end': 2},
            {'text': 'um', 'start': 2.5, 'end': 3},
            {'text': 'Today we are going to discuss', 'start': 3.5, 'end': 5},
        ]
        removes, markers = detect_takes(intervals, min_matching_words=3)
        # All three should be removed except the last take
        self.assertIn(0, removes)
        self.assertIn(1, removes)  # filler absorbed
        self.assertNotIn(2, removes)

    def test_filler_not_absorbed_without_later_take(self):
        """Short segments after a take aren't removed if no subsequent take follows"""
        intervals = [
            {'text': 'Today we are going to talk about', 'start': 0, 'end': 2},
            {'text': 'um', 'start': 2.5, 'end': 3},
            {'text': 'Something completely different here', 'start': 3.5, 'end': 5},
        ]
        removes, markers = detect_takes(intervals, min_matching_words=3)
        self.assertEqual(len(removes), 0)

    def test_different_sentences_common_words(self):
        intervals = [
            {'text': 'The quick brown fox jumps', 'start': 0, 'end': 1},
            {'text': 'The quick brown dog sits', 'start': 2, 'end': 3},
        ]
        removes, markers = detect_takes(intervals, min_matching_words=4)
        # "the quick brown fox" != "the quick brown dog", so no takes detected
        self.assertEqual(len(removes), 0)


if __name__ == '__main__':
    unittest.main()
