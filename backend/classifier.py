import pandas as pd
from transformers import pipeline
from utils import get_nowdate, savedf2, savetemp

classifier = pipeline(
    "zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
)


def get_class(article, candidate_labels, multi_label=False):
    results = classifier(article, candidate_labels, multi_label=multi_label)
    return results


def df2label(df, idcol, contentcol, candidate_labels, multi_label=False):
    artls = df[contentcol].tolist()
    urls = df[idcol].tolist()

    txtls = []
    idls = []

    for i, item in enumerate(zip(artls, urls)):
        article, url = item
        txtls.append(str(article))
        idls.append(url)
        mod = (i + 1) % 10
        if mod == 0 and i > 0:
            results = get_class(txtls, candidate_labels, multi_label)
            tempdf = pd.DataFrame({"result": results, "id": idls})
            tempdf["labels"] = tempdf["result"].apply(lambda x: x["labels"][:3])
            tempdf["scores"] = tempdf["result"].apply(lambda x: x["scores"][:3])
            savename = "templabel-" + str(i + 1)
            savetemp(tempdf, savename)

    results = get_class(txtls, candidate_labels, multi_label=False)
    tempdf = pd.DataFrame({"result": results, "id": idls})
    tempdf["labels"] = tempdf["result"].apply(lambda x: x["labels"][:3])
    tempdf["scores"] = tempdf["result"].apply(lambda x: x["scores"][:3])
    tempdf1 = tempdf[["id", "labels", "scores"]]
    savename = "csrc2label" + get_nowdate()
    savedf2(tempdf1, savename)
