# Enhanced Download with Progress Tracking

This guide explains the enhanced attachment download functionality with progress bars and optimized logging.

## Features

### 🚀 Progress Tracking
- Real-time progress bar during downloads
- Job-based progress monitoring via API
- Detailed progress callbacks with timestamps
- File-level progress for large downloads

### 📊 Optimized Logging
- Concise, informative log messages
- Progress indicators with visual bars
- Success/failure summaries
- Reduced verbose output for better readability

### 🔄 Job Management
- Asynchronous job tracking
- Job status monitoring endpoints
- Automatic job cleanup
- Error handling and retry logic

## API Endpoints

### 1. Analyze Attachments
```http
POST /analyze-attachments
Content-Type: application/json

{
  "contentLength": 100,
  "downloadFilter": "决定"
}
```

### 2. Download Attachments
```http
POST /download-attachments
Content-Type: application/json

{
  "positions": [0, 1, 2]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Attachment download completed successfully - 3 files processed",
  "data": {
    "job_id": "uuid-string",
    "results": [...],
    "summary": {
      "total_requested": 3,
      "total_processed": 3,
      "success_rate": "100.0%"
    }
  },
  "count": 3
}
```

### 3. Job Status Monitoring
```http
GET /job-status/{job_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "uuid-string",
    "status": "running",
    "progress": 67,
    "processed_records": 2,
    "total_records": 3,
    "created_at": "2025-01-17T10:30:00",
    "started_at": "2025-01-17T10:30:01",
    "completed_at": null,
    "error": null
  }
}
```

### 4. Job Management
```http
GET /jobs                    # List all jobs
DELETE /jobs/{job_id}        # Delete specific job
DELETE /jobs                 # Cleanup old jobs
```

## Progress Bar Features

### Console Progress Bar
```
Progress: |████████████████████████------| 80.0% (4/5) - Processing attachment 4
```

### File Download Progress
```
Progress: |██████████████████████████████| 100.0% (3/3) - File progress: 75%
```

### Final Summary
```
✓ Download completed: 3 successful, 0 failed, 0 errors
Results saved to: csrcmiscontent20250117103045.csv
Total records processed: 3
```

## Usage Examples

### Python Client Example

```python
import requests
import time

class DownloadClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def download_with_progress(self, positions):
        # Start download
        response = requests.post(f"{self.base_url}/download-attachments", 
                               json={"positions": positions})
        job_id = response.json()["data"]["job_id"]
        
        # Monitor progress
        while True:
            status_response = requests.get(f"{self.base_url}/job-status/{job_id}")
            status_data = status_response.json()["data"]
            
            progress = status_data["progress"]
            status = status_data["status"]
            
            print(f"Progress: {progress}% - Status: {status}")
            
            if status in ["completed", "failed"]:
                break
            
            time.sleep(2)
        
        return status_data

# Usage
client = DownloadClient()
result = client.download_with_progress([0, 1, 2])
```

### JavaScript/Frontend Example

```javascript
class DownloadClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async downloadWithProgress(positions) {
        // Start download
        const response = await fetch(`${this.baseUrl}/download-attachments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ positions })
        });
        
        const result = await response.json();
        const jobId = result.data.job_id;
        
        // Monitor progress
        return new Promise((resolve) => {
            const checkProgress = async () => {
                const statusResponse = await fetch(`${this.baseUrl}/job-status/${jobId}`);
                const statusData = await statusResponse.json();
                
                const { progress, status } = statusData.data;
                console.log(`Progress: ${progress}% - Status: ${status}`);
                
                if (status === 'completed' || status === 'failed') {
                    resolve(statusData.data);
                } else {
                    setTimeout(checkProgress, 2000);
                }
            };
            
            checkProgress();
        });
    }
}

// Usage
const client = new DownloadClient();
client.downloadWithProgress([0, 1, 2]).then(result => {
    console.log('Download completed:', result);
});
```

## Testing

### Run Progress Test
```bash
cd backend
python test_download_progress.py
```

### Run API Client Demo
```bash
cd backend
python example_download_client.py
```

## Configuration

### Environment Variables
```env
# Optional: Adjust download timeouts
DOWNLOAD_TIMEOUT=30
DOWNLOAD_RETRIES=3
PROGRESS_UPDATE_INTERVAL=2
```

### Customization Options

#### Progress Callback
```python
def custom_progress_callback(current, total, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    percentage = (current / total) * 100
    print(f"[{timestamp}] {percentage:.1f}% - {message}")

# Use with download
result = download_attachment(positions, custom_progress_callback)
```

#### Job Storage Configuration
```python
# Customize job cleanup interval
CLEANUP_INTERVAL_HOURS = 1

# Maximum concurrent jobs
MAX_CONCURRENT_JOBS = 5
```

## Error Handling

### Common Issues and Solutions

1. **Chrome Driver Issues**
   ```
   ✓ Chrome driver initialized successfully
   ```
   - Automatic ChromeDriver management
   - Fallback to system chromedriver
   - Clear error messages

2. **Network Timeouts**
   ```
   Download attempt 1 failed for file.pdf, retrying...
   Download attempt 2 failed for file.pdf, retrying...
   Failed to download file.pdf after 3 attempts: Timeout
   ```
   - Automatic retry logic (3 attempts)
   - Configurable timeout settings
   - Graceful failure handling

3. **Job Not Found**
   ```json
   {
     "success": false,
     "message": "Job not found",
     "error": "Invalid job ID"
   }
   ```

## Performance Optimizations

### Implemented Optimizations
- Reduced wait times between downloads (1-3s vs 2-20s)
- Batch saving every 10 downloads
- Optimized Chrome driver options
- Concurrent request handling
- Memory-efficient file streaming

### Monitoring Performance
```python
# Check system resources during download
import psutil

def monitor_resources():
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    print(f"CPU: {cpu_percent}%, Memory: {memory_percent}%")
```

## Best Practices

1. **Use Job IDs for Long Downloads**
   - Always store job IDs for tracking
   - Implement proper error handling
   - Clean up completed jobs

2. **Monitor Progress Appropriately**
   - Don't poll too frequently (recommended: 2-5 seconds)
   - Handle network interruptions
   - Provide user feedback

3. **Handle Large Downloads**
   - Use batch processing for many files
   - Implement pause/resume functionality
   - Monitor system resources

4. **Error Recovery**
   - Implement retry logic
   - Log errors appropriately
   - Provide meaningful error messages

## Troubleshooting

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run download with debug info
result = download_attachment(positions, debug=True)
```

### Common Log Messages
```
Initializing Chrome driver...
✓ Chrome driver initialized successfully
Starting download of 3 attachments...
Progress: |██████████████████████████████| 100.0% (3/3) - Processing attachment 3
✓ Download completed: 3 successful, 0 failed, 0 errors
```

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify API connectivity with `/health` endpoint
3. Test with small batches first
4. Review the example scripts for proper usage