import io
from typing import List, Union

import pandas as pd

# from classifier import df2label, get_class
from doc2text import convert_uploadfiles, docxconvertion

# from extractamount import df2amount
from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

# from locationanalysis import df2location
# from peopleanalysis import df2people

tempdir = "../data/penalty/csrc2/temp"

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


# @app.post("/classify")
# async def classify(
#     article: str,
#     candidate_labels: List[str] = Query(default=[]),
#     multi_label: bool = False,
# ):
#     return get_class(article, candidate_labels, multi_label)


# @app.post("/batchclassify")
# async def batchclassify(
#     candidate_labels: List[str] = Query(default=[]),
#     multi_label: bool = False,
#     # file: UploadFile = File(...),
#     idcol: str = "",
#     contentcol: str = "",
#     file: bytes = File(...),
# ):
#     file_obj = io.BytesIO(file)
#     df = pd.read_csv(file_obj)
#     resdf = df2label(df, idcol, contentcol, candidate_labels, multi_label)
#     return JSONResponse(content=resdf.to_json(orient="records"))


# @app.post("/amtanalysis")
# async def amtanalysis(idcol: str, contentcol: str, file: bytes = File(...)):
#     file_obj = io.BytesIO(file)
#     df = pd.read_csv(file_obj)
#     resdf = df2amount(df, idcol, contentcol)
#     return JSONResponse(content=resdf.to_json(orient="records"))


# @app.post("/locanalysis")
# async def locanalysis(
#     idcol: str, titlecol: str, contentcol: str, file: bytes = File(...)
# ):
#     file_obj = io.BytesIO(file)
#     df = pd.read_csv(file_obj)
#     resdf = df2location(df, idcol, titlecol, contentcol)
#     return JSONResponse(content=resdf.to_json(orient="records"))


# @app.post("/peopleanalysis")
# async def peopleanalysis(idcol: str, contentcol: str, file: bytes = File(...)):
#     file_obj = io.BytesIO(file)
#     df = pd.read_csv(file_obj)
#     resdf = df2people(df, idcol, contentcol)
#     return JSONResponse(content=resdf.to_json(orient="records"))


@app.get("/docxconvert")
async def docxconvert():
    docxconvertion(tempdir)
    return {"dirpath": tempdir}


@app.post("/convertuploadfiles")
async def convertuploadfiles(txtls: List[str] = Query(default=[]), dirpath: str = ""):
    resls = convert_uploadfiles(txtls, dirpath)
    return {"resls": resls}
