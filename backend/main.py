from typing import Union, List
from fastapi import FastAPI, Query, HTTPException, File, UploadFile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Union
import pandas as pd
import json
import os
import io
from datetime import datetime

# Import your existing modules
try:
    from classifier import df2label, get_class
except ImportError:
    def get_class(*args, **kwargs):
        return {"labels": ["未分类"], "scores": [1.0]}
    def df2label(*args, **kwargs):
        return pd.DataFrame()

try:
    from doc2text import convert_uploadfiles, docxconvertion, ofdconvertion
except ImportError:
    def convert_uploadfiles(*args, **kwargs):
        return {"message": "Document conversion not available"}

try:
    from extractamount import df2amount
except ImportError:
    def df2amount(*args, **kwargs):
        return pd.DataFrame()

try:
    from locationanalysis import df2location
except ImportError:
    def df2location(*args, **kwargs):
        return pd.DataFrame()

try:
    from peopleanalysis import df2people
except ImportError:
    def df2people(*args, **kwargs):
        return pd.DataFrame()

tempdir = "../data/penalty/csrc2/temp"
pencsrc2 = "../data/penalty/csrc2"

# Import web crawling functions
from web_crawler import get_sumeventdf_backend, update_sumeventdf_backend, get_csrc2analysis, content_length_analysis, download_attachment



