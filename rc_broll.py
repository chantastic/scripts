import re


def detect_proper_nouns(text):
    """Detect proper nouns for B-roll markers"""
    if not text:
        return []

    exclude = {'I', 'A', 'An', 'The', 'In', 'On', 'At', 'To', 'For', 'Of', 'And', 'Or', 'But',
               'My', 'Your', 'His', 'Her', 'Its', 'Our', 'Their', 'We', 'You', 'He', 'She', 'It',
               'They', 'What', 'When', 'Where', 'Why', 'How', 'This', 'That', 'These', 'Those',
               'Let', 'Now', 'So', 'Well', 'Just', 'Then', 'Here', 'There'}

    proper_nouns = set()
    multi_word_phrases = set()

    # Find multi-word capitalized phrases
    multi_word = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
    for phrase in multi_word:
        proper_nouns.add(phrase)
        multi_word_phrases.add(phrase)

    # Find mid-sentence capitalized words
    sentences = re.split(r'[.!?]\s+', text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        words = sentence.split()

        for i in range(1, len(words)):
            word = words[i]
            match = re.match(r'^([A-Z][a-z]+)', word)
            if match:
                cap_word = match.group(1)
                if len(cap_word) < 4:
                    continue
                if cap_word not in exclude:
                    is_part_of_phrase = any(cap_word in phrase for phrase in multi_word_phrases)
                    if not is_part_of_phrase:
                        proper_nouns.add(cap_word)

    return sorted(proper_nouns)
