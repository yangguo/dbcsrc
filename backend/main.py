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
        
        df = pd.DataFrame()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(load_csv_data)
                df = future.result(timeout=120)  # Increased to 120 second timeout
                if df is None:
                    df = pd.DataFrame()
        except FutureTimeoutError:
            logger.warning("CSV loading timed out after 120 seconds")
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
            
            # Simple organization count - show ALL organizations or limit if specified
            # Use same filtering as org-summary for consistency
            if '机构' in df.columns:
                try:
                    # Additional filtering for consistency with table data
                    if '发文日期' in df.columns:
                        # Only count organizations with valid dates for consistency
                        df_filtered = df.copy()
                        df_filtered['发文日期'] = pd.to_datetime(df_filtered['发文日期'], errors='coerce')
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
                    df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'], errors='coerce')
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
                df_copy['month'] = df_copy['发文日期'].dt.to_period('M').astype(str)
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
        df = pd.DataFrame()
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
                        df = pd.DataFrame()
                    else:
                        logger.info(f"Loaded {len(df)} rows from CSV data")
                except FutureTimeoutError:
                    logger.warning("CSV data loading timed out after 120 seconds")
                    df = pd.DataFrame()
                    
        except Exception as csv_error:
            logger.warning(f"Failed to load CSV data: {csv_error}")
            df = pd.DataFrame()
        
        org_chart_data = {}
        
        if not df.empty and '机构' in df.columns and '发文日期' in df.columns:
            # Use same filtering as org-summary for consistency
            df_copy = df.copy()
            
            # Clean and parse dates
            df_copy['发文日期'] = pd.to_datetime(df_copy['发文日期'], errors='coerce')
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

@app.get("/api/org-summary", response_model=APIResponse)
def get_org_summary():
    """Get organization summary with case counts and date ranges"""
    try:
        logger.info("Fetching organization summary with date ranges")
        
        # Get case detail data from CSV files
        df = pd.DataFrame()
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
                        df = pd.DataFrame()
                    else:
                        logger.info(f"Loaded {len(df)} rows from CSV data")
                except FutureTimeoutError:
                    logger.warning("CSV data loading timed out after 120 seconds")
                    df = pd.DataFrame()
                    
        except Exception as csv_error:
            logger.warning(f"Failed to load CSV data: {csv_error}")
            df = pd.DataFrame()
        
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
                        'minDate': row['minDate'].strftime('%Y-%m') if pd.notna(row['minDate']) else '',
                        'maxDate': row['maxDate'].strftime('%Y-%m') if pd.notna(row['maxDate']) else '',
                        'dateRange': f"{row['minDate'].strftime('%Y-%m')} 至 {row['maxDate'].strftime('%Y-%m')}" if pd.notna(row['minDate']) and pd.notna(row['maxDate']) else '暂无数据'
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
                    df = future.result(timeout=120)  # Increased to 120 second timeout
                    if df is None or df.empty:
                        logger.warning("No CSV data found")
                        df = pd.DataFrame()
                    else:
                        logger.info(f"Loaded {len(df)} rows from CSV data")
                except FutureTimeoutError:
                    logger.warning("CSV data loading timed out after 120 seconds")
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
                        df_copy['month'] = df_copy['发文日期'].dt.to_period('M').astype(str)
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
            data={"result": {"data": result_df.to_dict('records')}},
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
        def get_csv_stats(pattern, unique_id_column):
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
                intersection_df = pd.merge(
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
                    
                    intersection_df = pd.merge(
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
                    diff_df = pd.DataFrame()
            else:
                logger.warning("Missing required datasets for three-table intersection")
                logger.info(f"Data availability: analysis={not analysis_df.empty}, category={not category_df.empty}, split={not split_df.empty}")
                diff_df = pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error calculating three-table intersection: {str(e)}")
            diff_df = pd.DataFrame()
        
        # Add upload status fields
        if not diff_df.empty:
            diff_df['status'] = 'pending'
            diff_df['uploadProgress'] = 0
            diff_df['errorMessage'] = None
        
        data = {
            "caseDetail": {
                "data": case_detail_df.to_dict('records') if not case_detail_df.empty else [],
                "count": len(case_detail_df),
                "uniqueCount": case_detail_df['链接'].nunique() if not case_detail_df.empty and '链接' in case_detail_df.columns else 0
            },
            "analysisData": {
                "data": analysis_df.to_dict('records') if not analysis_df.empty else [],
                "count": len(analysis_df),
                "uniqueCount": analysis_df['链接'].nunique() if not analysis_df.empty and '链接' in analysis_df.columns else 0
            },
            "categoryData": {
                "data": category_df.to_dict('records') if not category_df.empty else [],
                "count": len(category_df),
                "uniqueCount": category_df['id'].nunique() if not category_df.empty and 'id' in category_df.columns else 0
            },
            "splitData": {
                "data": split_df.to_dict('records') if not split_df.empty else [],
                "count": len(split_df),
                "uniqueCount": split_df['id'].nunique() if not split_df.empty and 'id' in split_df.columns else 0
            },
            "onlineData": {
                "data": online_df.to_dict('records') if not online_df.empty else [],
                "count": len(online_df),
                "uniqueCount": 0
            },
            "diffData": {
                "data": diff_df.to_dict('records') if not diff_df.empty else [],
                "count": len(diff_df),
                "uniqueCount": diff_df['链接'].nunique() if not diff_df.empty and '链接' in diff_df.columns else 0
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
                diff_df = pd.merge(
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
                    
                    diff_df = pd.merge(
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
                diff_df = pd.DataFrame()
        else:
            diff_df = pd.DataFrame()
        
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
