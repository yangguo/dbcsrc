import pandas as pd
from transformers import pipeline
from paddlenlp import Taskflow
from utils import get_nowdate, savedf2, savetemp

classifier = pipeline(
    "zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
)


def get_class(article, candidate_labels, multi_label=False):
    # results = classifier(article, candidate_labels, multi_label=multi_label)
    my_cls = Taskflow("zero_shot_text_classification", schema=candidate_labels)
    results=my_cls(article)
    print(results)
    print(results[0]['predictions'][0])
    return results[0]['predictions'][0]


def df2label(df, idcol, contentcol, candidate_labels, multi_label=False):
    artls = df[contentcol].tolist()
    urls = df[idcol].tolist()

    txtls = []
    idls = []
    labells=[]
    scorels=[]

    for i, item in enumerate(zip(artls, urls)):
        article, url = item
        results = get_class(article, candidate_labels, multi_label)
        label=results['label']
        score=results['score']
        txtls.append(str(article))
        idls.append(url)
        labells.append(label)
        scorels.append(score)
        mod = (i + 1) % 10
        if mod == 0 and i > 0:

            tempdf = pd.DataFrame({"label": labells,"score":scorels, "id": idls})
            # tempdf["labels"] = tempdf["result"].apply(lambda x: x["labels"][:3])
            # tempdf["scores"] = tempdf["result"].apply(lambda x: x["scores"][:3])
            # tempdf["label"] = tempdf["labels"].apply(lambda x: x[0])
            # tempdf["label"]=tempdf["result"].apply(lambda x: x[0]["label"])
            savename = "templabel-" + str(i + 1)
            savetemp(tempdf, savename)

    # results = get_class(txtls, candidate_labels, multi_label=False)
    # tempdf = pd.DataFrame({"result": results, "id": idls})
    # tempdf["labels"] = tempdf["result"].apply(lambda x: x["labels"][:3])
    # tempdf["scores"] = tempdf["result"].apply(lambda x: x["scores"][:3])
    # tempdf["label"] = tempdf["labels"].apply(lambda x: x[0])
    tempdf = pd.DataFrame({"label": labells,"score":scorels, "id": idls})
    # tempdf1 = tempdf[["id", "labels", "scores", "label"]]
    # savename = "csrc2label" + get_nowdate()
    # savedf2(tempdf1, savename)
    return tempdf
