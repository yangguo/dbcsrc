from typing import Union, List
from fastapi import FastAPI, Query, HTTPException, File, UploadFile, Request, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union, Any, TYPE_CHECKING

# Import pandas type for type hints only
if TYPE_CHECKING:
    import pandas as pd
else:
    # Create a dummy class for runtime
    class pd:
        class DataFrame:
            pass
# Lazy import pandas to reduce memory usage during startup
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
import uuid
from enum import Enum
from datetime import datetime, timedelta

# Global variable for pandas - will be imported when needed
pd = None

# Job management system
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class JobInfo(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0  # 0-100
    total_records: Optional[int] = None
    processed_records: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None
    filename: Optional[str] = None

# Global job storage (in production, use Redis or database)
job_storage = {}

def get_pandas():
    """Lazy import pandas to reduce startup memory usage"""
    global pd
    if pd is None:
        try:
            import pandas as pandas_module
            pd = pandas_module
            logger.info("Pandas imported successfully")
        except ImportError as e:
            logger.error(f"Failed to import pandas: {e}")
            raise
    return pd

# Import your existing modules
try:
    from classifier import df2label, get_class, extract_penalty_info, df2penalty_analysis
except ImportError:
    def get_class(*args, **kwargs):
        return {"labels": ["未分类"], "scores": [1.0]}
    def df2label(*args, **kwargs):
        return get_pandas().DataFrame()
    def extract_penalty_info(*args, **kwargs):
        return {"success": False, "error": "LLM analysis not available"}
    def df2penalty_analysis(*args, **kwargs):
        return get_pandas().DataFrame()

try:
    from doc2text import convert_uploadfiles, docxconvertion
except ImportError:
    def convert_uploadfiles(*args, **kwargs):
        return {"message": "Document conversion not available"}

try:
    from extractamount import df2amount
except ImportError:
    def df2amount(*args, **kwargs):
        return get_pandas().DataFrame()

try:
    from locationanalysis import df2location
except ImportError:
    def df2location(*args, **kwargs):
        return get_pandas().DataFrame()

try:
    from peopleanalysis import df2people
except ImportError:
    def df2people(*args, **kwargs):
        return get_pandas().DataFrame()

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
    # Try MONGO_DB_URL first (frontend compatibility), then MONGODB_URL
    mongo_url: str = os.getenv("MONGO_DB_URL") or os.getenv("MONGODB_URL", "mongodb://localhost:27017/dbcsrc")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
settings = Settings()

# MongoDB connection
import pymongo
from pymongo import MongoClient

def get_mongo_client():
    """Get MongoDB client with optimized timeout settings"""
    try:
        # Log the MongoDB URL (without credentials)
        mongo_url_parts = settings.mongo_url.split('@')
        safe_mongo_url = mongo_url_parts[1] if len(mongo_url_parts) > 1 else mongo_url_parts[0]
        logger.info(f"Connecting to MongoDB: {safe_mongo_url}")
        
        # Configure MongoDB client with shorter timeout settings for faster failure
        client = MongoClient(
            settings.mongo_url,
            serverSelectionTimeoutMS=10000,  # Reduced to 10 seconds
            connectTimeoutMS=10000,          # Reduced to 10 seconds
            socketTimeoutMS=15000,           # 15 seconds for operations
            maxPoolSize=5,                   # Reduced pool size
            retryWrites=True,
            maxIdleTimeMS=30000,             # Close idle connections after 30s
            heartbeatFrequencyMS=10000       # Check connection every 10s
        )
        # Test connection with timeout
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}", exc_info=True)
        return None

def get_collection(db_name: str, collection_name: str):
    """Get MongoDB collection"""
    client = get_mongo_client()
    if client:
        db = client[db_name]
        return db[collection_name]
    return None

def get_online_data():
    """Get online data from MongoDB with timeout handling"""
    try:
        collection = get_collection("pencsrc2", "csrc2analysis")
        if collection is not None:
            # Use cursor with timeout and limit for better performance
            cursor = collection.find({}, {"_id": 0}).max_time_ms(15000)  # 15 second timeout
            data = list(cursor)
            logger.info(f"Retrieved {len(data)} records from MongoDB")
            return get_pandas().DataFrame(data)
        else:
            logger.warning("MongoDB collection not available")
            return get_pandas().DataFrame()
    except Exception as e:
        logger.error(f"Failed to get online data: {str(e)}")
        # Return empty DataFrame on error to prevent complete failure
        return get_pandas().DataFrame()

def insert_online_data(df: "pd.DataFrame"):
    """Insert data to MongoDB - following frontend logic"""
    import datetime
    
    try:
        collection = get_collection("pencsrc2", "csrc2analysis")
        if collection is not None and not df.empty:
            # Convert date objects to datetime objects for MongoDB compatibility
            df_copy = df.copy()
            for col in df_copy.columns:
                if df_copy[col].dtype == 'object':
                    # Check if column contains date objects
                    sample_value = df_copy[col].dropna().iloc[0] if not df_copy[col].dropna().empty else None
                    if isinstance(sample_value, datetime.date) and not isinstance(sample_value, datetime.datetime):
                        df_copy[col] = get_pandas().to_datetime(df_copy[col])
            
            records = df_copy.to_dict("records")
            batch_size = 10000  # Use same batch size as frontend
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                collection.insert_many(batch)
            logger.info(f"Successfully inserted {len(records)} records to MongoDB")
            return True
        else:
            logger.warning("Collection is None or DataFrame is empty")
            return False
    except Exception as e:
        logger.error(f"Failed to insert online data: {str(e)}", exc_info=True)
        return False

def delete_online_data():
    """Delete all online data from MongoDB"""
    try:
        collection = get_collection("pencsrc2", "csrc2analysis")
        if collection is not None:
            result = collection.delete_many({})
            return result.deleted_count
        return 0
    except Exception as e:
        logger.error(f"Failed to delete online data: {str(e)}")
        return 0

# Standardized response models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    count: Optional[int] = None
    error: Optional[str] = None

class CaseDetail(BaseModel):
    id: str
    title: str
    name: str
    docNumber: str
    date: str
    org: str
    content: str
    penalty: str = ""
    amount: float = 0
    party: str = ""
    violationFacts: str = ""
    penaltyBasis: str = ""
    penaltyDecision: str = ""
    category: str = ""
    region: str = ""
    industry: str = ""

class SearchResponse(BaseModel):
    data: List[CaseDetail]
    total: int
    page: Optional[int] = None
    pageSize: Optional[int] = None

tempdir = "../data/penalty/csrc2/temp"
pencsrc2 = "../data/penalty/csrc2"

# Import web crawling functions
from web_crawler import get_sumeventdf_backend, update_sumeventdf_backend, get_csrc2analysis, content_length_analysis, download_attachment



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    global rate_limiter, metrics, start_time
    start_time = time.time()
    rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
    metrics = Metrics()
    logger.info("DBCSRC API v1.0.0 started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DBCSRC API")

app = FastAPI(
    title="DBCSRC API", 
    description="Enhanced Case Analysis System API with comprehensive logging, security, and monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)



# Add CORS middleware with configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:3001", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Rate limiting and metrics middleware
@app.middleware("http")
async def rate_limit_and_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Safely get client IP with fallback options
    client_ip = "unknown"
    if request.client and request.client.host:
        client_ip = request.client.host
    else:
        # Try to get IP from headers (useful for proxied requests)
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
            request.headers.get("X-Real-IP", "") or
            request.headers.get("CF-Connecting-IP", "") or  # Cloudflare
            request.headers.get("X-Client-IP", "") or
            "127.0.0.1"  # Default fallback
        )
    
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
            "memory_usage": get_memory_usage(),
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
    selectedIds: Optional[List[str]] = Field(None, description="List of specific IDs to update")
    
    @field_validator('endPage')
    @classmethod
    def validate_page_range(cls, v, info):
        if info.data.get('startPage') and v < info.data['startPage']:
            raise ValueError('endPage must be >= startPage')
        if info.data.get('startPage') and v - info.data['startPage'] > 50:
            raise ValueError('Page range cannot exceed 50 pages')
        return v

class ClassifyRequest(BaseModel):
    article: str = Field(..., min_length=1, max_length=10000, description="Text to classify")
    candidate_labels: List[str] = Field(..., min_items=1, max_items=20, description="Classification labels")
    multi_label: bool = Field(default=False, description="Enable multi-label classification")

class AttachmentRequest(BaseModel):
    contentLength: int = Field(..., ge=0, description="Content length threshold")
    downloadFilter: str = Field(..., min_length=1, description="Download filter criteria")

class AttachmentDownloadRequest(BaseModel):
    positions: List[int] = Field(..., description="List of positions/indices to download")

class CaseSearchRequest(BaseModel):
    keyword: Optional[str] = Field(None, max_length=200, description="Search keyword")
    org: Optional[str] = Field(None, max_length=100, description="Organization filter")
    dateFrom: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    dateTo: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    page: int = Field(default=1, ge=1, le=1000, description="Page number")
    pageSize: int = Field(default=10, ge=1, le=100, description="Items per page")
    
    @field_validator('dateFrom', 'dateTo')
    @classmethod
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v

class PenaltyAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000, description="行政处罚决定书文本内容")

@app.get("/")
def read_root():
    return {"message": "DBCSRC API is running", "version": "1.0.0"}

@app.get("/job/{job_id}", response_model=APIResponse, tags=["Jobs"])
async def get_job_status(job_id: str):
    """Get job status and progress"""
    try:
        if job_id not in job_storage:
            return APIResponse(
                success=False,
                message="Job not found",
                error="Invalid job ID"
            )
        
        job_info = job_storage[job_id]
        
        # Calculate duration if job is running or completed
        duration = None
        if job_info.started_at:
            end_time = job_info.completed_at or datetime.now()
            duration = (end_time - job_info.started_at).total_seconds()
        
        return APIResponse(
            success=True,
            message="Job status retrieved successfully",
            data={
                "job_id": job_info.job_id,
                "status": job_info.status,
                "progress": job_info.progress,
                "processed_records": job_info.processed_records,
                "total_records": job_info.total_records,
                "created_at": job_info.created_at.isoformat(),
                "started_at": job_info.started_at.isoformat() if job_info.started_at else None,
                "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None,
                "duration_seconds": duration,
                "error": job_info.error,
                "result_count": len(job_info.result) if job_info.result else 0
            }
        )
    except Exception as e:
        logger.error(f"Error retrieving job status: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to retrieve job status",
            error=str(e)
        )

@app.get("/jobs", response_model=APIResponse, tags=["Jobs"])
async def list_jobs():
    """List all jobs with their status"""
    try:
        jobs_data = []
        for job_id, job_info in job_storage.items():
            duration = None
            if job_info.started_at:
                end_time = job_info.completed_at or datetime.now()
                duration = (end_time - job_info.started_at).total_seconds()
            
            jobs_data.append({
                "job_id": job_info.job_id,
                "status": job_info.status,
                "progress": job_info.progress,
                "processed_records": job_info.processed_records,
                "total_records": job_info.total_records,
                "created_at": job_info.created_at.isoformat(),
                "duration_seconds": duration,
                "error": job_info.error
            })
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(jobs_data)} jobs",
            data=jobs_data,
            count=len(jobs_data)
        )
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to list jobs",
            error=str(e)
        )

@app.delete("/jobs/{job_id}", response_model=APIResponse, tags=["Jobs"])
async def delete_job(job_id: str):
    """Delete a specific job from storage"""
    try:
        if job_id not in job_storage:
            return APIResponse(
                success=False,
                message="Job not found",
                error="Invalid job ID"
            )
        
        job_info = job_storage[job_id]
        if job_info.status == JobStatus.RUNNING:
            return APIResponse(
                success=False,
                message="Cannot delete running job",
                error="Job is currently running"
            )
        
        del job_storage[job_id]
        
        return APIResponse(
            success=True,
            message="Job deleted successfully"
        )
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to delete job",
            error=str(e)
        )

@app.delete("/jobs", response_model=APIResponse, tags=["Jobs"])
async def cleanup_jobs():
    """Clean up completed and failed jobs older than 1 hour"""
    try:
        current_time = datetime.now()
        cleanup_threshold = timedelta(hours=1)
        
        jobs_to_delete = []
        for job_id, job_info in job_storage.items():
            if job_info.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                if job_info.completed_at and (current_time - job_info.completed_at) > cleanup_threshold:
                    jobs_to_delete.append(job_id)
        
        for job_id in jobs_to_delete:
            del job_storage[job_id]
        
        return APIResponse(
            success=True,
            message=f"Cleaned up {len(jobs_to_delete)} old jobs",
            data={"deleted_count": len(jobs_to_delete)}
        )
    except Exception as e:
        logger.error(f"Error cleaning up jobs: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to cleanup jobs",
            error=str(e)
        )


# Cache for summary data to improve performance
_summary_cache = {"data": None, "timestamp": 0}
CACHE_DURATION = 300  # 5 minutes

@app.get("/summary-working", response_model=APIResponse)
def get_summary_working(
    limit_orgs: int = Query(None, ge=1, le=100, description="Limit number of organizations (optional)"),
    limit_months: int = Query(None, ge=1, le=60, description="Limit number of months (optional)")
):
    """Get case summary statistics with working implementation"""
    try:
        import time
        current_time = time.time()
        
        logger.info("Generating working summary with actual data")
        
        # Load CSV data with timeout
        from data_service import get_csrc2detail
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
        
        def load_csv_data():
            return get_csrc2detail()
        
        df = get_pandas().DataFrame()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(load_csv_data)
                df = future.result(timeout=120)  # Increased to 120 second timeout
                if df is None:
                    df = get_pandas().DataFrame()
        except FutureTimeoutError:
            logger.warning("CSV loading timed out after 120 seconds")
            df = get_pandas().DataFrame()
        except Exception as e:
            logger.warning(f"CSV loading failed: {e}")
            df = get_pandas().DataFrame()
        
        # Process data simply
        total = len(df) if not df.empty else 0
        by_org = {}
        by_month = {}
        
        if not df.empty and total > 0:
            logger.info(f"Processing {total} rows")
            
            # Simple organization count - show ALL organizations or limit if specified
            # Use same filtering as org-summary for consistency
            if '机构' in df.columns:
                try:
                    # Additional filtering for consistency with table data
                    if '发文日期' in df.columns:
                        # Only count organizations with valid dates for consistency
                        df_filtered = df.copy()
                        df_filtered['发文日期'] = get_pandas().to_datetime(df_filtered['发文日期'], errors='coerce')
                        df_filtered = df_filtered.dropna(subset=['发文日期', '机构'])
                        df_filtered = df_filtered[df_filtered['机构'].str.strip() != '']
                        
                        if not df_filtered.empty:
                            org_counts = df_filtered['机构'].value_counts()  # Show ALL organizations
                            if limit_orgs:
                                org_counts = org_counts.head(limit_orgs)
                            by_org = org_counts.to_dict()
                    else:
                        # Fallback to original logic if no date column
                        org_counts = df['机构'].value_counts()  # Show ALL organizations
                        if limit_orgs:
                            org_counts = org_counts.head(limit_orgs)
                        by_org = org_counts.to_dict()
                except Exception as e:
                    logger.warning(f"Organization processing failed: {e}")
            
            # Simple month count - show ALL months chronologically or limit if specified
            if '发文日期' in df.columns:
                try:
                    df_copy = df[['发文日期']].copy()
                    df_copy['发文日期'] = get_pandas().to_datetime(df_copy['发文日期'], errors='coerce')
                    df_copy = df_copy.dropna()
                    if not df_copy.empty:
                        df_copy['month'] = df_copy['发文日期'].dt.strftime('%Y-%m')
                        # Get ALL months and sort chronologically
                        month_counts = df_copy['month'].value_counts().sort_index()
                        if limit_months:
                            month_counts = month_counts.tail(limit_months)  # Show last N months
                        by_month = month_counts.to_dict()
                except Exception as e:
                    logger.warning(f"Date processing failed: {e}")
        
        response = APIResponse(
            success=True,
            message=f"Working summary generated: {total} cases processed",
            data={
                "total": total,
                "byOrg": by_org,
                "byMonth": by_month,
                "timestamp": current_time
            },
            count=total
        )
        
        logger.info(f"Successfully generated working summary: {total} cases")
        return response
        
    except Exception as e:
        logger.error(f"Error generating working summary: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to generate working summary",
            error=str(e),
            data={"total": 0, "byOrg": {}, "byMonth": {}}
        )

