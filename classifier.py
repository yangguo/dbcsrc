from transformers import pipeline

classifier = pipeline(
    "zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
)


def get_class(article, candidate_labels, multi_label=False):
    results = classifier(article, candidate_labels, multi_label=multi_label)
    return results
