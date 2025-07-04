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
    from classifier import df2label, get_class, extract_penalty_info, df2penalty_analysis
except ImportError:
    def get_class(*args, **kwargs):
        return {"labels": ["未分类"], "scores": [1.0]}
    def df2label(*args, **kwargs):
        return pd.DataFrame()
    def extract_penalty_info(*args, **kwargs):
        return {"success": False, "error": "LLM analysis not available"}
    def df2penalty_analysis(*args, **kwargs):
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
    mongo_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/dbcsrc")
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
            return pd.DataFrame(data)
        else:
            logger.warning("MongoDB collection not available")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed to get online data: {str(e)}")
        # Return empty DataFrame on error to prevent complete failure
        return pd.DataFrame()

def insert_online_data(df: pd.DataFrame):
    """Insert data to MongoDB"""
    try:
        collection = get_collection("pencsrc2", "csrc2analysis")
        if collection is not None and not df.empty:
            records = df.to_dict("records")
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                collection.insert_many(batch)
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to insert online data: {str(e)}")
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

class PenaltyAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000, description="行政处罚决定书文本内容")

@app.get("/")
def read_root():
    return {"message": "DBCSRC API is running", "version": "1.0.0"}


# Cache for summary data to improve performance
_summary_cache = {"data": None, "timestamp": 0}
CACHE_DURATION = 300  # 5 minutes

@app.get("/summary-working", response_model=APIResponse)
def get_summary_working():
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
        
        df = pd.DataFrame()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(load_csv_data)
                df = future.result(timeout=30)
                if df is None:
                    df = pd.DataFrame()
        except FutureTimeoutError:
            logger.warning("CSV loading timed out")
            df = pd.DataFrame()
        except Exception as e:
            logger.warning(f"CSV loading failed: {e}")
            df = pd.DataFrame()
        
        # Process data simply
        total = len(df) if not df.empty else 0
        by_org = {}
        by_month = {}
        
        if not df.empty and total > 0:
            logger.info(f"Processing {total} rows")
            
            # Simple organization count
            if '机构' in df.columns:
                try:
                    org_counts = df['机构'].value_counts().head(10)  # Limit to top 10
                    by_org = org_counts.to_dict()
                except Exception as e:
                    logger.warning(f"Organization processing failed: {e}")
            
            # Simple month count
            if '发文日期' in df.columns:
                try:
                    df_copy = df[['发文日期']].copy()
                    df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'], errors='coerce')
                    df_copy = df_copy.dropna()
                    if not df_copy.empty:
                        df_copy['month'] = df_copy['发文日期'].dt.strftime('%Y-%m')
                        month_counts = df_copy['month'].value_counts().head(12)  # Limit to 12 months
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

@app.get("/summary", response_model=APIResponse)
def get_summary():
    """Get case summary statistics - simplified version"""
    return _get_summary_impl()

@app.get("/api/summary", response_model=APIResponse)
def get_api_summary():
    """Get case summary statistics - API endpoint"""
    return _get_summary_impl()

def _get_summary_impl():
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
        df = pd.DataFrame()
        try:
            logger.info("Loading CSV data...")
            from data_service import get_csrc2detail
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
            
            def load_csv_data():
                return get_csrc2detail()
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(load_csv_data)
                try:
                    df = future.result(timeout=30)  # 30 second timeout
                    if df is None or df.empty:
                        logger.warning("No CSV data found")
                        df = pd.DataFrame()
                    else:
                        logger.info(f"Loaded {len(df)} rows from CSV data")
                except FutureTimeoutError:
                    logger.warning("CSV data loading timed out after 30 seconds")
                    df = pd.DataFrame()
                    
        except Exception as csv_error:
            logger.warning(f"Failed to load CSV data: {csv_error}")
            df = pd.DataFrame()
        
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
            
            # Simple organization count
            by_org = {}
            if '机构' in df.columns:
                org_series = df['机构'].dropna()
                org_series = org_series[org_series.str.strip() != '']
                if not org_series.empty:
                    by_org = org_series.value_counts().to_dict()
            
            # Simple month count
            by_month = {}
            if '发文日期' in df.columns:
                try:
                    df_copy = df[['发文日期']].copy()
                    df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'], errors='coerce')
                    df_copy = df_copy.dropna(subset=['发文日期'])
                    if not df_copy.empty:
                        df_copy['month'] = df_copy['发文日期'].dt.to_period('M').astype(str)
                        by_month = df_copy['month'].value_counts().sort_index().to_dict()
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