app = FastAPI(title="DBCSRC API", description="Case Analysis System API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class UpdateRequest(BaseModel):
    orgName: str
    startPage: int
    endPage: int

class ClassifyRequest(BaseModel):
    article: str
    candidate_labels: List[str]
    multi_label: bool = False

class AttachmentRequest(BaseModel):
    contentLength: int
    downloadFilter: str

class CaseSearchRequest(BaseModel):
    keyword: Optional[str] = None
    org: Optional[str] = None
    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None
    page: int = 1
    pageSize: int = 10

@app.get("/")
def read_root():
    return {"message": "DBCSRC API is running", "version": "1.0.0"}


@app.get("/summary")
def get_summary():
    """Get case summary statistics"""
    try:
        # Get actual data from the database
        df = get_csrc2analysis()
        
        if df.empty:
            return {
                "total": 0,
                "byOrg": {},
                "byMonth": {}
            }
        
        # Calculate total cases
        total = len(df)
        
        # Calculate statistics by organization
        by_org = {}
        if '机构' in df.columns:
            by_org = df['机构'].value_counts().to_dict()
        
        # Calculate statistics by month
        by_month = {}
        if '发文日期' in df.columns:
            try:
                # Convert to datetime and extract year-month
                df_copy = df.copy()
                df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'], errors='coerce')
                # Filter out invalid dates
                df_copy = df_copy.dropna(subset=['发文日期'])
                if not df_copy.empty:
                    df_copy['month'] = df_copy['发文日期'].dt.to_period('M').astype(str)
                    by_month = df_copy['month'].value_counts().sort_index().to_dict()
            except Exception as date_error:
                by_month = {}
        
        return {
            "total": total,
            "byOrg": by_org,
            "byMonth": by_month
        }
        
    except Exception as e:
        # Return empty data structure on error instead of mock data
        return {
            "total": 0,
            "byOrg": {},
            "byMonth": {}
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
    try:
        try:
            df = get_csrc2analysis()
        except Exception as db_error:
            # If database/file access fails, return empty result
            return {"data": [], "total": 0}
        
        if df.empty:
            return {"data": [], "total": 0}
        
        # Apply filters
        if keyword:
            mask = df['标题'].str.contains(keyword, na=False) | df['内容'].str.contains(keyword, na=False)
            df = df[mask]
        
        if org:
            df = df[df['机构'] == org]
        
        if dateFrom:
            df = df[pd.to_datetime(df['发文日期']) >= pd.to_datetime(dateFrom)]
        
        if dateTo:
            df = df[pd.to_datetime(df['发文日期']) <= pd.to_datetime(dateTo)]
        
        total = len(df)
        
        # Pagination
        start = (page - 1) * pageSize
        end = start + pageSize
        paginated_df = df.iloc[start:end]
        
        # Convert to list of dicts
        cases = []
        for _, row in paginated_df.iterrows():
            cases.append({
                "id": str(row.get('链接', '')),
                "title": row.get('标题', ''),
                "date": str(row.get('发文日期', '')),
                "org": row.get('机构', ''),
                "content": row.get('内容', ''),
                "penalty": row.get('处罚类型', ''),
                "amount": row.get('罚款金额', 0)
            })
        
        return {
            "data": cases,
            "total": total
        }
    except Exception as e:
        # Return empty result instead of 500 error
        return {"data": [], "total": 0}


@app.post("/update")
async def update_cases(request: UpdateRequest):
    """Update cases for specific organization"""
    try:
        # Validate input parameters
        if request.endPage - request.startPage > 50:
            return {
                "success": False,
                "count": 0,
                "message": "Page range too large. Maximum 50 pages per request to avoid timeout."
            }
        
        # Get case summary data using backend functions
        sumeventdf = get_sumeventdf_backend(request.orgName, request.startPage, request.endPage)
        
        # Update the database
        newsum = update_sumeventdf_backend(sumeventdf)
        
        return {
            "success": True,
            "count": len(newsum),
            "message": f"Successfully updated {len(newsum)} cases for {request.orgName}"
        }
    except Exception as e:
        return {
            "success": False,
            "count": 0,
            "message": f"Update failed: {str(e)}"
        }

@app.post("/classify")
def classify_text(request: ClassifyRequest):
    """Classify text using AI model"""
    try:
        result = get_class(request.article, request.candidate_labels, request.multi_label)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-classify")
def batch_classify(
    file: UploadFile = File(...),
    candidate_labels: List[str] = Query(default=[]),
    multi_label: bool = False,
    idcol: str = Query(...),
    contentcol: str = Query(...)
):
    """Batch classify cases from uploaded file"""
    try:
        # Read uploaded file
        contents = file.file.read()
        file_obj = io.BytesIO(contents)
        df = pd.read_csv(file_obj)
        
        # Perform batch classification
        result_df = df2label(df, idcol, contentcol, candidate_labels, multi_label)
        
        return result_df.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-attachments")
def analyze_attachments(request: AttachmentRequest):
    """Analyze case attachments"""
    try:
        result = content_length_analysis(request.contentLength, request.downloadFilter)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download-attachments")
def download_attachments():
    """Download case attachments"""
    try:
        result = download_attachment()
        return {"success": True, "message": "Attachments downloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/amount-analysis")
def amount_analysis(
    file: UploadFile = File(...),
    idcol: str = Query(...),
    contentcol: str = Query(...)
):
    """Analyze penalty amounts from uploaded file"""
    try:
        contents = file.file.read()
        file_obj = io.BytesIO(contents)
        df = pd.read_csv(file_obj)
        result_df = df2amount(df, idcol, contentcol)
        return result_df.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/location-analysis")
def location_analysis(
    file: UploadFile = File(...),
    idcol: str = Query(...),
    contentcol: str = Query(...)
):
    """Analyze locations from uploaded file"""
    try:
        contents = file.file.read()
        file_obj = io.BytesIO(contents)
        df = pd.read_csv(file_obj)
        result_df = df2location(df, idcol, contentcol)
        return result_df.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/people-analysis")
def people_analysis(
    file: UploadFile = File(...),
    idcol: str = Query(...),
    contentcol: str = Query(...)
):
    """Analyze people from uploaded file"""
    try:
        contents = file.file.read()
        file_obj = io.BytesIO(contents)
        df = pd.read_csv(file_obj)
        result_df = df2people(df, idcol, contentcol)
        return result_df.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert-documents")
def convert_documents(files: List[UploadFile] = File(...)):
    """Convert uploaded documents to text"""
    try:
        result = convert_uploadfiles(files)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
