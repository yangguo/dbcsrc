
from textrank4zh import TextRank4Keyword, TextRank4Sentence

# get summary of text
def get_summary(text):
    tr4s = TextRank4Sentence()
    tr4s.analyze(text=text, lower=True, source='all_filters')

    sumls = []
    for item in tr4s.get_key_sentences(num=3):
        sumls.append(item.sentence)
    summary = ''.join(sumls)
    return summary