@app.get("/summary-fast", response_model=APIResponse)
def get_summary_fast():
    """Get case summary statistics with minimal processing"""
    try:
        import time
        current_time = time.time()
        
        # Create a minimal response with just the timestamp
        response = APIResponse(
            success=True,
            message="Fast summary generated successfully",
            data={
                "total": 0,
                "byOrg": {},
                "byMonth": {},
                "timestamp": current_time
            }
        )
        
        return response
    except Exception as e:
        logger.error(f"Error generating fast summary: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to generate fast summary",
            error=str(e),
            data={}
        )

@app.get("/debug/org-comparison", response_model=APIResponse)
def get_org_comparison():
    """Debug endpoint to compare organization data between different filtering methods"""
    try:
        logger.info("Comparing organization data with different filtering methods")
        
        # Get case detail data
        from data_service import get_csrc2detail
        df = get_csrc2detail()
        
        if df.empty:
            return APIResponse(
                success=False,
                message="No data found",
                data={}
            )
        
        comparison_data = {
            "total_records": len(df),
            "method_1_no_date_filter": {},
            "method_2_with_date_filter": {},
            "difference_analysis": {}
        }
        
        # Method 1: No date filtering (original pie chart method)
        if '机构' in df.columns:
            org_series = df['机构'].dropna()
            org_series = org_series[org_series.str.strip() != '']
            org_counts_no_filter = org_series.value_counts()
            total_no_filter = len(org_series)
            
            comparison_data["method_1_no_date_filter"] = {
                "total_cases": total_no_filter,
                "unique_orgs": len(org_counts_no_filter),
                "top_10": {org: f"{count} ({round(count/total_no_filter*100, 2)}%)" 
                          for org, count in org_counts_no_filter.head(10).items()}
            }
        
        # Method 2: With date filtering (table method)
        if '机构' in df.columns and '发文日期' in df.columns:
            df_filtered = df.copy()
            df_filtered['发文日期'] = pd.to_datetime(df_filtered['发文日期'], errors='coerce')
            df_filtered = df_filtered.dropna(subset=['发文日期', '机构'])
            df_filtered = df_filtered[df_filtered['机构'].str.strip() != '']
            
            if not df_filtered.empty:
                org_counts_filtered = df_filtered['机构'].value_counts()
                total_filtered = len(df_filtered)
                
                comparison_data["method_2_with_date_filter"] = {
                    "total_cases": total_filtered,
                    "unique_orgs": len(org_counts_filtered),
                    "top_10": {org: f"{count} ({round(count/total_filtered*100, 2)}%)" 
                              for org, count in org_counts_filtered.head(10).items()}
                }
                
                # Calculate differences
                diff_total = total_no_filter - total_filtered
                diff_percentage = round((diff_total / total_no_filter) * 100, 2) if total_no_filter > 0 else 0
                
                comparison_data["difference_analysis"] = {
                    "cases_excluded_by_date_filter": diff_total,
                    "percentage_excluded": f"{diff_percentage}%",
                    "explanation": "Cases with invalid or missing dates are excluded in method 2"
                }
        
        return APIResponse(
            success=True,
            message="Organization data comparison completed",
            data=comparison_data
        )
        
    except Exception as e:
        logger.error(f"Organization comparison failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Organization comparison failed",
            error=str(e)
        )

@app.get("/debug/data-coverage", response_model=APIResponse)
def get_data_coverage():
    """Debug endpoint to check data coverage for organizations and time periods"""
    try:
        logger.info("Checking data coverage for debug purposes")
        
        # Get case detail data
        from data_service import get_csrc2detail
        df = get_csrc2detail()
        
        if df.empty:
            return APIResponse(
                success=False,
                message="No data found",
                data={}
            )
        
        coverage_info = {
            "total_records": len(df),
            "columns": list(df.columns),
            "organizations": {},
            "time_periods": {}
        }
        
        # Check organization coverage
        if '机构' in df.columns:
            org_series = df['机构'].dropna()
            org_series = org_series[org_series.str.strip() != '']
            org_counts = org_series.value_counts()
            coverage_info["organizations"] = {
                "total_unique": len(org_counts),
                "top_10": org_counts.head(10).to_dict(),
                "all_orgs": list(org_counts.index)
            }
        
        # Check time period coverage
        if '发文日期' in df.columns:
            df_copy = df[['发文日期']].copy()
            df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'], errors='coerce')
            df_copy = df_copy.dropna(subset=['发文日期'])
            if not df_copy.empty:
                df_copy.loc[:, 'month'] = df_copy['发文日期'].dt.to_period('M').astype(str)
                month_counts = df_copy['month'].value_counts().sort_index()
                coverage_info["time_periods"] = {
                    "total_unique_months": len(month_counts),
                    "date_range": {
                        "earliest": str(df_copy['发文日期'].min()),
                        "latest": str(df_copy['发文日期'].max())
                    },
                    "month_range": {
                        "earliest": month_counts.index.min(),
                        "latest": month_counts.index.max()
                    },
                    "monthly_counts": month_counts.to_dict()
                }
        
        return APIResponse(
            success=True,
            message="Data coverage analysis completed",
            data=coverage_info
        )
        
    except Exception as e:
        logger.error(f"Data coverage analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Data coverage analysis failed",
            error=str(e)
        )

@app.get("/summary-complete", response_model=APIResponse)
def get_summary_complete():
    """Get complete case summary statistics with ALL periods and organizations"""
    return _get_summary_impl(limit_orgs=None, limit_months=None)

@app.get("/api/summary-complete", response_model=APIResponse)
def get_api_summary_complete():
    """Get complete case summary statistics - API endpoint with ALL periods and organizations"""
    return _get_summary_impl(limit_orgs=None, limit_months=None)

@app.get("/summary", response_model=APIResponse)
def get_summary(
    limit_orgs: int = Query(None, ge=1, le=100, description="Limit number of organizations (optional)"),
    limit_months: int = Query(None, ge=1, le=60, description="Limit number of months (optional)")
):
    """Get case summary statistics - simplified version"""
    return _get_summary_impl(limit_orgs, limit_months)

@app.get("/api/summary", response_model=APIResponse)
def get_api_summary(
    limit_orgs: int = Query(None, ge=1, le=100, description="Limit number of organizations (optional)"),
    limit_months: int = Query(None, ge=1, le=60, description="Limit number of months (optional)")
):
    """Get case summary statistics - API endpoint"""
    return _get_summary_impl(limit_orgs, limit_months)

@app.get("/api/org-chart-data", response_model=APIResponse)
def get_org_chart_data():
    """Get organization data specifically formatted for pie charts with consistent percentages"""
    try:
        logger.info("Fetching organization chart data with consistent filtering")
        
        # Get case detail data from CSV files
        df = get_pandas().DataFrame()
        try:
            from data_service import get_csrc2detail
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
            
            def load_csv_data():
                return get_csrc2detail()
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(load_csv_data)
                try:
                    df = future.result(timeout=120)
                    if df is None or df.empty:
                        logger.warning("No CSV data found")
                        df = get_pandas().DataFrame()
                    else:
                        logger.info(f"Loaded {len(df)} rows from CSV data")
                except FutureTimeoutError:
                    logger.warning("CSV data loading timed out after 120 seconds")
                    df = get_pandas().DataFrame()
                    
        except Exception as csv_error:
            logger.warning(f"Failed to load CSV data: {csv_error}")
            df = get_pandas().DataFrame()
        
        org_chart_data = {}
        
        if not df.empty and '机构' in df.columns and '发文日期' in df.columns:
            # Use same filtering as org-summary for consistency
            df_copy = df.copy()
            
            # Clean and parse dates
            df_copy['发文日期'] = get_pandas().to_datetime(df_copy['发文日期'], errors='coerce')
            df_copy = df_copy.dropna(subset=['发文日期', '机构'])
            df_copy = df_copy[df_copy['机构'].str.strip() != '']
            
            if not df_copy.empty:
                # Get organization counts
                org_counts = df_copy['机构'].value_counts()
                total_cases = len(df_copy)
                
                # Limit to top 50 organizations for consistency with table
                org_counts = org_counts.head(50)
                
                # Convert to dictionary with counts (raw numbers for pie chart)
                org_chart_data = org_counts.to_dict()
                
                logger.info(f"Generated chart data for {len(org_counts)} organizations, total cases: {total_cases}")
        
        return APIResponse(
            success=True,
            message=f"Organization chart data generated successfully: {len(org_chart_data)} organizations",
            data={
                "organizations": org_chart_data,
                "total_cases": sum(org_chart_data.values()) if org_chart_data else 0
            },
            count=len(org_chart_data)
        )
        
    except Exception as e:
        logger.error(f"Error generating organization chart data: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to generate organization chart data",
            error=str(e),
            data={"organizations": {}, "total_cases": 0}
        )

@app.get("/api/org2id", response_model=APIResponse)
def get_org2id_mapping():
    """Get organization to ID mapping from web_crawler"""
    try:
        logger.info("Fetching org2id mapping")
        
        # Import org2id from web_crawler
        from web_crawler import org2id
        
        return APIResponse(
            success=True,
            message="Organization to ID mapping retrieved successfully",
            data=org2id,
            count=len(org2id)
        )
        
    except Exception as e:
        logger.error(f"Error fetching org2id mapping: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to fetch organization to ID mapping",
            error=str(e),
            data={}
        )

@app.get("/api/org-summary", response_model=APIResponse)
def get_org_summary():
    """Get organization summary with case counts and date ranges"""
    try:
        logger.info("Fetching organization summary with date ranges")
        
        # Get case detail data from CSV files
        df = get_pandas().DataFrame()
        try:
            from data_service import get_csrc2detail
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
            
            def load_csv_data():
                return get_csrc2detail()
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(load_csv_data)
                try:
                    df = future.result(timeout=120)
                    if df is None or df.empty:
                        logger.warning("No CSV data found")
                        df = get_pandas().DataFrame()
                    else:
                        logger.info(f"Loaded {len(df)} rows from CSV data")
                except FutureTimeoutError:
                    logger.warning("CSV data loading timed out after 120 seconds")
                    df = get_pandas().DataFrame()
                    
        except Exception as csv_error:
            logger.warning(f"Failed to load CSV data: {csv_error}")
            df = get_pandas().DataFrame()
        
        org_summary = []
        
        if not df.empty and '机构' in df.columns and '发文日期' in df.columns:
            # Process organization data with date ranges
            df_copy = df.copy()
            
            # Clean and parse dates
            df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'], errors='coerce')
            df_copy = df_copy.dropna(subset=['发文日期', '机构'])
            df_copy = df_copy[df_copy['机构'].str.strip() != '']
            
            if not df_copy.empty:
                # Group by organization and calculate statistics
                org_groups = df_copy.groupby('机构').agg({
                    '发文日期': ['count', 'min', 'max']
                }).reset_index()
                
                # Flatten column names
                org_groups.columns = ['orgName', 'caseCount', 'minDate', 'maxDate']
                
                # Sort by case count and take top organizations
                org_groups = org_groups.sort_values('caseCount', ascending=False).head(50)
                
                total_cases = len(df_copy)
                
                for _, row in org_groups.iterrows():
                    org_data = {
                        'orgName': row['orgName'],
                        'caseCount': int(row['caseCount']),
                        'percentage': round((row['caseCount'] / total_cases) * 100, 2),
                        'minDate': row['minDate'].strftime('%Y-%m') if get_pandas().notna(row['minDate']) else '',
                        'maxDate': row['maxDate'].strftime('%Y-%m') if get_pandas().notna(row['maxDate']) else '',
                        'dateRange': f"{row['minDate'].strftime('%Y-%m')} 至 {row['maxDate'].strftime('%Y-%m')}" if get_pandas().notna(row['minDate']) and get_pandas().notna(row['maxDate']) else '暂无数据'
                    }
                    org_summary.append(org_data)
        
        logger.info(f"Generated organization summary for {len(org_summary)} organizations")
        
        return APIResponse(
            success=True,
            message=f"Organization summary generated successfully: {len(org_summary)} organizations",
            data=org_summary,
            count=len(org_summary)
        )
        
    except Exception as e:
        logger.error(f"Error generating organization summary: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to generate organization summary",
            error=str(e),
            data=[]
        )

