from io import BytesIO, StringIO
from typing import List, Union

import pandas as pd
from classifier import df2label, get_class
from doc2text import convert_uploadfiles, docxconvertion
from extractamount import df2amount
from fastapi import FastAPI, File, Query, UploadFile

tempdir = "../data/penalty/csrc2/temp"

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.post("/classify")
async def classify(
    article: str,
    candidate_labels: List[str] = Query(default=[]),
    multi_label: bool = False,
):
    return get_class(article, candidate_labels, multi_label)


@app.post("/batchclassify")
async def batchclassify(
    candidate_labels: List[str] = Query(default=[]),
    multi_label: bool = False,
    # file: UploadFile = File(...),
    idcol: str = "",
    contentcol: str = "",
    df_in: str = "",
):
    # contents = file.file.read()
    # s = str(contents, "utf-8")
    # buffer = StringIO(s)
    # df = pd.read_csv(buffer)
    df = pd.read_json(df_in)
    df2label(df, idcol, contentcol, candidate_labels, multi_label)
    # buffer.close()
    # file.file.close()
    # return {"filename": file.filename}


@app.post("/amtanalysis")
async def amtanalysis(idcol: str, contentcol: str, df_in: str):
    df = pd.read_json(df_in)
    df2amount(df, idcol, contentcol)


@app.get("/docxconvert")
async def docxconvert():
    docxconvertion(tempdir)
    return {"dirpath": tempdir}


@app.post("/convertuploadfiles")
async def convertuploadfiles(txtls: List[str] = Query(default=[]), dirpath: str = ""):
    resls = convert_uploadfiles(txtls, dirpath)
    return {"resls": resls}
