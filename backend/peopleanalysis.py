import pandas as pd
from paddlenlp import Taskflow
from utils import savetemp


def text2schema(text, topic):
    schema = ["个人", "单位", "负责人"]  # Define the schema for entity extraction
    ie = Taskflow("information_extraction", schema=schema)
    txtls = []
    if text != "":
        result = ie(text)
        keyls = list(result[0].keys())
        if topic in keyls:
            rls = result[0][topic]
            for r in rls:
                txt = r["text"]
                txtls.append(txt)
    return txtls


def df2people(df, idcol, peoplecol):
    df1 = df[[idcol, peoplecol]]

    idls = []
    peoplels = []
    orgls = []
    start = 0
    for i in range(start, len(df1)):
        id = df1.iloc[i][idcol]
        content = df1.iloc[i][peoplecol]
        print(i)
        print(content)
        people = text2schema(str(content), "个人")
        org = text2schema(str(content), "单位")

        print(people)
        print(org)
        idls.append(id)
        peoplels.append(people)
        orgls.append(org)

        if (i + 1) % 10 == 0 and i > start:
            tempdf = pd.DataFrame({"id": idls, "peoplels": peoplels, "orgls": orgls})
            savename = "temppeople-" + str(i) + ".csv"
            savetemp(tempdf, savename)

    resdf = pd.DataFrame({"id": idls, "peoplels": peoplels, "orgls": orgls})
    resdf["org"] = resdf["orgls"].apply(lambda x: x[0] if len(x) > 0 else "")
    # savename = "temppeople-" + str(i)+'.csv'
    return resdf