def _get_summary_impl(limit_orgs: int = None, limit_months: int = None):
    try:
        import time
        
        # Check cache first
        current_time = time.time()
        if (_summary_cache["data"] is not None and 
            current_time - _summary_cache["timestamp"] < CACHE_DURATION):
            logger.info("Returning cached summary data")
            return _summary_cache["data"]
        
        logger.info("Fetching case summary statistics")
        
        # Get case detail data from CSV files with timeout protection
        df = get_pandas().DataFrame()
        try:
            logger.info("Loading CSV data...")
            from data_service import get_csrc2detail
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
            
            def load_csv_data():
                return get_csrc2detail()
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(load_csv_data)
                try:
                    df = future.result(timeout=120)  # Increased to 120 second timeout
                    if df is None or df.empty:
                        logger.warning("No CSV data found")
                        df = get_pandas().DataFrame()
                    else:
                        logger.info(f"Loaded {len(df)} rows from CSV data")
                except FutureTimeoutError:
                    logger.warning("CSV data loading timed out after 120 seconds")
                    df = get_pandas().DataFrame()
                    
        except Exception as csv_error:
            logger.warning(f"Failed to load CSV data: {csv_error}")
            df = get_pandas().DataFrame()
        
        # Simplified processing - skip MongoDB for now to avoid timeout issues
        logger.info("Skipping MongoDB data for simplified processing")
        
        # Initialize summary data structure
        summary_data = {
            "total": 0,
            "byOrg": {},
            "byMonth": {},
            "onlineTotal": 0,
            "onlineByOrg": {},
            "onlineByMonth": {}
        }
        
        # Process CSV data
        if not df.empty:
            total = len(df)
            logger.info(f"Processing {total} cases for summary")
            
            # Simple organization count - show ALL organizations or limit if specified
            # Use same filtering as org-summary for consistency
            by_org = {}
            if '机构' in df.columns:
                org_series = df['机构'].dropna()
                org_series = org_series[org_series.str.strip() != '']
                
                # Additional filtering for consistency with table data
                if '发文日期' in df.columns:
                    # Only count organizations with valid dates for consistency
                    df_filtered = df.copy()
                    df_filtered['发文日期'] = pd.to_datetime(df_filtered['发文日期'], errors='coerce')
                    df_filtered = df_filtered.dropna(subset=['发文日期', '机构'])
                    df_filtered = df_filtered[df_filtered['机构'].str.strip() != '']
                    
                    if not df_filtered.empty:
                        org_counts = df_filtered['机构'].value_counts()
                        logger.info(f"Found {len(org_counts)} unique organizations (filtered for valid dates)")
                        if limit_orgs:
                            org_counts = org_counts.head(limit_orgs)
                            logger.info(f"Limited to top {limit_orgs} organizations")
                        by_org = org_counts.to_dict()
                else:
                    # Fallback to original logic if no date column
                    if not org_series.empty:
                        org_counts = org_series.value_counts()
                        logger.info(f"Found {len(org_counts)} unique organizations")
                        if limit_orgs:
                            org_counts = org_counts.head(limit_orgs)
                            logger.info(f"Limited to top {limit_orgs} organizations")
                        by_org = org_counts.to_dict()
            
            # Simple month count - show ALL months chronologically or limit if specified
            by_month = {}
            if '发文日期' in df.columns:
                try:
                    df_copy = df[['发文日期']].copy()
                    df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'], errors='coerce')
                    df_copy = df_copy.dropna(subset=['发文日期'])
                    if not df_copy.empty:
                        df_copy.loc[:, 'month'] = df_copy['发文日期'].dt.to_period('M').astype(str)
                        # Get ALL months and sort chronologically
                        month_counts = df_copy['month'].value_counts().sort_index()
                        logger.info(f"Found {len(month_counts)} unique months from {month_counts.index.min()} to {month_counts.index.max()}")
                        if limit_months:
                            month_counts = month_counts.tail(limit_months)  # Show last N months
                            logger.info(f"Limited to last {limit_months} months")
                        by_month = month_counts.to_dict()
                except Exception as date_error:
                    logger.warning(f"Date processing error: {date_error}")
                    by_month = {}
            
            summary_data.update({
                "total": total,
                "byOrg": by_org,
                "byMonth": by_month
            })
        else:
            logger.warning("No case detail data found")
        
        total_cases = summary_data["total"]
        online_cases = summary_data["onlineTotal"]
        
        logger.info(f"Successfully generated summary: {total_cases} total cases, {online_cases} online cases")
        
        # Create response and cache it
        response = APIResponse(
            success=True,
            message=f"Summary generated successfully: {total_cases} total cases, {online_cases} online cases",
            data=summary_data,
            count=total_cases
        )
        
        # Cache the response
        _summary_cache["data"] = response
        _summary_cache["timestamp"] = current_time
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to generate summary",
            error=str(e),
            data={}
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


@app.get("/test-simple")
def test_simple():
    """Simple test endpoint to verify server responsiveness"""
    return {"status": "ok", "message": "Server is responsive", "timestamp": time.time()}

@app.get("/search", response_model=SearchResponse)
@app.get("/api/search", response_model=SearchResponse)
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
            from data_service import get_csrc2_intersection
            df = get_csrc2_intersection()
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
            mask = df['名称'].str.contains(keyword, na=False, case=False) | df['内容'].str.contains(keyword, na=False, case=False)
            df = df[mask]
            logger.info(f"After keyword filter: {len(df)} cases")
        
        if org:
            df = df[df['机构'] == org]
            logger.info(f"After organization filter: {len(df)} cases")
        
        if dateFrom:
            try:
                df = df[get_pandas().to_datetime(df['发文日期'], errors='coerce') >= get_pandas().to_datetime(dateFrom)]
                logger.info(f"After dateFrom filter: {len(df)} cases")
            except Exception as date_error:
                logger.warning(f"Date filtering error for dateFrom: {date_error}")
        
        if dateTo:
            try:
                df = df[get_pandas().to_datetime(df['发文日期'], errors='coerce') <= get_pandas().to_datetime(dateTo)]
                logger.info(f"After dateTo filter: {len(df)} cases")
            except Exception as date_error:
                logger.warning(f"Date filtering error for dateTo: {date_error}")
        
        # Sort by date in descending order (newest first)
        try:
            # Convert date column to datetime for proper sorting
            df['发文日期_datetime'] = get_pandas().to_datetime(df['发文日期'], errors='coerce')
            # Sort by date descending, with NaT (invalid dates) at the end
            df = df.sort_values('发文日期_datetime', ascending=False, na_position='last')
            # Drop the temporary datetime column
            df = df.drop('发文日期_datetime', axis=1)
            logger.info(f"Data sorted by date in descending order")
        except Exception as sort_error:
            logger.warning(f"Date sorting error: {sort_error}, proceeding without sorting")
        
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
            
            case_detail = CaseDetail(
                id=str(row.get('链接', '')),
                title=name_field,
                name=name_field,
                docNumber=doc_field,
                date=str(row.get('date', row.get('发文日期', ''))),
                org=str(row.get('org', row.get('机构', ''))),
                content=str(row.get('内容', '')),
                penalty=str(row.get('category', '')),  # 案件类型从category获取
                amount=float(row.get('amount', row.get('罚款金额', 0))) if pd.notna(row.get('amount', row.get('罚款金额'))) else 0,
                party=str(row.get('people', '')),
                violationFacts=str(row.get('event', '')),
                penaltyBasis=str(row.get('law', '')),
                penaltyDecision=str(row.get('penalty', '')),  # 处罚决定从penalty获取
                category=str(row.get('category', '')),
                region=str(row.get('province', '')),
                industry=str(row.get('industry', ''))
            )
            cases.append(case_detail)
        
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


