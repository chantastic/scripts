import unittest

from rc_broll import detect_proper_nouns


class TestDetectProperNouns(unittest.TestCase):

    def test_multiword_phrases(self):
        text = "I use Claude Code and Final Cut Pro for editing."
        result = detect_proper_nouns(text)
        self.assertIn("Claude Code", result)
        self.assertIn("Final Cut Pro", result)

    def test_filters_short_words(self):
        text = "Let me show you Cod and Mac tools."
        result = detect_proper_nouns(text)
        self.assertNotIn("Cod", result)
        self.assertNotIn("Mac", result)

    def test_filters_sentence_initial(self):
        text = "Let me show you Python. Now we can code."
        result = detect_proper_nouns(text)
        self.assertNotIn("Let", result)
        self.assertNotIn("Now", result)
        self.assertIn("Python", result)

    def test_empty_input(self):
        self.assertEqual(detect_proper_nouns(""), [])


if __name__ == '__main__':
    unittest.main()