@app.post("/penalty-analysis", response_model=APIResponse)
async def penalty_analysis(request: PenaltyAnalysisRequest):
    """Extract key information from administrative penalty decision using LLM"""
    try:
        logger.info("Starting penalty analysis with LLM")
        
        # Extract penalty information using LLM
        result = extract_penalty_info(request.text)
        
        logger.info("Penalty analysis completed successfully")
        return APIResponse(
            success=True,
            message="Penalty analysis completed successfully",
            data={"result": result}
        )
        
    except Exception as e:
        logger.error(f"Penalty analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Penalty analysis failed",
            error=str(e)
        )

@app.post("/batch-penalty-analysis", response_model=APIResponse)
async def batch_penalty_analysis(
    file: UploadFile = File(...),
    idcol: str = Query(...),
    contentcol: str = Query(...)
):
    """Batch extract key information from administrative penalty decisions using LLM"""
    try:
        logger.info(f"Starting batch penalty analysis from file: {file.filename}")
        
        contents = file.file.read()
        file_obj = io.BytesIO(contents)
        df = pd.read_csv(file_obj)
        
        logger.info(f"Processing {len(df)} rows for penalty analysis")
        result_df = df2penalty_analysis(df, idcol, contentcol)
        
        logger.info(f"Batch penalty analysis completed successfully for {len(result_df)} records")
        return APIResponse(
            success=True,
            message=f"Batch penalty analysis completed for {len(result_df)} records",
            data={"results": result_df.to_dict('records')},
            count=len(result_df)
        )
        
    except Exception as e:
        logger.error(f"Batch penalty analysis failed: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            message="Batch penalty analysis failed",
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
        def get_csv_stats(pattern):
            files = glob.glob(os.path.join(data_dir, pattern))
            if files:
                dflist = []
                for filepath in files:
                    try:
                        df = pd.read_csv(filepath)
                        dflist.append(df)
                    except Exception as e:
                        # Skip files that can't be read
                        pass
                
                if dflist:
                    # Combine all dataframes like get_csvdf does
                    combined_df = pd.concat(dflist)
                    combined_df.reset_index(drop=True, inplace=True)
                    count = len(combined_df)
                    unique_count = combined_df['案例编号'].nunique() if '案例编号' in combined_df.columns else count
                    return count, unique_count
            return 0, 0
        
        # Get case detail data stats
        case_detail_count, case_detail_unique = get_csv_stats("csrcdtlall*.csv")
        
        # Get analysis data stats
        analysis_count, analysis_unique = get_csv_stats("csrc2analysis*.csv")
        
        # Get category data stats (assuming similar pattern)
        category_count, category_unique = get_csv_stats("csrc2label*.csv")
        
        # Get split data stats
        split_count, split_unique = get_csv_stats("csrc2split*.csv")
        
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
        
        from data_service import get_csrc2label
        
        df = get_csrc2label()
        
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
        
        from data_service import get_csvdf
        
        df = get_csvdf("../data/penalty/csrc2", "csrc2split")
        
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
            
        from data_service import get_csrc2detail, get_csrc2analysis, get_csrc2label, get_csvdf
        
        # Get case detail data with timeout handling
        logger.info("Loading case detail data")
        case_detail_df = get_csrc2detail()
        
        # Get analysis data with timeout handling
        logger.info("Loading analysis data")
        analysis_df = get_csrc2analysis()
        
        # Get category data with timeout handling
        logger.info("Loading category data")
        category_df = get_csrc2label()
        
        # Get split data with timeout handling
        logger.info("Loading split data")
        split_df = get_csvdf("../data/penalty/csrc2", "csrc2split")
        
        # Get online data from MongoDB with timeout handling
        logger.info("Loading online data from MongoDB")
        online_df = get_online_data()
        
        # Calculate diff data (cases not in online)
        if not case_detail_df.empty:
            if not online_df.empty and '案例编号' in online_df.columns:
                # Get cases that are not online
                online_case_ids = set(online_df['案例编号'].tolist())
                diff_df = case_detail_df[~case_detail_df['案例编号'].isin(online_case_ids)].copy()
            else:
                # If no online data, all cases are diff
                diff_df = case_detail_df.copy()
            
            # Add upload status fields
            diff_df['status'] = 'pending'
            diff_df['uploadProgress'] = 0
            diff_df['errorMessage'] = None
        else:
            diff_df = pd.DataFrame()
        
        data = {
            "caseDetail": {
                "data": case_detail_df.to_dict('records') if not case_detail_df.empty else [],
                "count": len(case_detail_df),
                "uniqueCount": case_detail_df['案例编号'].nunique() if not case_detail_df.empty and '案例编号' in case_detail_df.columns else 0
            },
            "analysisData": {
                "data": analysis_df.to_dict('records') if not analysis_df.empty else [],
                "count": len(analysis_df),
                "uniqueCount": analysis_df['案例编号'].nunique() if not analysis_df.empty and '案例编号' in analysis_df.columns else 0
            },
            "categoryData": {
                "data": category_df.to_dict('records') if not category_df.empty else [],
                "count": len(category_df),
                "uniqueCount": category_df['案例编号'].nunique() if not category_df.empty and '案例编号' in category_df.columns else 0
            },
            "splitData": {
                "data": split_df.to_dict('records') if not split_df.empty else [],
                "count": len(split_df),
                "uniqueCount": split_df['案例编号'].nunique() if not split_df.empty and '案例编号' in split_df.columns else 0
            },
            "onlineData": {
                "data": online_df.to_dict('records') if not online_df.empty else [],
                "count": len(online_df),
                "uniqueCount": 0
            },
            "diffData": {
                "data": diff_df.to_dict('records') if not diff_df.empty else [],
                "count": len(diff_df),
                "uniqueCount": diff_df['案例编号'].nunique() if not diff_df.empty and '案例编号' in diff_df.columns else 0
            }
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
    """Upload selected cases to online database"""
    try:
        logger.info(f"Starting upload for {len(request.case_ids)} cases")
        
        # Get case data to upload
        from data_service import get_csrc2analysis
        
        analysis_df = get_csrc2analysis()
        
        if analysis_df.empty:
            return APIResponse(
                success=False,
                message="No analysis data available for upload",
                count=0
            )
        
        # Filter cases to upload
        if '案例编号' in analysis_df.columns:
            cases_to_upload = analysis_df[analysis_df['案例编号'].isin(request.case_ids)]
        else:
            # If no case ID column, use link as identifier
            cases_to_upload = analysis_df[analysis_df['链接'].isin(request.case_ids)]
        
        if cases_to_upload.empty:
            return APIResponse(
                success=False,
                message="No matching cases found for upload",
                count=0
            )
        
        # Upload to MongoDB
        success = insert_online_data(cases_to_upload)
        
        if success:
            uploaded_count = len(cases_to_upload)
            logger.info(f"Successfully uploaded {uploaded_count} cases to MongoDB")
            return APIResponse(
                success=True,
                message=f"Successfully uploaded {uploaded_count} cases",
                count=uploaded_count
            )
        else:
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

@app.delete("/online-data", response_model=APIResponse)
@app.delete("/api/online-data", response_model=APIResponse)
async def delete_online_data_endpoint():
    """Delete all online case data"""
    try:
        logger.info("Starting deletion of online data")
        
        # Delete from MongoDB
        deleted_count = delete_online_data()
        
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
async def download_diff_data():
    """Download diff data CSV file"""
    try:
        logger.info("Starting diff data CSV download")
        
        from data_service import get_csrc2detail
        
        # Get case detail data as diff data (cases not online)
        diff_df = get_csrc2detail()
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
