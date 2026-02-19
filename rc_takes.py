import re


def get_first_words(text, n=4):
    """Extract first n words from text, normalized"""
    words = re.findall(r'\b\w+\b', text.lower())
    return ' '.join(words[:n])


def detect_takes(intervals, min_matching_words=3):
    """
    Detect repeated takes in speech intervals.

    Each interval must have a 'text' key with transcript text.

    Returns: (removes, take_markers)
        removes: set of interval indices to remove
        take_markers: dict mapping kept idx to marker info
    """
    if not intervals:
        return set(), {}

    removes = set()
    take_markers = {}

    i = 0
    while i < len(intervals):
        text = intervals[i].get('text', '').strip()
        first_words = get_first_words(text, min_matching_words)

        if not first_words or len(first_words.split()) < min_matching_words:
            i += 1
            continue

        take_group = [i]
        skipped = []
        j = i + 1

        while j < len(intervals):
            next_text = intervals[j].get('text', '').strip()
            next_first = get_first_words(next_text, min_matching_words)
            if next_first == first_words or (
                len(next_first.split()) >= min_matching_words and
                next_first.split()[:min_matching_words] == first_words.split()[:min_matching_words]
            ):
                # Found another take — absorb any skipped filler
                take_group.extend(skipped)
                skipped = []
                take_group.append(j)
                j += 1
            elif len(next_first.split()) < min_matching_words:
                # Too short to match — possible filler between takes, skip for now
                skipped.append(j)
                j += 1
            else:
                break

        if len(take_group) > 1:
            for idx in take_group[:-1]:
                removes.add(idx)
            take_markers[take_group[-1]] = {
                'removed_count': len(take_group) - 1,
                'sample_text': first_words
            }
            i = j
        else:
            i += 1

    return removes, take_markers
