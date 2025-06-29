from typing import Union, List
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# from classifier import df2label, get_class
# from doc2text import convert_uploadfiles, docxconvertion, ofdconvertion

# from extractamount import df2amount

# from locationanalysis import df2location
# from peopleanalysis import df2people

tempdir = "../data/penalty/csrc2/temp"

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/summary")
def get_summary():
    """Get case summary statistics"""
    # Mock data for demonstration - replace with actual database queries
    return {
        "total": 1250,
        "byOrg": {
            "北京": 320,
            "上海": 280,
            "深圳": 210,
            "广州": 180,
            "杭州": 120,
            "其他": 140
        },
        "byMonth": {
            "2024-01": 95,
            "2024-02": 88,
            "2024-03": 102,
            "2024-04": 110,
            "2024-05": 98,
            "2024-06": 105,
            "2024-07": 115,
            "2024-08": 108,
            "2024-09": 112,
            "2024-10": 118,
            "2024-11": 125,
            "2024-12": 174
        }
    }


@app.get("/search")
def search_cases(
    keyword: str = Query(None),
    org: str = Query(None),
    page: int = Query(1),
    pageSize: int = Query(10),
    dateFrom: str = Query(None),
    dateTo: str = Query(None)
):
    """Search cases with filters"""
    # Mock data for demonstration - replace with actual database queries
    mock_cases = [
        {
            "id": "1",
            "title": "关于对某某公司信息披露违规的处罚决定",
            "date": "2024-01-15",
            "org": "北京",
            "type": "信息披露违规",
            "content": "某某公司未按规定披露重要信息..."
        },
        {
            "id": "2",
            "title": "关于对某某证券公司违规交易的处罚决定",
            "date": "2024-01-20",
            "org": "上海",
            "type": "违规交易",
            "content": "某某证券公司存在违规交易行为..."
        },
        {
            "id": "3",
            "title": "关于对某某基金公司违规操作的处罚决定",
            "date": "2024-02-01",
            "org": "深圳",
            "type": "违规操作",
            "content": "某某基金公司违规操作基金资产..."
        }
    ]
    
    # Simple filtering logic (replace with actual database queries)
    filtered_cases = mock_cases
    if keyword:
        filtered_cases = [case for case in filtered_cases if keyword in case["title"] or keyword in case["content"]]
    if org:
        filtered_cases = [case for case in filtered_cases if case["org"] == org]
    
    # Pagination
    start = (page - 1) * pageSize
    end = start + pageSize
    paginated_cases = filtered_cases[start:end]
    
    return {
        "data": paginated_cases,
        "total": len(filtered_cases)
    }


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


# @app.get("/docxconvert")
# async def docxconvert():
#     docxconvertion(tempdir)
#     return {"dirpath": tempdir}


# @app.post("/convertuploadfiles")
# async def convertuploadfiles(txtls: List[str] = Query(default=[]), dirpath: str = ""):
#     resls = convert_uploadfiles(txtls, dirpath)
#     return {"resls": resls}


# @app.get("/ofdconvert")
# async def ofdconvert():
#     ofdconvertion(tempdir)
#     return {"dirpath": tempdir}
