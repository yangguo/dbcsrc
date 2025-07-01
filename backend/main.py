from typing import Union, List
from fastapi import FastAPI, Query, HTTPException, File, UploadFile, Request, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union, Any
import pandas as pd
import json
import os
import io
import logging
import time
import psutil
import shutil
from datetime import datetime
from html import escape
import re
from functools import wraps
import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security utilities
def sanitize_text_input(text: str) -> str:
    """Sanitize user text input to prevent XSS and injection attacks"""
    if not text:
        return ""
    # HTML escape
    text = escape(text)
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Limit length
    return text[:10000]  # Max 10k characters

# Rate limiting
class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[client_ip]) < self.max_requests:
            self.requests[client_ip].append(now)
            return True
        return False

# Global variables (will be initialized on startup)
rate_limiter = None
metrics = None
start_time = None

# Metrics collection
class Metrics:
    def __init__(self):
        self.request_count = defaultdict(int)
        self.request_duration = defaultdict(list)
        self.error_count = defaultdict(int)
        self.start_time = time.time()
    
    def record_request(self, endpoint: str, method: str, duration: float, status_code: int):
        key = f"{method}_{endpoint}"
        self.request_count[key] += 1
        self.request_duration[key].append(duration)
        
        if status_code >= 400:
            self.error_count[key] += 1
    
    def get_stats(self) -> dict:
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": uptime,
            "total_requests": sum(self.request_count.values()),
            "total_errors": sum(self.error_count.values()),
            "endpoints": dict(self.request_count),
            "error_rate": sum(self.error_count.values()) / max(sum(self.request_count.values()), 1)
        }

# Health check utilities
async def check_database_connection() -> bool:
    """Check if database is accessible"""
    try:
        # Add your database connection check here
        # For now, return True as placeholder
        return True
    except Exception:
        return False

async def check_external_apis() -> bool:
    """Check if external APIs are accessible"""
    try:
        # Add checks for OpenAI API, etc.
        return True
    except Exception:
        return False

def check_disk_space() -> dict:
    """Check available disk space"""
    try:
        usage = shutil.disk_usage(".")
        return {
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "usage_percent": round((usage.used / usage.total) * 100, 2)
        }
    except Exception:
        return {"error": "Unable to check disk space"}

def get_memory_usage() -> dict:
    """Get current memory usage"""
    try:
        memory = psutil.virtual_memory()
        return {
            "total_mb": round(memory.total / (1024**2), 2),
            "used_mb": round(memory.used / (1024**2), 2),
            "available_mb": round(memory.available / (1024**2), 2),
            "usage_percent": memory.percent
        }
    except Exception:
        return {"error": "Unable to check memory usage"}

# Configuration settings
class Settings:
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    mongo_url: str = os.getenv("MONGO_DB_URL", "")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
settings = Settings()

# Standardized response models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    count: Optional[int] = None
    error: Optional[str] = None

class SearchResponse(BaseModel):
    data: List[dict]
    total: int
    page: Optional[int] = None
    pageSize: Optional[int] = None

tempdir = "../data/penalty/csrc2/temp"
pencsrc2 = "../data/penalty/csrc2"

# Import web crawling functions
from web_crawler import get_sumeventdf_backend, update_sumeventdf_backend, get_csrc2analysis, content_length_analysis, download_attachment



app = FastAPI(
    title="DBCSRC API", 
    description="Enhanced Case Analysis System API with comprehensive logging, security, and monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    global rate_limiter, metrics, start_time
    start_time = time.time()
    rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
    metrics = Metrics()
    logger.info("DBCSRC API v1.0.0 started successfully")
    
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down DBCSRC API")

# Add CORS middleware with configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Rate limiting and metrics middleware
@app.middleware("http")
async def rate_limit_and_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host
    
    # Rate limiting check
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "message": "Rate limit exceeded. Please try again later.",
                "error": "Too many requests"
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Record metrics
    duration = time.time() - start_time
    metrics.record_request(
        endpoint=request.url.path,
        method=request.method,
        duration=duration,
        status_code=response.status_code
    )
    
    # Add performance headers
    response.headers["X-Process-Time"] = str(duration)
    response.headers["X-Request-ID"] = f"{int(start_time * 1000)}"
    
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception on {request.method} {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False,
            message="Internal server error",
            error="An unexpected error occurred"
        ).__dict__
    )