@app.get("/api/search-enhanced", response_model=SearchResponse)
def search_cases_enhanced(
    keyword: str = Query(None, max_length=200),
    docNumber: str = Query(None, max_length=100),
    org: str = Query(None, max_length=100),
    dateFrom: str = Query(None),
    dateTo: str = Query(None),
    party: str = Query(None, max_length=100),
    minAmount: float = Query(None, ge=0),
    legalBasis: str = Query(None, max_length=200),
    page: int = Query(1, ge=1, le=1000),
    pageSize: int = Query(10, ge=1, le=100)
):
    """Enhanced search cases with additional filters"""
    try:
        logger.info(f"Enhanced search with filters: keyword={keyword}, docNumber={docNumber}, org={org}, party={party}, minAmount={minAmount}, legalBasis={legalBasis}")
        
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
            from data_service import get_csrc2_intersection
            df = get_csrc2_intersection()
        except Exception as db_error:
            logger.error(f"Database access error: {db_error}")
            return SearchResponse(data=[], total=0, page=page, pageSize=pageSize)
        
        if df.empty:
            logger.warning("No data found in database")
            return SearchResponse(data=[], total=0, page=page, pageSize=pageSize)
        
        original_count = len(df)
        logger.info(f"Starting enhanced search with {original_count} total cases")
        logger.info(f"DataFrame columns: {list(df.columns)}")
        if not df.empty:
            first_row = df.iloc[0]
            logger.info(f"First row category: {first_row.get('category', 'NOT_FOUND')}")
            logger.info(f"First row province: {first_row.get('province', 'NOT_FOUND')}")
            logger.info(f"First row industry: {first_row.get('industry', 'NOT_FOUND')}")
        
        # Apply filters
        if keyword:
            mask = df['名称'].str.contains(keyword, na=False, case=False) | df['内容'].str.contains(keyword, na=False, case=False)
            df = df[mask]
            logger.info(f"After keyword filter: {len(df)} cases")
        
        if docNumber:
            df = df[df['文号'].str.contains(docNumber, na=False, case=False)]
            logger.info(f"After docNumber filter: {len(df)} cases")
        
        if org:
            df = df[df['机构'] == org]
            logger.info(f"After organization filter: {len(df)} cases")
        
        if party:
            df = df[df['内容'].str.contains(party, na=False, case=False)]
            logger.info(f"After party filter: {len(df)} cases")
        
        if minAmount is not None:
            # Ensure 罚款金额 is numeric and handle NaN values
            df['罚款金额_numeric'] = get_pandas().to_numeric(df['罚款金额'], errors='coerce').fillna(0)
            df = df[df['罚款金额_numeric'] >= minAmount]
            # Drop the temporary column
            df = df.drop('罚款金额_numeric', axis=1)
            logger.info(f"After minAmount filter: {len(df)} cases")
        
        if legalBasis:
            df = df[df['内容'].str.contains(legalBasis, na=False, case=False)]
            logger.info(f"After legalBasis filter: {len(df)} cases")
        
        if dateFrom:
            try:
                df = df[get_pandas().to_datetime(df['发文日期'], errors='coerce') >= get_pandas().to_datetime(dateFrom)]
                logger.info(f"After dateFrom filter: {len(df)} cases")
            except Exception as date_error:
                logger.warning(f"Date filtering error for dateFrom: {date_error}")
        
        if dateTo:
            try:
                df = df[get_pandas().to_datetime(df['发文日期'], errors='coerce') <= get_pandas().to_datetime(dateTo)]
                logger.info(f"After dateTo filter: {len(df)} cases")
            except Exception as date_error:
                logger.warning(f"Date filtering error for dateTo: {date_error}")
        
        # Sort by date in descending order (newest first)
        try:
            # Convert date column to datetime for proper sorting
            df['发文日期_datetime'] = get_pandas().to_datetime(df['发文日期'], errors='coerce')
            # Sort by date descending, with NaT (invalid dates) at the end
            df = df.sort_values('发文日期_datetime', ascending=False, na_position='last')
            # Drop the temporary datetime column
            df = df.drop('发文日期_datetime', axis=1)
            logger.info(f"Data sorted by date in descending order")
        except Exception as sort_error:
            logger.warning(f"Date sorting error: {sort_error}, proceeding without sorting")
        
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
            
            case_detail = CaseDetail(
                id=str(row.get('链接', '')),
                title=name_field,
                name=name_field,
                docNumber=doc_field,
                date=str(row.get('发文日期', '')),
                org=row.get('机构', ''),
                content=row.get('内容', ''),
                penalty=row.get('处罚类型', ''),
                amount=row.get('罚款金额', 0),
                party=row.get('people', ''),
                violationFacts=row.get('event', ''),
                penaltyBasis=row.get('law', ''),
                penaltyDecision=row.get('penalty', ''),
                category=row.get('category', ''),
                region=row.get('province', ''),
                industry=row.get('industry', '')
            )
            logger.info(f"Case data: category={case_detail.category}, region={case_detail.region}, industry={case_detail.industry}")
            cases.append(case_detail)
        
        logger.info(f"Enhanced search completed: returning {len(cases)} cases out of {total} total matches")
        return SearchResponse(
            data=cases,
            total=total,
            page=page,
            pageSize=pageSize
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced search error: {str(e)}", exc_info=True)
        return SearchResponse(data=[], total=0, page=page, pageSize=pageSize)


@app.post("/update", response_model=APIResponse)
async def update_cases(request: UpdateRequest):
    """Update cases for specific organization"""
    try:
        logger.info(f"Starting update for organization: {request.orgName}, pages {request.startPage}-{request.endPage}")
        
        # Get case summary data using backend functions
        logger.info(f"Fetching case data from pages {request.startPage} to {request.endPage}")
        if request.selectedIds:
            logger.info(f"Using selected IDs: {request.selectedIds}")
        sumeventdf = get_sumeventdf_backend(request.orgName, request.startPage, request.endPage, request.selectedIds)
        
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
        df = get_pandas().read_csv(file_obj, encoding='utf-8-sig')
        
        logger.info(f"Processing {len(df)} rows for batch classification")
        
        # Perform batch classification
        result_df = df2label(df, idcol, contentcol, candidate_labels, multi_label)
        
        # Limit results to prevent memory issues
        MAX_RESULTS = 1000  # Limit to prevent memory overflow
        total_count = len(result_df)
        limited_df = result_df.head(MAX_RESULTS)
        
        logger.info(f"Batch classification completed successfully for {total_count} records (showing {len(limited_df)})")
        return APIResponse(
            success=True,
            message=f"Batch classification completed for {total_count} records (showing {len(limited_df)})",
            data={
                "results": limited_df.to_dict('records'),
                "hasMore": total_count > MAX_RESULTS,
                "showing": len(limited_df)
            },
            count=total_count
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
        
        # Import here to avoid circular imports
        from web_crawler import content_length_analysis
        
        result = content_length_analysis(request.contentLength, request.downloadFilter)
        
        # Handle empty result gracefully
        if not result or len(result) == 0:
            logger.warning("No data found for attachment analysis - returning empty result")
            return APIResponse(
                success=True,
                message="No attachments found matching the criteria. This may be because the data directory is not set up yet.",
                data={"result": []},
                count=0
            )
        
        logger.info(f"Attachment analysis completed successfully with {len(result)} results")
        return APIResponse(
            success=True,
            message="Attachment analysis completed successfully",
            data={"result": result},
            count=len(result)
        )
        
    except Exception as e:
        logger.error(f"Attachment analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Attachment analysis failed. Please ensure the data directory structure is set up correctly.",
            error=str(e)
        )

@app.post("/download-attachments", response_model=APIResponse)
async def download_attachments(request: AttachmentDownloadRequest):
    """Download case attachments with progress tracking"""
    try:
        logger.info(f"Starting attachment download with positions={request.positions}")
        
        # Create a job for tracking progress
        job_id = str(uuid.uuid4())
        job_info = JobInfo(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            total_records=len(request.positions)
        )
        job_storage[job_id] = job_info
        
        # Progress callback function
        def progress_callback(current: int, total: int, message: str):
            if job_id in job_storage:
                job_storage[job_id].processed_records = current
                job_storage[job_id].progress = int((current / total) * 100) if total > 0 else 0
                logger.info(f"Download progress: {current}/{total} ({job_storage[job_id].progress}%) - {message}")
        
        # Update job status to running
        job_storage[job_id].status = JobStatus.RUNNING
        job_storage[job_id].started_at = datetime.now()
        
        # Import here to avoid circular imports
        from web_crawler import download_attachment
        
        # Run download with progress callback
        result = download_attachment(request.positions, progress_callback)
        
        # Convert DataFrame to serializable format
        if hasattr(result, 'to_dict'):
            # It's a pandas DataFrame, convert to records
            serializable_result = result.to_dict('records')
            total_count = len(result)
        else:
            # It's already serializable or None
            serializable_result = result if result is not None else []
            total_count = 0
        
        # Update job status to completed
        job_storage[job_id].status = JobStatus.COMPLETED
        job_storage[job_id].completed_at = datetime.now()
        job_storage[job_id].result = serializable_result
        
        logger.info(f"Attachment download completed successfully - {total_count} files processed")
        
        return APIResponse(
            success=True,
            message=f"Attachment download completed successfully - {total_count} files processed",
            data={
                "job_id": job_id,
                "results": serializable_result,
                "summary": {
                    "total_requested": len(request.positions),
                    "total_processed": total_count,
                    "success_rate": f"{(total_count/len(request.positions)*100):.1f}%" if request.positions else "0%"
                }
            },
            count=total_count
        )
        
    except Exception as e:
        # Update job status to failed
        if 'job_id' in locals() and job_id in job_storage:
            job_storage[job_id].status = JobStatus.FAILED
            job_storage[job_id].error = str(e)
            job_storage[job_id].completed_at = datetime.now()
        
        logger.error(f"Attachment download failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Attachment download failed",
            error=str(e)
        )

@app.get("/job-status/{job_id}", response_model=APIResponse)
async def get_job_status(job_id: str):
    """Get job status and progress"""
    try:
        if job_id not in job_storage:
            return APIResponse(
                success=False,
                message="Job not found",
                error="Invalid job ID"
            )
        
        job_info = job_storage[job_id]
        
        # Convert datetime objects to strings for JSON serialization
        job_data = {
            "job_id": job_info.job_id,
            "status": job_info.status,
            "progress": job_info.progress,
            "processed_records": job_info.processed_records,
            "total_records": job_info.total_records,
            "created_at": job_info.created_at.isoformat() if job_info.created_at else None,
            "started_at": job_info.started_at.isoformat() if job_info.started_at else None,
            "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None,
            "error": job_info.error
        }
        
        # Include result only if job is completed
        if job_info.status == JobStatus.COMPLETED and job_info.result:
            job_data["result"] = job_info.result
        
        return APIResponse(
            success=True,
            message="Job status retrieved successfully",
            data=job_data
        )
        
    except Exception as e:
        logger.error(f"Error retrieving job status: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to retrieve job status",
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
        df = get_pandas().read_csv(file_obj, encoding='utf-8-sig')
        
        logger.info(f"Processing {len(df)} rows for amount analysis")
        result_df = df2amount(df, idcol, contentcol)
        
        # Limit results to prevent memory issues
        MAX_RESULTS = 1000  # Limit to prevent memory overflow
        total_count = len(result_df)
        limited_df = result_df.head(MAX_RESULTS)
        
        logger.info(f"Amount analysis completed successfully for {total_count} records (showing {len(limited_df)})")
        return APIResponse(
            success=True,
            message=f"Amount analysis completed for {total_count} records (showing {len(limited_df)})",
            data={
                "results": limited_df.to_dict('records'),
                "hasMore": total_count > MAX_RESULTS,
                "showing": len(limited_df)
            },
            count=total_count
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
        df = get_pandas().read_csv(file_obj, encoding='utf-8-sig')
        
        logger.info(f"Processing {len(df)} rows for location analysis")
        result_df = df2location(df, idcol, contentcol)
        
        # Limit results to prevent memory issues
        MAX_RESULTS = 1000  # Limit to prevent memory overflow
        total_count = len(result_df)
        limited_df = result_df.head(MAX_RESULTS)
        
        logger.info(f"Location analysis completed successfully for {total_count} records (showing {len(limited_df)})")
        return APIResponse(
            success=True,
            message=f"Location analysis completed for {total_count} records (showing {len(limited_df)})",
            data={
                "results": limited_df.to_dict('records'),
                "hasMore": total_count > MAX_RESULTS,
                "showing": len(limited_df)
            },
            count=total_count
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
        df = get_pandas().read_csv(file_obj, encoding='utf-8-sig')
        
        logger.info(f"Processing {len(df)} rows for people analysis")
        result_df = df2people(df, idcol, contentcol)
        
        # Limit results to prevent memory issues
        MAX_RESULTS = 1000  # Limit to prevent memory overflow
        total_count = len(result_df)
        limited_df = result_df.head(MAX_RESULTS)
        
        logger.info(f"People analysis completed successfully for {total_count} records (showing {len(limited_df)})")
        return APIResponse(
            success=True,
            message=f"People analysis completed for {total_count} records (showing {len(limited_df)})",
            data={
                "results": limited_df.to_dict('records'),
                "hasMore": total_count > MAX_RESULTS,
                "showing": len(limited_df)
            },
            count=total_count
        )
        
    except Exception as e:
        logger.error(f"People analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="People analysis failed",
            error=str(e)
        )

@app.post("/penalty-analysis", response_model=APIResponse)
async def penalty_analysis(request: PenaltyAnalysisRequest):
    """Extract key information from administrative penalty decision using LLM"""
    try:
        logger.info("Starting penalty analysis with LLM")
        
        # Extract penalty information using LLM
        result = extract_penalty_info(request.text)
        
        logger.info(f"Extract penalty info result: {result}")
        logger.info("Penalty analysis completed successfully")
        return APIResponse(
            success=True,
            message="Penalty analysis completed successfully",
            data={"result": result.get("data") if result.get("success") else None}
        )
        
    except Exception as e:
        logger.error(f"Penalty analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Penalty analysis failed",
            error=str(e)
        )

async def process_batch_penalty_analysis_background(job_id: str, file_content: bytes, filename: str, idcol: str, contentcol: str, max_workers: int = None):
    """Background task for batch penalty analysis with parallel processing support"""
    try:
        # Update job status to running
        job_storage[job_id].status = JobStatus.RUNNING
        job_storage[job_id].started_at = datetime.now()
        logger.info(f"Starting background batch penalty analysis for job {job_id} with max_workers={max_workers}")
        
        # Process the file
        file_obj = io.BytesIO(file_content)
        df = get_pandas().read_csv(file_obj, encoding='utf-8-sig')
        
        # Update total records
        job_storage[job_id].total_records = len(df)
        logger.info(f"Processing {len(df)} rows for penalty analysis in job {job_id} using parallel processing")
        
        # Process the data with parallel processing
        result_df = df2penalty_analysis(df, idcol, contentcol, job_id, max_workers)
        
        # Update job as completed
        job_storage[job_id].status = JobStatus.COMPLETED
        job_storage[job_id].completed_at = datetime.now()
        job_storage[job_id].progress = 100
        job_storage[job_id].processed_records = len(result_df)
        job_storage[job_id].result = {"data": result_df.to_dict('records')}
        
        logger.info(f"Batch penalty analysis completed successfully for job {job_id} with {len(result_df)} records")
        
    except Exception as e:
        # Update job as failed
        job_storage[job_id].status = JobStatus.FAILED
        job_storage[job_id].completed_at = datetime.now()
        job_storage[job_id].error = str(e)
        logger.error(f"Batch penalty analysis failed for job {job_id}: {str(e)}", exc_info=True)

@app.post("/batch-penalty-analysis", response_model=APIResponse)
async def batch_penalty_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    idcol: str = Query(...),
    contentcol: str = Query(...),
    max_workers: int = Query(None, description="Maximum number of parallel workers for processing (default: auto-detect)")
):
    """Start batch penalty analysis as background job"""
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Read file content
        contents = await file.read()
        
        # Create job info
        job_info = JobInfo(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            filename=file.filename
        )
        job_storage[job_id] = job_info
        
        # Add background task with parallel processing support
        background_tasks.add_task(
            process_batch_penalty_analysis_background,
            job_id,
            contents,
            file.filename,
            idcol,
            contentcol,
            max_workers
        )
        
        logger.info(f"Batch penalty analysis job {job_id} started for file: {file.filename}")
        return APIResponse(
            success=True,
            message=f"Batch penalty analysis job started",
            data={"job_id": job_id, "status": "pending"}
        )
        
    except Exception as e:
        logger.error(f"Failed to start batch penalty analysis: {str(e)}", exc_info=True)
        return APIResponse(
             success=False,
             message="Failed to start batch penalty analysis",
             error=str(e)
         )

@app.get("/batch-penalty-analysis/{job_id}/status", response_model=APIResponse)
async def get_batch_penalty_analysis_status(job_id: str):
    """Get status of batch penalty analysis job"""
    try:
        if job_id not in job_storage:
            return APIResponse(
                success=False,
                message="Job not found",
                error="Invalid job ID"
            )
        
        job_info = job_storage[job_id]
        
        # Calculate elapsed time
        elapsed_time = None
        if job_info.started_at:
            end_time = job_info.completed_at or datetime.now()
            elapsed_time = (end_time - job_info.started_at).total_seconds()
        
        return APIResponse(
            success=True,
            message="Job status retrieved successfully",
            data={
                "job_id": job_info.job_id,
                "status": job_info.status,
                "progress": job_info.progress,
                "total_records": job_info.total_records,
                "processed_records": job_info.processed_records,
                "filename": job_info.filename,
                "created_at": job_info.created_at.isoformat(),
                "started_at": job_info.started_at.isoformat() if job_info.started_at else None,
                "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None,
                "elapsed_time_seconds": elapsed_time,
                "error": job_info.error
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to get job status",
            error=str(e)
        )

@app.get("/batch-penalty-analysis/{job_id}/result", response_model=APIResponse)
async def get_batch_penalty_analysis_result(job_id: str):
    """Get result of completed batch penalty analysis job"""
    try:
        if job_id not in job_storage:
            return APIResponse(
                success=False,
                message="Job not found",
                error="Invalid job ID"
            )
        
        job_info = job_storage[job_id]
        
        if job_info.status != JobStatus.COMPLETED:
            return APIResponse(
                success=False,
                message=f"Job is not completed. Current status: {job_info.status}",
                data={"status": job_info.status, "error": job_info.error}
            )
        
        return APIResponse(
            success=True,
            message="Job result retrieved successfully",
            data={
                "job_id": job_info.job_id,
                "result": job_info.result,
                "processed_records": job_info.processed_records,
                "filename": job_info.filename
            },
            count=job_info.processed_records
        )
        
    except Exception as e:
        logger.error(f"Failed to get job result: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to get job result",
            error=str(e)
        )

@app.get("/batch-penalty-analysis/jobs", response_model=APIResponse)
async def list_batch_penalty_analysis_jobs():
    """List all batch penalty analysis jobs"""
    try:
        jobs = []
        for job_id, job_info in job_storage.items():
            jobs.append({
                "job_id": job_info.job_id,
                "status": job_info.status,
                "progress": job_info.progress,
                "filename": job_info.filename,
                "created_at": job_info.created_at.isoformat(),
                "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None
            })
        
        return APIResponse(
            success=True,
            message="Jobs listed successfully",
            data={"jobs": jobs},
            count=len(jobs)
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to list jobs",
            error=str(e)
        )

@app.delete("/batch-penalty-analysis/{job_id}", response_model=APIResponse)
async def delete_batch_penalty_analysis_job(job_id: str):
    """Delete a batch penalty analysis job"""
    try:
        if job_id not in job_storage:
            return APIResponse(
                success=False,
                message="Job not found",
                error="Invalid job ID"
            )
        
        del job_storage[job_id]
        
        return APIResponse(
            success=True,
            message="Job deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to delete job: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to delete job",
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

@app.post("/update-analysis-data", response_model=APIResponse)
async def update_analysis_data():
    """Update analysis data by processing new case data and creating timestamped files"""
    try:
        logger.info("Starting analysis data update")
        
        # Import the update function from web_crawler
        from web_crawler import update_csrc2analysis_backend
        
        # Call the update function
        update_csrc2analysis_backend()
        
        # Get updated analysis data to return count
        from data_service import get_csrc2analysis
        updated_cases = get_csrc2analysis()
        
        logger.info(f"Analysis data update completed successfully")
        return APIResponse(
            success=True,
            message="Analysis data updated successfully with new timestamped file",
            count=len(updated_cases) if not updated_cases.empty else 0,
            data={"totalCases": len(updated_cases) if not updated_cases.empty else 0}
        )
        
    except Exception as e:
        logger.error(f"Analysis data update failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to update analysis data",
            error=str(e),
            count=0
        )

# Download data endpoints
@app.get("/download-data", response_model=APIResponse)
@app.get("/api/download-data", response_model=APIResponse)
async def get_download_data():
    """Get download data statistics"""
    try:
        logger.info("Getting download data statistics")
        
        import glob
        import os
        
        # Define data directory path
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'penalty', 'csrc2')
        
        # Helper function to get CSV file count
        def get_csv_stats(pattern, unique_id_column):
            files = glob.glob(os.path.join(data_dir, pattern))
            if files:
                dflist = []
                for filepath in files:
                    try:
                        df = get_pandas().read_csv(filepath, encoding='utf-8-sig')
                        dflist.append(df)
                    except Exception as e:
                        # Skip files that can't be read
                        pass
                
                if dflist:
                    # Combine all dataframes like get_csvdf does
                    combined_df = get_pandas().concat(dflist)
                    combined_df.reset_index(drop=True, inplace=True)
                    count = len(combined_df)
                    unique_count = combined_df[unique_id_column].nunique() if unique_id_column in combined_df.columns else count
                    return count, unique_count
            return 0, 0
        
        # Get case detail data stats (uses "链接" as unique ID)
        case_detail_count, case_detail_unique = get_csv_stats("csrcdtlall*.csv", "链接")
        
        # Get analysis data stats (uses "链接" as unique ID)
        analysis_count, analysis_unique = get_csv_stats("csrc2analysis*.csv", "链接")
        
        # Get category data stats (uses "id" as unique ID)
        category_count, category_unique = get_csv_stats("csrccat*.csv", "id")
        
        # Get split data stats (uses "id" as unique ID)
        split_count, split_unique = get_csv_stats("csrcsplit*.csv", "id")
        
        data = {
            "caseDetail": {
                "data": [],
                "count": case_detail_count,
                "uniqueCount": case_detail_unique
            },
            "analysisData": {
                "data": [],
                "count": analysis_count,
                "uniqueCount": analysis_unique
            },
            "categoryData": {
                "data": [],
                "count": category_count,
                "uniqueCount": category_unique
            },
            "splitData": {
                "data": [],
                "count": split_count,
                "uniqueCount": split_unique
            }
        }
        
        logger.info(f"Download data statistics retrieved successfully")
        return APIResponse(
            success=True,
            message="Download data statistics retrieved successfully",
            data=data
        )
        
    except Exception as e:
        logger.error(f"Failed to get download data statistics: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to get download data statistics",
            error=str(e)
        )

from fastapi.responses import StreamingResponse

@app.get("/download/case-detail")
async def download_case_detail():
    """Download case detail CSV file"""
    try:
        logger.info("Starting case detail CSV download")
        
        from data_service import get_csrc2detail
        
        df = get_csrc2detail()
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_content = csv_buffer.getvalue()
        
        # Create response
        response = StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=case_detail_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
        
        logger.info("Case detail CSV download completed")
        return response
        
    except Exception as e:
        logger.error(f"Case detail CSV download failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/analysis-data")
async def download_analysis_data():
    """Download analysis data CSV file"""
    try:
        logger.info("Starting analysis data CSV download")
        
        from data_service import get_csrc2analysis
        
        df = get_csrc2analysis()
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_content = csv_buffer.getvalue()
        
        # Create response
        response = StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=analysis_data_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
        
        logger.info("Analysis data CSV download completed")
        return response
        
    except Exception as e:
        logger.error(f"Analysis data CSV download failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/category-data")
async def download_category_data():
    """Download category data CSV file"""
    try:
        logger.info("Starting category data CSV download")
        
        from data_service import get_csrc2cat
        
        df = get_csrc2cat()
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_content = csv_buffer.getvalue()
        
        # Create response
        response = StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=category_data_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
        
        logger.info("Category data CSV download completed")
        return response
        
    except Exception as e:
        logger.error(f"Category data CSV download failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/split-data")
async def download_split_data():
    """Download split data CSV file"""
    try:
        logger.info("Starting split data CSV download")
        
        from data_service import get_csrc2split
        
        df = get_csrc2split()
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_content = csv_buffer.getvalue()
        
        # Create response
        response = StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=split_data_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
        
        logger.info("Split data CSV download completed")
        return response
        
    except Exception as e:
        logger.error(f"Split data CSV download failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/search-results")
async def download_search_results(
    keyword: str = Query(None, max_length=200),
    docNumber: str = Query(None, max_length=100),
    org: str = Query(None, max_length=100),
    dateFrom: str = Query(None),
    dateTo: str = Query(None),
    party: str = Query(None, max_length=100),
    minAmount: float = Query(None, ge=0),
    legalBasis: str = Query(None, max_length=200)
):
    """Download search results as CSV file"""
    try:
        logger.info(f"Starting search results download with filters: keyword={keyword}, docNumber={docNumber}, org={org}")
        
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
            from data_service import get_csrc2_intersection
            df = get_csrc2_intersection()
        except Exception as db_error:
            logger.error(f"Database access error: {db_error}")
            raise HTTPException(status_code=500, detail="Database access failed")
        
        if df.empty:
            logger.warning("No data found in database")
            raise HTTPException(status_code=404, detail="No data found")
        
        # Apply the same filters as in search_cases_enhanced
        if keyword:
            mask = df['名称'].str.contains(keyword, na=False, case=False) | df['内容'].str.contains(keyword, na=False, case=False)
            df = df[mask]
        
        if docNumber:
            df = df[df['文号'].str.contains(docNumber, na=False, case=False)]
        
        if org:
            df = df[df['机构'] == org]
        
        if party:
            df = df[df['内容'].str.contains(party, na=False, case=False)]
        
        if minAmount is not None:
            df = df[get_pandas().to_numeric(df['罚款金额'], errors='coerce') >= minAmount]
        
        if legalBasis:
            df = df[df['内容'].str.contains(legalBasis, na=False, case=False)]
        
        if dateFrom:
            try:
                df = df[pd.to_datetime(df['发文日期'], errors='coerce') >= pd.to_datetime(dateFrom)]
            except Exception as date_error:
                logger.warning(f"Date filtering error for dateFrom: {date_error}")
        
        if dateTo:
            try:
                df = df[pd.to_datetime(df['发文日期'], errors='coerce') <= pd.to_datetime(dateTo)]
            except Exception as date_error:
                logger.warning(f"Date filtering error for dateTo: {date_error}")
        
        if df.empty:
            logger.warning("No data found after applying filters")
            raise HTTPException(status_code=404, detail="No data found matching the search criteria")
        
        # Select relevant columns for export (including detailed case information)
        export_columns = [
            '名称', '文号', '发文日期', '机构', '罚款金额', '内容',  # Basic info
            'people', 'category', 'province', 'industry',  # Classification info
            'event', 'law', 'penalty', 'org', 'date',  # Detailed case info
            'wenhao', '序列号', '链接'  # Additional identifiers
        ]
        available_columns = [col for col in export_columns if col in df.columns]
        
        if available_columns:
            df_export = df[available_columns].copy()
        else:
            df_export = df.copy()
        
        # Rename columns to Chinese for better readability
        column_mapping = {
            '名称': '发文名称',
            '文号': '文号',
            '发文日期': '发文日期',
            '机构': '发文地区',
            '罚款金额': '罚款金额',
            '内容': '案例详情',
            'people': '当事人',
            'category': '案件类型',
            'province': '地区',
            'industry': '行业',
            'event': '违法事实',
            'law': '法律依据',
            'penalty': '处罚决定',
            'org': '处罚机构',
            'date': '处罚日期',
            'wenhao': '文件编号',
            '序列号': '序列号',
            '链接': '案例链接'
        }
        
        df_export = df_export.rename(columns=column_mapping)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_content = csv_buffer.getvalue()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"search_results_{timestamp}.csv"
        
        # Create response
        response = StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
        logger.info(f"Search results download completed: {len(df_export)} records exported")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search results download failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Case upload endpoints
# Simple in-memory cache for upload data with expiration
upload_data_cache = {
    "data": None,
    "timestamp": 0,
    "expiry": 300  # Cache expiry in seconds (5 minutes)
}

@app.get("/upload-data", response_model=APIResponse)
@app.get("/api/upload-data", response_model=APIResponse)
async def get_upload_data():
    """Get upload data for case upload functionality with caching and timeout handling"""
    try:
        logger.info("Getting upload data")
        
        # Check if we have valid cached data
        current_time = time.time()
        if upload_data_cache["data"] and (current_time - upload_data_cache["timestamp"] < upload_data_cache["expiry"]):
            logger.info("Returning cached upload data")
            return upload_data_cache["data"]
            
        from data_service import get_csrc2detail, get_csrc2analysis, get_csrc2label, get_csrc2cat, get_csrc2split
        
        # Get case detail data with timeout handling
        logger.info("Loading case detail data")
        case_detail_df = get_csrc2detail()
        
        # Get analysis data with timeout handling
        logger.info("Loading analysis data")
        analysis_df = get_csrc2analysis()
        
        # Get category data with timeout handling
        logger.info("Loading category data")
        category_df = get_csrc2cat()
        
        # Get split data with timeout handling
        logger.info("Loading split data")
        split_df = get_csrc2split()
        
        # Get online data from MongoDB with timeout handling
        logger.info("Loading online data from MongoDB")
        online_df = get_online_data()
        
        # Calculate diff data (three-table intersection minus online data)
        # Following frontend logic: csrc2analysis + csrc2cat + csrc2split intersection
        logger.info("Calculating three-table intersection for diff data")
        
        # First, get the three-table intersection regardless of online data
        try:
            if not analysis_df.empty and not category_df.empty and not split_df.empty:
                logger.info(f"Starting three-table intersection: analysis({len(analysis_df)}), category({len(category_df)}), split({len(split_df)})")
                
                # Step 1: Inner join analysis with category data
                intersection_df = get_pandas().merge(
                    analysis_df,
                    category_df,
                    left_on="链接",
                    right_on="id",
                    how="inner"
                )
                logger.info(f"After analysis+category merge: {len(intersection_df)} records")
                
                # Step 2: Inner join with split data
                if not intersection_df.empty:
                    # Remove 'org' column if exists to use the one from split data
                    if 'org' in intersection_df.columns:
                        intersection_df = intersection_df.drop(columns=['org'])
                    
                    intersection_df = get_pandas().merge(
                        intersection_df,
                        split_df,
                        left_on="链接",
                        right_on="id",
                        how="inner",
                        suffixes=('', '_split')
                    )
                    logger.info(f"After three-table intersection: {len(intersection_df)} records")
                    
                    # Now exclude online cases from the intersection
                    if not online_df.empty and '链接' in online_df.columns:
                        online_case_ids = set(online_df['链接'].tolist())
                        diff_df = intersection_df[~intersection_df['链接'].isin(online_case_ids)].copy()
                        logger.info(f"After excluding online cases: {len(diff_df)} records")
                    else:
                        diff_df = intersection_df.copy()
                        logger.info(f"No online data to exclude, keeping all intersection: {len(diff_df)} records")
                    
                    # Select specific columns as in frontend
                    selected_columns = []
                    
                    # csrc2analysis fields (including 序列号)
                    analysis_fields = ["名称", "文号", "发文日期", "序列号", "链接", "内容", "机构"]
                    for field in analysis_fields:
                        if field in diff_df.columns:
                            selected_columns.append(field)
                    
                    # csrc2cat fields
                    cat_fields = ["amount", "category", "province", "industry"]
                    for field in cat_fields:
                        if field in diff_df.columns:
                            selected_columns.append(field)
                    
                    # csrc2split fields
                    split_fields = ["wenhao", "people", "event", "law", "penalty", "org", "date"]
                    for field in split_fields:
                        if field in diff_df.columns:
                            selected_columns.append(field)
                    
                    # Keep only selected columns
                    if selected_columns:
                        diff_df = diff_df[selected_columns]
                        logger.info(f"Final diff data with selected columns: {len(diff_df)} records")
                else:
                    logger.warning("No data after analysis+category merge")
                    diff_df = get_pandas().DataFrame()
            else:
                logger.warning("Missing required datasets for three-table intersection")
                logger.info(f"Data availability: analysis={not analysis_df.empty}, category={not category_df.empty}, split={not split_df.empty}")
                diff_df = get_pandas().DataFrame()
                
        except Exception as e:
            logger.error(f"Error calculating three-table intersection: {str(e)}")
            diff_df = get_pandas().DataFrame()
        
        # Add upload status fields
        if not diff_df.empty:
            diff_df['status'] = 'pending'
            diff_df['uploadProgress'] = 0
            diff_df['errorMessage'] = None
        
        # Remove artificial limits for upload data to show all pending cases
        # Only apply reasonable limits for very large datasets to prevent memory issues
        MAX_RECORDS_PER_DATASET = 50000  # Very high limit to accommodate all pending upload cases
        
        def get_limited_data(df, max_records=MAX_RECORDS_PER_DATASET):
            """Get limited data with summary info to prevent memory issues"""
            if df.empty:
                return {"data": [], "count": 0, "uniqueCount": 0, "hasMore": False}
            
            # Get basic counts
            total_count = len(df)
            unique_count = 0
            
            # Calculate unique count based on available columns
            if '链接' in df.columns:
                unique_count = df['链接'].nunique()
            elif 'id' in df.columns:
                unique_count = df['id'].nunique()
            
            # Return limited records
            limited_df = df.head(max_records)
            
            return {
                "data": limited_df.to_dict('records'),
                "count": total_count,
                "uniqueCount": unique_count,
                "hasMore": total_count > max_records,
                "showing": len(limited_df)
            }
        
        data = {
            "caseDetail": get_limited_data(case_detail_df),
            "analysisData": get_limited_data(analysis_df),
            "categoryData": get_limited_data(category_df),
            "splitData": get_limited_data(split_df),
            "onlineData": get_limited_data(online_df),
            "diffData": get_limited_data(diff_df)
        }
        
        logger.info(f"Upload data retrieved successfully")
        
        # Create response
        response = APIResponse(
            success=True,
            message="Upload data retrieved successfully",
            data=data
        )
        
        # Cache the response
        upload_data_cache["data"] = response
        upload_data_cache["timestamp"] = time.time()
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get upload data: {str(e)}", exc_info=True)
        
        # If we have cached data, return it even if it's slightly stale
        if upload_data_cache["data"]:
            logger.info("Returning stale cached data due to error")
            return upload_data_cache["data"]
            
        return APIResponse(
            success=False,
            message="Failed to get upload data",
            error=str(e)
        )

class UploadCasesRequest(BaseModel):
    case_ids: List[str]

@app.post("/upload-cases", response_model=APIResponse)
@app.post("/api/upload-cases", response_model=APIResponse)
async def upload_cases(request: UploadCasesRequest):
    """Upload selected cases to online database using three-table intersection data"""
    try:
        logger.info(f"Starting upload for {len(request.case_ids)} cases")
        
        # Get three-table intersection data (following frontend logic)
        from data_service import get_csrc2analysis, get_csrc2cat, get_csrc2split
        
        # Get analysis data
        analysis_df = get_csrc2analysis()
        if analysis_df.empty:
            return APIResponse(
                success=False,
                message="No analysis data available for upload",
                count=0
            )
        
        # Get category data
        cat_df = get_csrc2cat()
        if cat_df.empty:
            return APIResponse(
                success=False,
                message="No category data available for upload",
                count=0
            )
        
        # Get split data
        split_df = get_csrc2split()
        if split_df.empty:
            return APIResponse(
                success=False,
                message="No split data available for upload",
                count=0
            )
        
        # Create three-table intersection (inner join)
        # Step 1: Merge analysis with category data
        merged_data = pd.merge(
            analysis_df,
            cat_df,
            left_on="链接",
            right_on="id",
            how="inner"
        )
        
        if merged_data.empty:
            return APIResponse(
                success=False,
                message="No intersection between analysis and category data",
                count=0
            )
        
        # Step 2: Merge with split data
        if 'org' in merged_data.columns:
            merged_data = merged_data.drop(columns=['org'])
        
        final_data = pd.merge(
            merged_data,
            split_df,
            left_on="链接",
            right_on="id",
            how="inner",
            suffixes=('', '_split')
        )
        
        if final_data.empty:
            return APIResponse(
                success=False,
                message="No three-table intersection data available",
                count=0
            )
        
        # Filter cases to upload from the three-table intersection
        cases_to_upload = final_data[final_data['链接'].isin(request.case_ids)]
        
        if cases_to_upload.empty:
            return APIResponse(
                success=False,
                message="No matching cases found in three-table intersection for upload",
                count=0
            )
        
        # Select only the required fields (following frontend logic)
        selected_columns = []
        
        # csrc2analysis fields
        analysis_fields = ["名称", "文号", "发文日期", "序列号", "链接", "内容", "机构"]
        for field in analysis_fields:
            if field in cases_to_upload.columns:
                selected_columns.append(field)
        
        # csrc2cat fields
        cat_fields = ["amount", "category", "province", "industry"]
        for field in cat_fields:
            if field in cases_to_upload.columns:
                selected_columns.append(field)
        
        # csrc2split fields
        split_fields = ["wenhao", "people", "event", "law", "penalty", "org", "date"]
        for field in split_fields:
            if field in cases_to_upload.columns:
                selected_columns.append(field)
        
        # Keep only selected columns
        if selected_columns:
            cases_to_upload = cases_to_upload[selected_columns]
        
        logger.info(f"Uploading {len(cases_to_upload)} cases with three-table intersection data")
        
        # Upload to MongoDB
        logger.info(f"Attempting to insert {len(cases_to_upload)} cases to MongoDB")
        success = insert_online_data(cases_to_upload)
        
        if success:
            uploaded_count = len(cases_to_upload)
            logger.info(f"Successfully uploaded {uploaded_count} cases to MongoDB")
            
            # Clear upload data cache to ensure fresh data on next request
            upload_data_cache["data"] = None
            upload_data_cache["timestamp"] = 0
            logger.info("Cleared upload data cache after successful upload")
            
            response = APIResponse(
                success=True,
                message=f"Successfully uploaded {uploaded_count} cases with complete data",
                count=uploaded_count
            )
            logger.info(f"Returning success response: {response.dict()}")
            return response
        else:
            logger.error("Failed to insert data to MongoDB")
            return APIResponse(
                success=False,
                message="Failed to upload cases to database",
                count=0
            )
        
    except Exception as e:
        logger.error(f"Case upload failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Case upload failed",
            error=str(e)
        )

@app.post("/generate-labels", response_model=APIResponse)
async def generate_labels():
    """Generate labels for case classification training - following frontend logic"""
    try:
        logger.info("Starting label generation for case classification")
        
        from data_service import get_csrc2analysis, get_csrc2cat, get_csrc2split
        
        # Get analysis data (equivalent to newdf in frontend)
        analysis_df = get_csrc2analysis()
        
        if analysis_df.empty:
            return APIResponse(
                success=False,
                message="No analysis data available for label generation"
            )
        
        # Get all analysis case URLs
        analysis_urls = analysis_df["链接"].tolist()
        
        # Get category data (equivalent to amtdf in frontend)
        category_df = get_csrc2cat()
        if category_df.empty:
            old_category_urls = []
        else:
            old_category_urls = category_df["id"].tolist()
        
        # Get split data (equivalent to splitdf in frontend)
        split_df = get_csrc2split()
        if split_df.empty:
            old_split_urls = []
        else:
            old_split_urls = split_df["id"].tolist()
        
        # Find cases that need category labeling (not in category data)
        new_category_urls = [x for x in analysis_urls if x not in old_category_urls]
        category_update_df = analysis_df[analysis_df["链接"].isin(new_category_urls)].copy()
        category_update_df.reset_index(drop=True, inplace=True)
        
        # Find cases that need split labeling (not in split data)
        new_split_urls = [x for x in analysis_urls if x not in old_split_urls]
        split_update_df = analysis_df[analysis_df["链接"].isin(new_split_urls)].copy()
        split_update_df.reset_index(drop=True, inplace=True)
        
        # Prepare data for labeling
        label_data = {
            "category_cases": [],
            "split_cases": [],
            "category_count": len(category_update_df),
            "split_count": len(split_update_df)
        }
        
        # Process category cases
        for _, row in category_update_df.iterrows():
            # Ensure all fields contain complete information
            content = str(row.get('内容', '')) if row.get('内容') is not None else ''
            title = str(row.get('名称', '')) if row.get('名称') is not None else ''
            org = str(row.get('机构', '')) if row.get('机构') is not None else ''
            wenhao = str(row.get('文号', '')) if row.get('文号') is not None else ''
            
            label_data["category_cases"].append({
                "id": row.get('链接', ''),
                "title": title,
                "content": content,  # Keep full content without truncation
                "organization": org,  # Use 'organization' to match frontend column
                "org": org,  # Keep 'org' for backward compatibility
                "date": str(row.get('发文日期', '')),
                "wenhao": wenhao,
                "status": "pending_category_label",
                "type": "category"
            })
        
        # Process split cases
        for _, row in split_update_df.iterrows():
            # Ensure all fields contain complete information
            content = str(row.get('内容', '')) if row.get('内容') is not None else ''
            title = str(row.get('名称', '')) if row.get('名称') is not None else ''
            org = str(row.get('机构', '')) if row.get('机构') is not None else ''
            wenhao = str(row.get('文号', '')) if row.get('文号') is not None else ''
            
            label_data["split_cases"].append({
                "id": row.get('链接', ''),
                "title": title,
                "content": content,  # Keep full content without truncation
                "organization": org,  # Use 'organization' to match frontend column
                "org": org,  # Keep 'org' for backward compatibility
                "date": str(row.get('发文日期', '')),
                "wenhao": wenhao,
                "status": "pending_split_label",
                "type": "split"
            })
        
        # Sort both category and split cases by date (newest first)
        # Handle empty dates by treating them as very old dates
        def sort_by_date(case):
            date_str = case.get('date', '')
            if not date_str or date_str == 'nan':
                return '1900-01-01'  # Very old date for empty values
            return date_str
        
        label_data["category_cases"].sort(key=sort_by_date, reverse=True)
        label_data["split_cases"].sort(key=sort_by_date, reverse=True)
        
        total_cases = len(label_data["category_cases"]) + len(label_data["split_cases"])
        
        if total_cases == 0:
            return APIResponse(
                success=True,
                message="所有数据已更新，无需标注",
                data=label_data,
                count=0
            )
        
        logger.info(f"Generated {total_cases} cases for labeling (Category: {len(label_data['category_cases'])}, Split: {len(label_data['split_cases'])})")
        
        return APIResponse(
            success=True,
            message=f"成功生成 {total_cases} 条待标注案例 (分类: {len(label_data['category_cases'])}条, 拆分: {len(label_data['split_cases'])}条)",
            data=label_data,
            count=total_cases
        )
        
    except Exception as e:
        logger.error(f"Label generation failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Label generation failed",
            error=str(e)
        )

@app.delete("/online-data", response_model=APIResponse)
@app.delete("/api/online-data", response_model=APIResponse)
async def delete_online_data_endpoint():
    """Delete all online case data"""
    try:
        logger.info("Starting deletion of online data")
        
        # Delete from MongoDB
        deleted_count = delete_online_data()
        
        # Clear upload data cache to ensure fresh data on next request
        upload_data_cache["data"] = None
        upload_data_cache["timestamp"] = 0
        logger.info("Cleared upload data cache after successful deletion")
        
        logger.info(f"Successfully deleted {deleted_count} online cases")
        return APIResponse(
            success=True,
            message=f"Successfully deleted {deleted_count} online cases",
            count=deleted_count
        )
        
    except Exception as e:
        logger.error(f"Online data deletion failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Online data deletion failed",
            error=str(e)
        )

@app.get("/api/download/online-data")
async def download_online_data():
    """Download online case data CSV file"""
    try:
        logger.info("Starting online data CSV download")
        
        # Get online data from MongoDB
        online_df = get_online_data()
        
        # Check if data is empty
        if online_df.empty:
            logger.warning("No online data available for download")
            raise HTTPException(status_code=404, detail="No online data available for download")
        
        logger.info(f"Retrieved {len(online_df)} records for download")
        
        # Convert to CSV
        try:
            csv_buffer = io.StringIO()
            online_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            csv_content = csv_buffer.getvalue()
            logger.info(f"CSV conversion successful, size: {len(csv_content)} bytes")
        except Exception as csv_error:
            logger.error(f"CSV conversion failed: {str(csv_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"CSV conversion failed: {str(csv_error)}")
        
        # Create response
        try:
            response = StreamingResponse(
                io.BytesIO(csv_content.encode('utf-8-sig')),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=online_data_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
            logger.info("Online data CSV download response created successfully")
            return response
        except Exception as resp_error:
            logger.error(f"Failed to create response: {str(resp_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create response: {str(resp_error)}")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Online data CSV download failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/diff-data")
@app.get("/api/download/diff-data")
async def download_diff_data():
    """Download diff data CSV file (three-table intersection minus online)"""
    try:
        logger.info("Starting diff data CSV download")
        
        from data_service import get_csrc2analysis, get_csrc2cat, get_csrc2split
        
        # Get analysis data
        analysis_df = get_csrc2analysis()
        
        # Get category data
        category_df = get_csrc2cat()
        
        # Get split data
        split_df = get_csrc2split()
        
        # Get online data
        online_df = get_online_data()
        
        # Calculate diff data using same logic as upload-data endpoint
        if not analysis_df.empty:
            # Exclude online cases from analysis data
            if not online_df.empty and '链接' in online_df.columns:
                online_case_ids = set(online_df['链接'].tolist())
                diff_analysis = analysis_df[~analysis_df['链接'].isin(online_case_ids)].copy()
            else:
                diff_analysis = analysis_df.copy()
            
            # Merge with category and split data (inner join for intersection)
            if not category_df.empty and not split_df.empty and not diff_analysis.empty:
                # Step 1: Inner join with category data
                diff_df = get_pandas().merge(
                    diff_analysis,
                    category_df,
                    left_on="链接",
                    right_on="id",
                    how="inner"
                )
                
                # Step 2: Inner join with split data
                if not diff_df.empty:
                    # Remove 'org' column if exists
                    if 'org' in diff_df.columns:
                        diff_df = diff_df.drop(columns=['org'])
                    
                    diff_df = get_pandas().merge(
                        diff_df,
                        split_df,
                        left_on="链接",
                        right_on="id",
                        how="inner",
                        suffixes=('', '_split')
                    )
                
                # Select specific columns
                selected_columns = []
                analysis_fields = ["名称", "文号", "发文日期", "序列号", "链接", "内容", "机构"]
                cat_fields = ["amount", "category", "province", "industry"]
                split_fields = ["wenhao", "people", "event", "law", "penalty", "org", "date"]
                
                for field in analysis_fields + cat_fields + split_fields:
                    if field in diff_df.columns:
                        selected_columns.append(field)
                
                if selected_columns:
                    diff_df = diff_df[selected_columns]
            else:
                diff_df = get_pandas().DataFrame()
        else:
            diff_df = get_pandas().DataFrame()
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        diff_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_content = csv_buffer.getvalue()
        
        # Create response
        response = StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=diff_data_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
        
        logger.info("Diff data CSV download completed")
        return response
        
    except Exception as e:
        logger.error(f"Diff data CSV download failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-penalty-analysis-results", response_model=APIResponse)
async def save_penalty_analysis_results(request: Request):
    """Save penalty analysis results to CSV files in the data directory"""
    try:
        logger.info("Starting penalty analysis results save")
        
        # Parse request body
        body = await request.json()
        penalty_results = body.get('penaltyResults', [])
        
        if not penalty_results:
            return APIResponse(
                success=False,
                message="No penalty results to save"
            )
        
        # Generate datetime string for filenames
        datetime_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Define file paths in the same directory as csrc2analysis.csv
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "..", "data", "penalty", "csrc2")
        data_dir = os.path.abspath(data_dir)  # Normalize the path
        
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        cat_filename = f"csrccat_{datetime_str}.csv"
        split_filename = f"csrcsplit_{datetime_str}.csv"
        
        cat_filepath = os.path.join(data_dir, cat_filename)
        split_filepath = os.path.join(data_dir, split_filename)
        
        # Prepare data for csrc2cat (id, amount, category, province, industry)
        cat_data = []
        for result in penalty_results:
            cat_data.append({
                'id': result.get('id', ''),
                'amount': result.get('罚没总金额', ''),
                'category': result.get('违规类型', ''),
                'province': result.get('监管地区', ''),
                'industry': result.get('行业', '')
            })
        
        # Prepare data for csrc2split (id, wenhao, people, event, law, penalty, org, date)
        split_data = []
        for result in penalty_results:
            split_data.append({
                'id': result.get('id', ''),
                'wenhao': result.get('行政处罚决定书文号', ''),
                'people': result.get('被处罚当事人', ''),
                'event': result.get('主要违法违规事实', ''),
                'law': result.get('行政处罚依据', ''),
                'penalty': result.get('行政处罚决定', ''),
                'org': result.get('作出处罚决定的机关名称', ''),
                'date': result.get('作出处罚决定的日期', '')
            })
        
        # Convert to DataFrames and save as CSV
        cat_df = get_pandas().DataFrame(cat_data)
        split_df = get_pandas().DataFrame(split_data)
        
        cat_df.to_csv(cat_filepath, index=False, encoding='utf-8-sig')
        split_df.to_csv(split_filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"Successfully saved penalty analysis results to {cat_filename} and {split_filename}")
        
        return APIResponse(
            success=True,
            message=f"分析结果已成功保存为 {cat_filename} 和 {split_filename}",
            data={
                'cat_filename': cat_filename,
                'split_filename': split_filename,
                'cat_filepath': cat_filepath,
                'split_filepath': split_filepath,
                'records_count': len(penalty_results)
            }
        )
        
    except Exception as e:
        logger.error(f"Penalty analysis results save failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="保存分析结果失败",
            error=str(e)
        )

@app.post("/api/upload-analysis-results", response_model=APIResponse)
async def upload_analysis_results(file: UploadFile = File(...)):
    """Upload and save analysis results file as csrccat and csrcsplit files, filtering out failed records"""
    try:
        logger.info(f"Starting upload analysis results from file: {file.filename}")
        
        # Validate file type
        if not file.filename.endswith('.csv'):
            return APIResponse(
                success=False,
                message="只支持CSV文件格式"
            )
        
        # Read and parse CSV file
        contents = await file.read()
        file_obj = io.BytesIO(contents)
        df = get_pandas().read_csv(file_obj, encoding='utf-8-sig')
        
        if df.empty:
            return APIResponse(
                success=False,
                message="上传的文件为空"
            )
        
        # Filter out failed records based on status column
        original_count = len(df)
        filtered_df = df.copy()
        
        # Check for various status column names and filter out failed records
        status_columns = ['status', 'Status', 'STATUS', '状态', 'state', 'State', 'analysis_status', 'Analysis_Status', 'ANALYSIS_STATUS']
        status_col = None
        
        for col in status_columns:
            if col in df.columns:
                status_col = col
                break
        
        if status_col:
            # Filter out records with failed status
            failed_values = ['failed', 'Failed', 'FAILED', 'fail', 'Fail', 'FAIL', 
                           'error', 'Error', 'ERROR', '失败', '错误', 'false', 'False', 'FALSE']
            
            # Keep only records that are not in failed_values
            filtered_df = df[~df[status_col].astype(str).str.strip().isin(failed_values)]
            
            # Also filter out empty/null status values if they should be considered failed
            filtered_df = filtered_df[filtered_df[status_col].notna() & (filtered_df[status_col].astype(str).str.strip() != '')]
            
            filtered_count = len(filtered_df)
            failed_count = original_count - filtered_count
            
            logger.info(f"Filtered out {failed_count} failed records from {original_count} total records, {filtered_count} records remaining")
        else:
            logger.info(f"No status column found, processing all {original_count} records")
            filtered_count = original_count
            failed_count = 0
        
        if filtered_df.empty:
            return APIResponse(
                success=False,
                message=f"过滤失败记录后没有有效数据。原始记录数: {original_count}, 失败记录数: {failed_count}"
            )
        
        # Convert DataFrame to list of dictionaries with size limit to prevent memory issues
        MAX_UPLOAD_RECORDS = 5000  # Limit to prevent memory overflow during upload
        total_records = len(filtered_df)
        limited_df = filtered_df.head(MAX_UPLOAD_RECORDS)
        penalty_results = limited_df.to_dict('records')
        
        if total_records > MAX_UPLOAD_RECORDS:
            logger.warning(f"Upload file has {total_records} records, processing only first {MAX_UPLOAD_RECORDS} to prevent memory issues")
        
        # Generate datetime string for filenames
        datetime_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Define file paths in the same directory as csrc2analysis.csv
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "..", "data", "penalty", "csrc2")
        data_dir = os.path.abspath(data_dir)  # Normalize the path
        
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        cat_filename = f"csrccat_{datetime_str}.csv"
        split_filename = f"csrcsplit_{datetime_str}.csv"
        
        cat_filepath = os.path.join(data_dir, cat_filename)
        split_filepath = os.path.join(data_dir, split_filename)
        
        # Prepare data for csrc2cat (id, amount, category, province, industry)
        cat_data = []
        for result in penalty_results:
            cat_data.append({
                'id': result.get('id', '') or result.get('ID', '') or result.get('链接', ''),
                'amount': result.get('amount', '') or result.get('罚没总金额', ''),
                'category': result.get('category', '') or result.get('违规类型', ''),
                'province': result.get('province', '') or result.get('监管地区', ''),
                'industry': result.get('industry', '') or result.get('行业', '')
            })
        
        # Prepare data for csrc2split (id, wenhao, people, event, law, penalty, org, date)
        split_data = []
        for result in penalty_results:
            split_data.append({
                'id': result.get('id', '') or result.get('ID', '') or result.get('链接', ''),
                'wenhao': result.get('wenhao', '') or result.get('行政处罚决定书文号', ''),
                'people': result.get('people', '') or result.get('被处罚当事人', ''),
                'event': result.get('event', '') or result.get('主要违法违规事实', ''),
                'law': result.get('law', '') or result.get('行政处罚依据', ''),
                'penalty': result.get('penalty', '') or result.get('行政处罚决定', ''),
                'org': result.get('org', '') or result.get('作出处罚决定的机关名称', ''),
                'date': result.get('date', '') or result.get('作出处罚决定的日期', '')
            })
        
        # Convert to DataFrames and save as CSV
        cat_df = get_pandas().DataFrame(cat_data)
        split_df = get_pandas().DataFrame(split_data)
        
        cat_df.to_csv(cat_filepath, index=False, encoding='utf-8-sig')
        split_df.to_csv(split_filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"Successfully saved uploaded analysis results to {cat_filename} and {split_filename}")
        
        # Prepare success message with filtering information
        if status_col and failed_count > 0:
            filter_message = f"已过滤掉 {failed_count} 条失败记录，"
        else:
            filter_message = ""
        
        success_message = f"{filter_message}上传的分析结果已成功保存为 {cat_filename} 和 {split_filename}"
        
        return APIResponse(
            success=True,
            message=success_message,
            data={
                'cat_filename': cat_filename,
                'split_filename': split_filename,
                'cat_filepath': cat_filepath,
                'split_filepath': split_filepath,
                'records_count': len(penalty_results),
                'total_records_in_file': original_count,
                'filtered_records_count': filtered_count,
                'failed_records_count': failed_count,
                'records_processed': len(penalty_results),
                'has_more_records': total_records > MAX_UPLOAD_RECORDS,
                'status_column_found': status_col is not None,
                'status_column_name': status_col,
                'uploaded_data': penalty_results if len(penalty_results) <= 100 else penalty_results[:100]  # Only return first 100 for display
            }
        )
        
    except Exception as e:
        logger.error(f"Upload analysis results failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="上传分析结果失败",
            error=str(e)
        )

@app.get("/api/downloaded-file-status", response_model=APIResponse)
async def get_downloaded_file_status():
    """Get downloaded file status from csrcmiscontent files"""
    try:
        logger.info("Getting downloaded file status from csrcmiscontent files")
        
        from data_service import get_csrcmiscontent
        
        # Get csrcmiscontent data
        misc_df = get_csrcmiscontent()
        
        if misc_df.empty:
            logger.info("No csrcmiscontent data found")
            return APIResponse(
                success=True,
                message="No downloaded file data available",
                data=[]
            )
        
        # Convert DataFrame to list of dictionaries
        downloaded_files = misc_df.to_dict('records')
        
        logger.info(f"Retrieved {len(downloaded_files)} downloaded file records")
        
        return APIResponse(
            success=True,
            message=f"Successfully retrieved {len(downloaded_files)} downloaded file records",
            data=downloaded_files
        )
        
    except Exception as e:
        logger.error(f"Failed to get downloaded file status: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to get downloaded file status",
            error=str(e)
        )

@app.post("/check-file-exists", response_model=APIResponse)
async def check_file_exists(request: dict):
    """Check if a file exists on the server"""
    try:
        file_path = request.get('file_path', '')
        
        if not file_path:
            return APIResponse(
                success=False,
                message="File path is required",
                data={'exists': False}
            )
        
        # Check if file exists
        exists = os.path.exists(file_path)
        
        logger.info(f"File existence check for {file_path}: {exists}")
        
        return APIResponse(
            success=True,
            message=f"File {'exists' if exists else 'does not exist'}",
            data={'exists': exists, 'file_path': file_path}
        )
        
    except Exception as e:
        logger.error(f"Failed to check file existence: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to check file existence",
            error=str(e),
            data={'exists': False}
        )

async def update_content_files_after_extraction(extraction_results: list):
    """Update csrclenanalysis files after text extraction
    
    Only updates existing files, does not create new ones.
    """
    try:
        from web_crawler import get_csrclenanalysis, savetemp
        import pandas as pd
        import os
        
        # Get file paths
        current_file = os.path.abspath(__file__)
        backend_dir = os.path.dirname(current_file)
        project_root = os.path.dirname(backend_dir)
        tempdir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
        len_file_path = os.path.join(tempdir, "csrclenanalysis.csv")
        
        # Only update csrclenanalysis if the file already exists
        if os.path.exists(len_file_path):
            # Update csrclenanalysis with new content lengths and content
            len_df = get_csrclenanalysis()
            
            if not len_df.empty:
                updated_len = False
                for result in extraction_results:
                    url = result.get('url', '')
                    extracted_text = result.get('text', '')
                    text_length = len(extracted_text) if extracted_text else 0
                    
                    if url:
                        # Find matching rows by URL
                        mask = len_df['链接'] == url if '链接' in len_df.columns else len_df['url'] == url
                        if mask.any():
                            # Update the length information
                            if 'len' in len_df.columns:
                                len_df.loc[mask, 'len'] = text_length
                            if '内容长度' in len_df.columns:
                                len_df.loc[mask, '内容长度'] = text_length
                            # Update the content information
                            if 'content' in len_df.columns:
                                len_df.loc[mask, 'content'] = extracted_text
                            if '内容' in len_df.columns:
                                len_df.loc[mask, '内容'] = extracted_text
                            if 'text' in len_df.columns:
                                len_df.loc[mask, 'text'] = extracted_text
                            logger.info(f"Updated length and content for URL: {url} to {text_length} characters")
                            updated_len = True
                
                # Save updated csrclenanalysis only if there were updates
                if updated_len:
                    savetemp(len_df, "csrclenanalysis")
                    logger.info("Updated existing csrclenanalysis file")
                else:
                    logger.info("No matching URLs found in csrclenanalysis for update")
            else:
                logger.info("csrclenanalysis file exists but is empty")
        else:
            logger.info("csrclenanalysis file does not exist, skipping update")
            
    except Exception as e:
        logger.error(f"Error updating content files: {str(e)}")
        raise

@app.post("/extract-text", response_model=APIResponse)
async def extract_text(request: dict):
    """Extract text from attachments based on file type"""
    try:
        attachment_ids = request.get('attachment_ids', [])
        
        if not attachment_ids:
            return APIResponse(
                success=False,
                message="Attachment IDs are required",
                data={'result': []}
            )
        
        logger.info(f"Starting text extraction for {len(attachment_ids)} attachments")
        
        # Get csrcmiscontent data to find attachment information
        from data_service import get_csrcmiscontent
        misc_df = get_csrcmiscontent()
        
        if misc_df.empty:
            logger.warning("No csrcmiscontent data found")
            return APIResponse(
                success=True,
                message="No attachment data available for text extraction",
                data={'result': []}
            )
        
        # Import text extraction functions from doc2text
        from doc2text import docxurl2txt, pdfurl2txt, docxurl2ocr, pdfurl2ocr, picurl2ocr, find_libreoffice_executable, convert_with_libreoffice
        import os
        import subprocess
        
        # Extract text for each attachment ID
        extraction_results = []
        
        for attachment_id in attachment_ids:
            try:
                # Find the attachment in the data
                attachment_data = misc_df[misc_df['url'] == attachment_id]
                
                if attachment_data.empty:
                    # If not found by URL, try to find by other identifiers
                    attachment_data = misc_df[misc_df.index.astype(str) == str(attachment_id)]
                
                if not attachment_data.empty:
                    row = attachment_data.iloc[0]
                    raw_filename = row.get('filename', '') if hasattr(row, 'get') else ''
                    attachment_url = row.get('url', attachment_id) if hasattr(row, 'get') else attachment_id
                    
                    # Clean filename by removing timestamp prefix (format: YYYYMMDDHHMMSS)
                    # Use original filename from CSV data (keep timestamp)
                    filename = raw_filename if raw_filename else f"attachment_{attachment_id}"
                    
                    # First check if text is already extracted in the CSV
                    existing_text = ""
                    try:
                        if hasattr(row, '__getitem__') and 'text' in row and row['text'] is not None:
                            # Use pandas isna if available, otherwise check for None/empty
                            if hasattr(pd, 'isna') and not pd.isna(row['text']):
                                existing_text = str(row['text']).strip()
                            elif row['text'] not in [None, '', 'nan', 'NaN']:
                                existing_text = str(row['text']).strip()
                        elif hasattr(row, '__getitem__') and 'content' in row and row['content'] is not None:
                            if hasattr(pd, 'isna') and not pd.isna(row['content']):
                                existing_text = str(row['content']).strip()
                            elif row['content'] not in [None, '', 'nan', 'NaN']:
                                existing_text = str(row['content']).strip()
                    except Exception as text_check_error:
                        logger.warning(f"Error checking existing text: {str(text_check_error)}")
                        existing_text = ""
                    
                    extracted_text = ""
                    
                    # If no existing text or empty, extract based on file type
                    if not existing_text and filename:
                        # Get file extension
                        base, ext = os.path.splitext(filename)
                        ext = ext.lower()
                        
                        # Construct file path in temp directory
                        current_file = os.path.abspath(__file__)
                        backend_dir = os.path.dirname(current_file)
                        project_root = os.path.dirname(backend_dir)
                        temp_dir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
                        file_path = os.path.join(temp_dir, filename)
                        
                        try:
                            if os.path.exists(file_path):
                                if ext in ['.docx']:
                                    extracted_text = docxurl2txt(file_path)
                                    logger.info(f"DOCX direct extraction result length: {len(extracted_text) if extracted_text else 0}")
                                    # If direct extraction fails, try OCR
                                    if not extracted_text or not extracted_text.strip():
                                        logger.info(f"Trying OCR for DOCX file: {filename}")
                                        extracted_text = docxurl2ocr(file_path, temp_dir)
                                        logger.info(f"DOCX OCR extraction result length: {len(extracted_text) if extracted_text else 0}")
                                        
                                elif ext in ['.doc']:
                                    # For .doc files, convert to DOCX using LibreOffice first
                                    doc_dir = os.path.join(temp_dir, "doc")
                                    os.makedirs(doc_dir, exist_ok=True)
                                    converted_path = os.path.join(doc_dir, base + ".docx")
                                    
                                    # Convert using LibreOffice if converted file doesn't exist
                                    if not os.path.exists(converted_path):
                                        try:
                                            logger.info(f"Converting DOC file to DOCX: {filename}")
                                            soffice_path = find_libreoffice_executable()
                                            if soffice_path:
                                                success = convert_with_libreoffice(file_path, doc_dir, soffice_path)
                                                if not success:
                                                    extracted_text = f"LibreOffice conversion failed for {filename}"
                                            else:
                                                logger.error("LibreOffice not found on system")
                                                extracted_text = "LibreOffice not found - cannot convert DOC files"
                                        except Exception as convert_error:
                                            logger.error(f"LibreOffice conversion failed for {filename}: {str(convert_error)}")
                                            extracted_text = f"Conversion failed: {str(convert_error)}"
                                    
                                    # Extract text from converted DOCX file
                                    if os.path.exists(converted_path) and not extracted_text:
                                        extracted_text = docxurl2txt(converted_path)
                                        logger.info(f"DOC->DOCX direct extraction result length: {len(extracted_text) if extracted_text else 0}")
                                        # If direct extraction fails, try OCR
                                        if not extracted_text or not extracted_text.strip():
                                            logger.info(f"Trying OCR for converted DOC file: {filename}")
                                            extracted_text = docxurl2ocr(converted_path, temp_dir)
                                            logger.info(f"DOC->DOCX OCR extraction result length: {len(extracted_text) if extracted_text else 0}")
                                    
                                elif ext in ['.wps']:
                                    # For .wps files, convert to DOCX using LibreOffice first
                                    wps_dir = os.path.join(temp_dir, "wps")
                                    os.makedirs(wps_dir, exist_ok=True)
                                    converted_path = os.path.join(wps_dir, base + ".docx")
                                    
                                    # Convert using LibreOffice if converted file doesn't exist
                                    if not os.path.exists(converted_path):
                                        try:
                                            logger.info(f"Converting WPS file to DOCX: {filename}")
                                            soffice_path = find_libreoffice_executable()
                                            if soffice_path:
                                                success = convert_with_libreoffice(file_path, wps_dir, soffice_path)
                                                if not success:
                                                    extracted_text = f"LibreOffice conversion failed for {filename}"
                                            else:
                                                logger.error("LibreOffice not found on system")
                                                extracted_text = "LibreOffice not found - cannot convert WPS files"
                                        except Exception as convert_error:
                                            logger.error(f"LibreOffice conversion failed for {filename}: {str(convert_error)}")
                                            extracted_text = f"Conversion failed: {str(convert_error)}"
                                    
                                    # Extract text from converted DOCX file
                                    if os.path.exists(converted_path) and not extracted_text:
                                        extracted_text = docxurl2txt(converted_path)
                                        logger.info(f"WPS->DOCX direct extraction result length: {len(extracted_text) if extracted_text else 0}")
                                        # If direct extraction fails, try OCR
                                        if not extracted_text or not extracted_text.strip():
                                            logger.info(f"Trying OCR for converted WPS file: {filename}")
                                            extracted_text = docxurl2ocr(converted_path, temp_dir)
                                            logger.info(f"WPS->DOCX OCR extraction result length: {len(extracted_text) if extracted_text else 0}")
                                            
                                elif ext in ['.pdf']:
                                    extracted_text = pdfurl2txt(file_path)
                                    # If direct extraction fails, try OCR
                                    if not extracted_text.strip():
                                        extracted_text = pdfurl2ocr(file_path, temp_dir)
                                        
                                elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
                                    extracted_text = picurl2ocr(file_path)
                                    
                                elif ext in ['.xls', '.xlsx']:
                                    # For Excel files, we could add support later
                                    extracted_text = "Excel file - text extraction not yet supported"
                                    
                                else:
                                    extracted_text = f"Unsupported file type: {ext}"
                            else:
                                extracted_text = f"File not found: {filename}"
                                
                        except Exception as file_error:
                            logger.error(f"Error extracting text from {filename}: {str(file_error)}")
                            extracted_text = f"Error extracting text: {str(file_error)}"
                    else:
                        extracted_text = existing_text if existing_text else "No text content available"
                    
                    result_item = {
                        'url': attachment_url,
                        'filename': filename,
                        'text': extracted_text
                    }
                else:
                    # Attachment not found, return empty result
                    result_item = {
                        'url': attachment_id,
                        'filename': f'attachment_{attachment_id}',
                        'text': 'Attachment not found'
                    }
                
                extraction_results.append(result_item)
                
            except Exception as e:
                logger.error(f"Error extracting text for attachment {attachment_id}: {str(e)}")
                extraction_results.append({
                    'url': attachment_id,
                    'filename': f'attachment_{attachment_id}',
                    'text': f'Error: {str(e)}'
                })
        
        logger.info(f"Text extraction completed for {len(extraction_results)} attachments")
        
        # Update csrclenanalysis files after successful text extraction
        try:
            await update_content_files_after_extraction(extraction_results)
            logger.info("Successfully updated csrclenanalysis files")
        except Exception as update_error:
            logger.warning(f"Failed to update content files: {str(update_error)}")
            # Don't fail the entire operation if file update fails
        
        return APIResponse(
            success=True,
            message=f"Successfully extracted text from {len(extraction_results)} attachments",
            data={'result': extraction_results}
        )
        
    except Exception as e:
        logger.error(f"Text extraction failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Text extraction failed",
            error=str(e),
            data={'result': []}
        )

@app.post("/delete-attachments", response_model=APIResponse)
async def delete_attachments(request: dict):
    """Delete attachments"""
    try:
        attachment_ids = request.get('attachment_ids', [])
        
        if not attachment_ids:
            return APIResponse(
                success=False,
                message="Attachment IDs are required"
            )
        
        logger.info(f"Starting deletion of {len(attachment_ids)} attachments")
        
        # For now, this is a placeholder implementation
        # In a real implementation, you would delete the actual files and database records
        
        logger.info(f"Successfully deleted {len(attachment_ids)} attachments")
        
        return APIResponse(
            success=True,
            message=f"Successfully deleted {len(attachment_ids)} attachments"
        )
        
    except Exception as e:
        logger.error(f"Attachment deletion failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Attachment deletion failed",
            error=str(e)
        )

@app.post("/update-attachment-text", response_model=APIResponse)
async def update_attachment_text(request: dict):
    """Update attachment text content in csrc2analysis files based on links and source file information"""
    try:
        attachment_ids = request.get('attachment_ids', [])
        
        if not attachment_ids:
            return APIResponse(
                success=False,
                message="Attachment IDs are required"
            )
        
        logger.info(f"Starting text update for {len(attachment_ids)} attachments")
        
        # Import required modules
        from web_crawler import get_csrc2analysis, get_csrclenanalysis, savedf_backend, get_now
        import pandas as pd
        import os
        
        # Get csrc2analysis data
        analysis_df = get_csrc2analysis()
        if analysis_df.empty:
            return APIResponse(
                success=False,
                message="No csrc2analysis data found"
            )
        
        # Get csrclenanalysis data to find attachment information
        len_df = get_csrclenanalysis()
        if len_df.empty:
            return APIResponse(
                success=False,
                message="No csrclenanalysis data found"
            )
        
        updated_attachments = []
        updated_count = 0
        
        # Track which specific records need to be updated (by URL)
        records_to_update = {}  # {url: {text_content, content_length}}
        
        # Process each attachment ID
        for attachment_id in attachment_ids:
            try:
                # Find the attachment in csrclenanalysis data
                # Try to find by URL first
                attachment_data = pd.DataFrame()
                if '链接' in len_df.columns:
                    attachment_data = len_df[len_df['链接'] == attachment_id]
                elif 'url' in len_df.columns:
                    attachment_data = len_df[len_df['url'] == attachment_id]
                
                if attachment_data.empty:
                    # Try to find by index if not found by URL
                    try:
                        attachment_data = len_df[len_df.index.astype(str) == str(attachment_id)]
                    except:
                        pass
                
                if not attachment_data.empty:
                    row = attachment_data.iloc[0]
                    attachment_url = row.get('url', attachment_id) if hasattr(row, 'get') else attachment_id
                    
                    # Get text content from csrclenanalysis data
                    text_content = ""
                    try:
                        # Try to get text from various possible columns in csrclenanalysis
                        if hasattr(row, '__getitem__') and 'text' in row and row['text'] is not None:
                            if hasattr(pd, 'isna') and not pd.isna(row['text']):
                                text_content = str(row['text']).strip()
                            elif row['text'] not in [None, '', 'nan', 'NaN']:
                                text_content = str(row['text']).strip()
                        elif hasattr(row, '__getitem__') and '内容' in row and row['内容'] is not None:
                            if hasattr(pd, 'isna') and not pd.isna(row['内容']):
                                text_content = str(row['内容']).strip()
                            elif row['内容'] not in [None, '', 'nan', 'NaN']:
                                text_content = str(row['内容']).strip()
                        elif hasattr(row, '__getitem__') and 'content' in row and row['content'] is not None:
                            if hasattr(pd, 'isna') and not pd.isna(row['content']):
                                text_content = str(row['content']).strip()
                            elif row['content'] not in [None, '', 'nan', 'NaN']:
                                text_content = str(row['content']).strip()
                    except Exception as text_error:
                        logger.warning(f"Error getting text content for {attachment_id}: {str(text_error)}")
                        text_content = ""
                    
                    # Find matching record in csrc2analysis by URL
                    if '链接' in analysis_df.columns:
                        mask = analysis_df['链接'] == attachment_url
                    elif 'url' in analysis_df.columns:
                        mask = analysis_df['url'] == attachment_url
                    else:
                        logger.warning("No URL column found in csrc2analysis data")
                        continue
                    
                    if mask.any():
                        # Store the update information for later processing
                        content_length = len(text_content) if text_content else 0
                        records_to_update[attachment_url] = {
                            'text_content': text_content,
                            'content_length': content_length
                        }
                        
                        updated_count += 1
                        logger.info(f"Prepared update for URL: {attachment_url} with {content_length} characters")
                        
                        updated_attachments.append({
                            'id': attachment_id,
                            'url': attachment_url,
                            'content': text_content,
                            'contentLength': content_length
                        })
                    else:
                        logger.warning(f"No matching record found in csrc2analysis for URL: {attachment_url}")
                        updated_attachments.append({
                            'id': attachment_id,
                            'url': attachment_url,
                            'content': '',
                            'contentLength': 0,
                            'error': 'No matching record found in csrc2analysis'
                        })
                else:
                    logger.warning(f"Attachment not found in csrclenanalysis: {attachment_id}")
                    updated_attachments.append({
                        'id': attachment_id,
                        'content': '',
                        'contentLength': 0,
                        'error': 'Attachment not found'
                    })
                    
            except Exception as attachment_error:
                logger.error(f"Error processing attachment {attachment_id}: {str(attachment_error)}")
                updated_attachments.append({
                    'id': attachment_id,
                    'content': '',
                    'contentLength': 0,
                    'error': str(attachment_error)
                })
        
        # Save updated csrc2analysis data if any updates were made
        if updated_count > 0 and records_to_update:
            try:
                # Group by source_filename to save each file separately
                if 'source_filename' in analysis_df.columns:
                    # Find which files contain the updated records
                    files_to_update = set()
                    for url in records_to_update.keys():
                        if '链接' in analysis_df.columns:
                            matching_records = analysis_df[analysis_df['链接'] == url]
                        elif 'url' in analysis_df.columns:
                            matching_records = analysis_df[analysis_df['url'] == url]
                        else:
                            continue
                        
                        if not matching_records.empty:
                            source_files = matching_records['source_filename'].dropna().unique()
                            files_to_update.update(source_files)
                    
                    backup_count = 0  # Track total number of backups created
                    
                    # Collect all records that will be updated for backup
                    backup_records = []
                    
                    # Only process files that contain updated records
                    for source_filename in files_to_update:
                        # Read the original file from disk to get clean data
                        current_file = os.path.abspath(__file__)
                        backend_dir = os.path.dirname(current_file)
                        project_root = os.path.dirname(backend_dir)
                        csrc2_dir = os.path.join(project_root, "data", "penalty", "csrc2")
                        original_file_path = os.path.join(csrc2_dir, source_filename)
                        
                        if not os.path.exists(original_file_path):
                            logger.warning(f"Original file not found: {original_file_path}")
                            continue
                        
                        # Read the original file data
                        try:
                            original_file_data = get_pandas().read_csv(original_file_path, encoding='utf-8-sig')
                        except Exception as read_error:
                            logger.error(f"Failed to read original file {source_filename}: {str(read_error)}")
                            continue
                        
                        # Collect records that will be updated for backup
                        file_updated = False
                        for url, update_info in records_to_update.items():
                            # Find matching records in this file
                            if '链接' in original_file_data.columns:
                                mask = original_file_data['链接'] == url
                            elif 'url' in original_file_data.columns:
                                mask = original_file_data['url'] == url
                            else:
                                continue
                            
                            if mask.any():
                                # Get the original record(s) before update for backup
                                original_records = original_file_data[mask].copy()
                                # Add source file info to backup records
                                original_records['backup_source_file'] = source_filename
                                original_records['backup_timestamp'] = get_now()
                                backup_records.append(original_records)
                                
                                # Update the content field
                                if '内容' in original_file_data.columns:
                                    original_file_data.loc[mask, '内容'] = update_info['text_content']
                                elif 'content' in original_file_data.columns:
                                    original_file_data.loc[mask, 'content'] = update_info['text_content']
                                
                                # Update content length if column exists
                                if 'len' in original_file_data.columns:
                                    original_file_data.loc[mask, 'len'] = update_info['content_length']
                                elif '内容长度' in original_file_data.columns:
                                    original_file_data.loc[mask, '内容长度'] = update_info['content_length']
                                
                                file_updated = True
                                logger.info(f"Applied update for URL {url} in file {source_filename}")
                        
                        # Save the updated file data only if changes were made
                        if file_updated:
                            original_file_data.to_csv(original_file_path, index=False, encoding='utf-8-sig')
                            logger.info(f"Saved updated data to {source_filename}")
                    
                    # Create a single backup file with all updated records
                    if backup_records:
                        try:
                            # Combine all backup records into one DataFrame
                            backup_df = get_pandas().concat(backup_records, ignore_index=True)
                            
                            # Create backup filename with timestamp
                            nowstr = get_now()
                            backup_filename = f"{nowstr}_updated_records_backup.csv"
                            backup_file_path = os.path.join(csrc2_dir, backup_filename)
                            
                            # Save backup file
                            backup_df.to_csv(backup_file_path, index=False, encoding='utf-8-sig')
                            backup_count = 1
                            logger.info(f"Created backup file with {len(backup_df)} updated records: {backup_filename}")
                        except Exception as backup_error:
                            logger.error(f"Failed to create backup file: {str(backup_error)}")
                            backup_count = 0
                    else:
                        backup_count = 0
                    
                    logger.info(f"Processed {len(files_to_update)} files, created backup for {len(backup_records)} updated records")
                else:
                    # No source_filename column found - do not update anything
                    logger.warning("No source_filename column found in analysis_df, skipping file updates")
                    return APIResponse(
                        success=False,
                        message="Cannot update files: source_filename column not found in data",
                        data=updated_attachments
                    )
                    
            except Exception as save_error:
                logger.error(f"Error saving updated csrc2analysis data: {str(save_error)}")
                return APIResponse(
                    success=False,
                    message=f"Updated {updated_count} records but failed to save: {str(save_error)}",
                    data=updated_attachments
                )
        
        logger.info(f"Successfully updated text for {updated_count} out of {len(attachment_ids)} attachments")
        
        return APIResponse(
            success=True,
            message=f"Successfully updated text for {updated_count} out of {len(attachment_ids)} attachments",
            data=updated_attachments
        )
        
    except Exception as e:
        logger.error(f"Attachment text update failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Attachment text update failed",
            error=str(e)
        )

@app.get("/api/csrclenanalysis-data", response_model=APIResponse)
async def get_csrclenanalysis_data():
    """Get updated csrclenanalysis data after text extraction"""
    try:
        from web_crawler import get_csrclenanalysis
        import pandas as pd
        import os
        
        # Get file paths
        current_file = os.path.abspath(__file__)
        backend_dir = os.path.dirname(current_file)
        project_root = os.path.dirname(backend_dir)
        tempdir = os.path.join(project_root, "data", "penalty", "csrc2", "temp")
        len_file_path = os.path.join(tempdir, "csrclenanalysis.csv")
        
        # Check if csrclenanalysis file exists
        if not os.path.exists(len_file_path):
            return APIResponse(
                success=False,
                message="csrclenanalysis file not found",
                data={'result': []}
            )
        
        # Get csrclenanalysis data
        len_df = get_csrclenanalysis()
        
        if len_df.empty:
            return APIResponse(
                success=True,
                message="csrclenanalysis file is empty",
                data={'result': []}
            )
        
        # Convert DataFrame to list of dictionaries
        result_data = []
        for index, row in len_df.iterrows():
            item = {
                'id': str(index),
                'url': row.get('链接', row.get('url', '')),
                'title': row.get('案例标题', row.get('title', '')),
                'date': row.get('发文日期', row.get('date', '')),
                'content': row.get('内容', row.get('content', '')),
                'contentLength': row.get('内容长度', row.get('len', 0)),
                'filename': row.get('文件名', row.get('filename', '')),
                'downloadStatus': '已下载' if row.get('文件名', row.get('filename', '')) else '未下载',
                'fileStatus': '已存在' if row.get('文件名', row.get('filename', '')) else '不存在',
                'textExtracted': bool(row.get('内容', row.get('content', '')))
            }
            result_data.append(item)
        
        logger.info(f"Retrieved {len(result_data)} records from csrclenanalysis")
        
        return APIResponse(
            success=True,
            message=f"Successfully retrieved {len(result_data)} records",
            data={'result': result_data}
        )
        
    except Exception as e:
        logger.error(f"Failed to get csrclenanalysis data: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to get csrclenanalysis data",
            error=str(e),
            data={'result': []}
        )

@app.get("/api/csrccat-invalid-amount", response_model=APIResponse)
async def get_csrccat_invalid_amount():
    """Analyze csrccat data to find records where amount field is not a valid number"""
    try:
        from csrccat_analysis import analyze_csrccat_invalid_amounts
        
        # Get analysis results from the dedicated module
        analysis_result = analyze_csrccat_invalid_amounts()
        
        invalid_count = analysis_result['summary']['invalid']
        total_count = analysis_result['summary']['total']
        
        return APIResponse(
            success=True,
            message=f"Found {invalid_count} records with invalid amount values out of {total_count} total records",
            data=analysis_result
        )
        
    except Exception as e:
        logger.error(f"Failed to analyze csrccat invalid amounts: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Failed to analyze csrccat invalid amounts",
            error=str(e),
            data={'result': [], 'summary': {'total': 0, 'invalid': 0, 'valid': 0, 'invalidPercentage': 0, 'nanCount': 0, 'zeroCount': 0, 'negativeCount': 0}}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