# Health check endpoints
@app.get("/health", response_model=APIResponse, tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return APIResponse(
        success=True,
        message="Service is healthy",
        data={"status": "healthy", "timestamp": time.time()}
    )

@app.get("/health/detailed", response_model=APIResponse, tags=["Health"])
async def detailed_health_check():
    """Detailed health check with system metrics"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "database": await check_database_connection(),
            "disk_space": check_disk_space(),
            "memory_usage": check_memory_usage(),
            "uptime": time.time() - start_time if 'start_time' in globals() else 0
        }
        
        # Check if any component is unhealthy
        is_healthy = all([
            health_status["database"]["status"] == "connected",
            health_status["disk_space"]["available_gb"] > 1.0,  # At least 1GB free
            health_status["memory_usage"]["percent"] < 90  # Less than 90% memory usage
        ])
        
        if not is_healthy:
            health_status["status"] = "degraded"
        
        return APIResponse(
            success=True,
            message="Health check completed",
            data=health_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return APIResponse(
            success=False,
            message="Health check failed",
            error=str(e)
        )

@app.get("/metrics", response_model=APIResponse, tags=["Monitoring"])
async def get_metrics():
    """Get application metrics"""
    try:
        return APIResponse(
            success=True,
            message="Metrics retrieved successfully",
            data=metrics.get_stats()
        )
    except Exception as e:
        logger.error(f"Failed to retrieve metrics: {str(e)}")
        return APIResponse(
            success=False,
            message="Failed to retrieve metrics",
            error=str(e)
        )

# Enhanced Pydantic models with validation
class UpdateRequest(BaseModel):
    orgName: str = Field(..., min_length=1, max_length=100, description="Organization name")
    startPage: int = Field(..., ge=1, le=1000, description="Starting page number")
    endPage: int = Field(..., ge=1, le=1000, description="Ending page number")
    
    @validator('endPage')
    def validate_page_range(cls, v, values):
        if 'startPage' in values and v < values['startPage']:
            raise ValueError('endPage must be >= startPage')
        if 'startPage' in values and v - values['startPage'] > 50:
            raise ValueError('Page range cannot exceed 50 pages')
        return v

class ClassifyRequest(BaseModel):
    article: str = Field(..., min_length=1, max_length=10000, description="Text to classify")
    candidate_labels: List[str] = Field(..., min_items=1, max_items=20, description="Classification labels")
    multi_label: bool = Field(default=False, description="Enable multi-label classification")

class AttachmentRequest(BaseModel):
    contentLength: int = Field(..., ge=0, description="Content length threshold")
    downloadFilter: str = Field(..., min_length=1, description="Download filter criteria")

class CaseSearchRequest(BaseModel):
    keyword: Optional[str] = Field(None, max_length=200, description="Search keyword")
    org: Optional[str] = Field(None, max_length=100, description="Organization filter")
    dateFrom: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    dateTo: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    page: int = Field(default=1, ge=1, le=1000, description="Page number")
    pageSize: int = Field(default=10, ge=1, le=100, description="Items per page")
    
    @validator('dateFrom', 'dateTo')
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v

@app.get("/")
def read_root():
    return {"message": "DBCSRC API is running", "version": "1.0.0"}


@app.get("/summary", response_model=APIResponse)
def get_summary():
    """Get case summary statistics"""
    try:
        logger.info("Fetching case summary statistics")
        # Get actual data from the database
        df = get_csrc2analysis()
        
        if df.empty:
            logger.warning("No data found in database")
            return APIResponse(
                success=True,
                message="No data available",
                data={
                    "total": 0,
                    "byOrg": {},
                    "byMonth": {}
                },
                count=0
            )
        
        # Calculate total cases
        total = len(df)
        logger.info(f"Processing {total} cases for summary")
        
        # Calculate statistics by organization
        by_org = {}
        if '机构' in df.columns:
            # Filter out empty strings and null values
            org_series = df['机构'].dropna()
            org_series = org_series[org_series.str.strip() != '']
            if not org_series.empty:
                by_org = org_series.value_counts().to_dict()
        
        # Calculate statistics by month
        by_month = {}
        if '发文日期' in df.columns:
            try:
                # Convert to datetime and extract year-month
                df_copy = df.copy()
                # Handle both string and date objects
                if df_copy['发文日期'].dtype == 'object':
                    # Check if it's already date objects
                    if hasattr(df_copy['发文日期'].iloc[0], 'year'):
                        # Already date objects, convert to datetime
                        df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'])
                    else:
                        # String dates, parse them
                        df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'], errors='coerce')
                else:
                    # Already datetime, keep as is
                    pass
                
                # Filter out invalid dates
                df_copy = df_copy.dropna(subset=['发文日期'])
                if not df_copy.empty:
                    df_copy['month'] = df_copy['发文日期'].dt.to_period('M').astype(str)
                    by_month = df_copy['month'].value_counts().sort_index().to_dict()
            except Exception as date_error:
                logger.warning(f"Date processing error: {date_error}")
                by_month = {}
        
        summary_data = {
            "total": total,
            "byOrg": by_org,
            "byMonth": by_month
        }
        
        logger.info(f"Successfully generated summary for {total} cases")
        return APIResponse(
            success=True,
            message=f"Summary generated successfully for {total} cases",
            data=summary_data,
            count=total
        )
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to generate summary",
            error=str(e),
            data={
                "total": 0,
                "byOrg": {},
                "byMonth": {}
            }
        )


@app.get("/search", response_model=SearchResponse)
def search_cases(
    keyword: str = Query(None, max_length=200),
    org: str = Query(None, max_length=100),
    page: int = Query(1, ge=1, le=1000),
    pageSize: int = Query(10, ge=1, le=100),
    dateFrom: str = Query(None),
    dateTo: str = Query(None)
):
    """Search cases with filters"""
    try:
        logger.info(f"Searching cases with filters: keyword={keyword}, org={org}, page={page}, pageSize={pageSize}")
        
        # Validate date formats
        if dateFrom:
            try:
                datetime.strptime(dateFrom, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="dateFrom must be in YYYY-MM-DD format")
        
        if dateTo:
            try:
                datetime.strptime(dateTo, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="dateTo must be in YYYY-MM-DD format")
        
        try:
            df = get_csrc2analysis()
        except Exception as db_error:
            logger.error(f"Database access error: {db_error}")
            return SearchResponse(data=[], total=0, page=page, pageSize=pageSize)
        
        if df.empty:
            logger.warning("No data found in database")
            return SearchResponse(data=[], total=0, page=page, pageSize=pageSize)
        
        original_count = len(df)
        logger.info(f"Starting search with {original_count} total cases")
        
        # Apply filters
        if keyword:
            mask = df['标题'].str.contains(keyword, na=False, case=False) | df['内容'].str.contains(keyword, na=False, case=False)
            df = df[mask]
            logger.info(f"After keyword filter: {len(df)} cases")
        
        if org:
            df = df[df['机构'] == org]
            logger.info(f"After organization filter: {len(df)} cases")
        
        if dateFrom:
            try:
                df = df[pd.to_datetime(df['发文日期'], errors='coerce') >= pd.to_datetime(dateFrom)]
                logger.info(f"After dateFrom filter: {len(df)} cases")
            except Exception as date_error:
                logger.warning(f"Date filtering error for dateFrom: {date_error}")
        
        if dateTo:
            try:
                df = df[pd.to_datetime(df['发文日期'], errors='coerce') <= pd.to_datetime(dateTo)]
                logger.info(f"After dateTo filter: {len(df)} cases")
            except Exception as date_error:
                logger.warning(f"Date filtering error for dateTo: {date_error}")
        
        total = len(df)
        
        # Pagination
        start = (page - 1) * pageSize
        end = start + pageSize
        paginated_df = df.iloc[start:end]
        
        # Convert to list of dicts
        cases = []
        for _, row in paginated_df.iterrows():
            # Extract name and docNumber from the combined field
            name_field = str(row.get('名称', ''))
            doc_field = str(row.get('文号', ''))
            
            cases.append({
                "id": str(row.get('链接', '')),
                "title": name_field,
                "name": name_field,
                "docNumber": doc_field,
                "date": str(row.get('发文日期', '')),
                "org": row.get('机构', ''),
                "content": row.get('内容', ''),
                "penalty": row.get('处罚类型', ''),
                "amount": row.get('罚款金额', 0)
            })
        
        logger.info(f"Search completed: returning {len(cases)} cases out of {total} total matches")
        return SearchResponse(
            data=cases,
            total=total,
            page=page,
            pageSize=pageSize
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return SearchResponse(data=[], total=0, page=page, pageSize=pageSize)


@app.post("/update", response_model=APIResponse)
async def update_cases(request: UpdateRequest):
    """Update cases for specific organization"""
    try:
        logger.info(f"Starting update for organization: {request.orgName}, pages {request.startPage}-{request.endPage}")
        
        # Get case summary data using backend functions
        logger.info(f"Fetching case data from pages {request.startPage} to {request.endPage}")
        sumeventdf = get_sumeventdf_backend(request.orgName, request.startPage, request.endPage)
        
        if sumeventdf.empty:
            logger.warning(f"No data found for {request.orgName} in specified page range")
            return APIResponse(
                success=True,
                message=f"No new cases found for {request.orgName} in pages {request.startPage}-{request.endPage}",
                count=0
            )
        
        # Update the database
        logger.info(f"Updating database with {len(sumeventdf)} cases")
        newsum = update_sumeventdf_backend(sumeventdf)
        
        logger.info(f"Successfully updated {len(newsum)} cases for {request.orgName}")
        return APIResponse(
            success=True,
            message=f"Successfully updated {len(newsum)} cases for {request.orgName}",
            count=len(newsum),
            data={"updatedCases": len(newsum), "totalFetched": len(sumeventdf)}
        )
        
    except Exception as e:
        logger.error(f"Update failed for {request.orgName}: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message=f"Update failed for {request.orgName}",
            error=str(e),
            count=0
        )

@app.post("/classify", response_model=APIResponse)
async def classify_text(request: ClassifyRequest):
    """Classify text using AI model with enhanced security"""
    try:
        # Sanitize input text
        sanitized_article = sanitize_text_input(request.article)
        
        logger.info(f"Starting classification for text (length: {len(sanitized_article)} chars)")
        
        # Validate sanitized input
        if not sanitized_article or len(sanitized_article.strip()) == 0:
            logger.warning("Empty text provided for classification")
            return APIResponse(
                success=False,
                message="Text cannot be empty",
                error="Invalid input"
            )
        
        result = get_class(sanitized_article, request.candidate_labels, request.multi_label)
        
        logger.info(f"Classification completed successfully: {result}")
        return APIResponse(
            success=True,
            message="Classification completed successfully",
            data={"classification": result}
        )
        
    except Exception as e:
        logger.error(f"Classification failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Classification failed",
            error=str(e)
        )

@app.post("/batch-classify", response_model=APIResponse)
async def batch_classify(
    file: UploadFile = File(...),
    candidate_labels: List[str] = Query(default=[]),
    multi_label: bool = False,
    idcol: str = Query(...),
    contentcol: str = Query(...)
):
    """Batch classify cases from uploaded file"""
    try:
        logger.info(f"Starting batch classification from file: {file.filename}")
        
        # Read uploaded file
        contents = file.file.read()
        file_obj = io.BytesIO(contents)
        df = pd.read_csv(file_obj)
        
        logger.info(f"Processing {len(df)} rows for batch classification")
        
        # Perform batch classification
        result_df = df2label(df, idcol, contentcol, candidate_labels, multi_label)
        
        logger.info(f"Batch classification completed successfully for {len(result_df)} records")
        return APIResponse(
            success=True,
            message=f"Batch classification completed for {len(result_df)} records",
            data={"results": result_df.to_dict('records')},
            count=len(result_df)
        )
        
    except Exception as e:
        logger.error(f"Batch classification failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Batch classification failed",
            error=str(e)
        )

@app.post("/analyze-attachments", response_model=APIResponse)
async def analyze_attachments(request: AttachmentRequest):
    """Analyze case attachments"""
    try:
        logger.info(f"Starting attachment analysis with contentLength={request.contentLength}, downloadFilter={request.downloadFilter}")
        
        result = content_length_analysis(request.contentLength, request.downloadFilter)
        
        logger.info("Attachment analysis completed successfully")
        return APIResponse(
            success=True,
            message="Attachment analysis completed successfully",
            data={"result": result}
        )
        
    except Exception as e:
        logger.error(f"Attachment analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Attachment analysis failed",
            error=str(e)
        )

@app.post("/download-attachments", response_model=APIResponse)
async def download_attachments(request: AttachmentRequest):
    """Download case attachments"""
    try:
        logger.info(f"Starting attachment download with contentLength={request.contentLength}, downloadFilter={request.downloadFilter}")
        
        result = download_attachment(request.contentLength, request.downloadFilter)
        
        logger.info("Attachment download completed successfully")
        return APIResponse(
            success=True,
            message="Attachment download completed successfully",
            data={"result": result}
        )
        
    except Exception as e:
        logger.error(f"Attachment download failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Attachment download failed",
            error=str(e)
        )

@app.post("/amount-analysis", response_model=APIResponse)
async def amount_analysis(
    file: UploadFile = File(...),
    idcol: str = Query(...),
    contentcol: str = Query(...)
):
    """Analyze penalty amounts from uploaded file"""
    try:
        logger.info(f"Starting amount analysis from file: {file.filename}")
        
        contents = file.file.read()
        file_obj = io.BytesIO(contents)
        df = pd.read_csv(file_obj)
        
        logger.info(f"Processing {len(df)} rows for amount analysis")
        result_df = df2amount(df, idcol, contentcol)
        
        logger.info(f"Amount analysis completed successfully for {len(result_df)} records")
        return APIResponse(
            success=True,
            message=f"Amount analysis completed for {len(result_df)} records",
            data={"results": result_df.to_dict('records')},
            count=len(result_df)
        )
        
    except Exception as e:
        logger.error(f"Amount analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Amount analysis failed",
            error=str(e)
        )

@app.post("/location-analysis", response_model=APIResponse)
async def location_analysis(
    file: UploadFile = File(...),
    idcol: str = Query(...),
    contentcol: str = Query(...)
):
    """Analyze locations from uploaded file"""
    try:
        logger.info(f"Starting location analysis from file: {file.filename}")
        
        contents = file.file.read()
        file_obj = io.BytesIO(contents)
        df = pd.read_csv(file_obj)
        
        logger.info(f"Processing {len(df)} rows for location analysis")
        result_df = df2location(df, idcol, contentcol)
        
        logger.info(f"Location analysis completed successfully for {len(result_df)} records")
        return APIResponse(
            success=True,
            message=f"Location analysis completed for {len(result_df)} records",
            data={"results": result_df.to_dict('records')},
            count=len(result_df)
        )
        
    except Exception as e:
        logger.error(f"Location analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Location analysis failed",
            error=str(e)
        )

@app.post("/people-analysis", response_model=APIResponse)
async def people_analysis(
    file: UploadFile = File(...),
    idcol: str = Query(...),
    contentcol: str = Query(...)
):
    """Analyze people from uploaded file"""
    try:
        logger.info(f"Starting people analysis from file: {file.filename}")
        
        contents = file.file.read()
        file_obj = io.BytesIO(contents)
        df = pd.read_csv(file_obj)
        
        logger.info(f"Processing {len(df)} rows for people analysis")
        result_df = df2people(df, idcol, contentcol)
        
        logger.info(f"People analysis completed successfully for {len(result_df)} records")
        return APIResponse(
            success=True,
            message=f"People analysis completed for {len(result_df)} records",
            data={"results": result_df.to_dict('records')},
            count=len(result_df)
        )
        
    except Exception as e:
        logger.error(f"People analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="People analysis failed",
            error=str(e)
        )

@app.post("/convert-documents", response_model=APIResponse)
async def convert_documents(files: List[UploadFile] = File(...)):
    """Convert uploaded documents to text"""
    try:
        logger.info(f"Starting document conversion for {len(files)} files")
        
        result = convert_uploadfiles(files)
        
        logger.info(f"Document conversion completed successfully for {len(files)} files")
        return APIResponse(
            success=True,
            message=f"Document conversion completed for {len(files)} files",
            data={"results": result},
            count=len(files)
        )
        
    except Exception as e:
        logger.error(f"Document conversion failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Document conversion failed",
            error=str(e)
        )

@app.post("/refresh-data", response_model=APIResponse)
async def refresh_data():
    """Refresh case data from database"""
    try:
        logger.info("Starting data refresh from database")
        
        # Refresh case data using get_csrc2analysis
        refreshed_cases = get_csrc2analysis()
        
        if refreshed_cases.empty:
            logger.warning("No cases found during data refresh")
            return APIResponse(
                success=True,
                message="Data refresh completed but no cases found",
                count=0
            )
        
        logger.info(f"Data refresh completed successfully with {len(refreshed_cases)} cases")
        return APIResponse(
            success=True,
            message=f"Successfully refreshed {len(refreshed_cases)} cases",
            count=len(refreshed_cases),
            data={"refreshedCases": len(refreshed_cases)}
        )
        
    except Exception as e:
        logger.error(f"Data refresh failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to refresh data",
            error=str(e),
            count=0
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
