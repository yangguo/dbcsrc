#!/usr/bin/env python3
"""
Example client to demonstrate the enhanced download API with progress tracking.
"""

import requests
import time
import json
from datetime import datetime

class DownloadClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def analyze_attachments(self, content_length=100, download_filter="决定"):
        """Analyze attachments to find downloadable items."""
        url = f"{self.base_url}/analyze-attachments"
        data = {
            "contentLength": content_length,
            "downloadFilter": download_filter
        }
        
        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error analyzing attachments: {e}")
            return None
    
    def start_download(self, positions):
        """Start attachment download and return job ID."""
        url = f"{self.base_url}/download-attachments"
        data = {"positions": positions}
        
        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result.get("data", {}).get("job_id")
            else:
                print(f"❌ Download failed: {result.get('message')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error starting download: {e}")
            return None
    
    def get_job_status(self, job_id):
        """Get job status and progress."""
        url = f"{self.base_url}/job-status/{job_id}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result.get("data")
            else:
                print(f"❌ Error getting job status: {result.get('message')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting job status: {e}")
            return None
    
    def monitor_download(self, job_id, update_interval=2):
        """Monitor download progress until completion."""
        print(f"📊 Monitoring job: {job_id}")
        print("-" * 50)
        
        while True:
            status_data = self.get_job_status(job_id)
            if not status_data:
                break
            
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            processed = status_data.get("processed_records", 0)
            total = status_data.get("total_records", 0)
            
            # Create progress bar
            bar_length = 30
            filled_length = int(bar_length * progress // 100)
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\r[{timestamp}] |{bar}| {progress}% ({processed}/{total}) - {status}", end='', flush=True)
            
            if status in ["completed", "failed"]:
                print()  # New line
                break
            
            time.sleep(update_interval)
        
        return status_data
    
    def download_with_progress(self, positions):
        """Complete download workflow with progress monitoring."""
        print("🚀 Starting Enhanced Download with Progress Tracking")
        print("=" * 60)
        
        # Start download
        print(f"📋 Requesting download of {len(positions)} attachments...")
        job_id = self.start_download(positions)
        
        if not job_id:
            print("❌ Failed to start download")
            return None
        
        print(f"✅ Download job started: {job_id}")
        
        # Monitor progress
        final_status = self.monitor_download(job_id)
        
        # Show final results
        print("\n" + "=" * 50)
        print("📈 DOWNLOAD RESULTS")
        print("=" * 50)
        
        if final_status:
            status = final_status.get("status")
            if status == "completed":
                print("✅ Download completed successfully!")
                
                # Show timing information
                created_at = final_status.get("created_at")
                completed_at = final_status.get("completed_at")
                if created_at and completed_at:
                    start_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                    duration = (end_time - start_time).total_seconds()
                    print(f"⏱️  Total duration: {duration:.2f} seconds")
                
                processed = final_status.get("processed_records", 0)
                total = final_status.get("total_records", 0)
                print(f"📁 Files processed: {processed}/{total}")
                
                # Show sample results if available
                result = final_status.get("result", [])
                if result:
                    print(f"\n📋 Sample Results (showing first 3):")
                    for i, item in enumerate(result[:3]):
                        filename = item.get('filename', 'N/A')
                        url = item.get('url', 'N/A')
                        if len(url) > 50:
                            url = url[:50] + '...'
                        print(f"  {i+1}. File: {filename}")
                        print(f"     URL: {url}")
                
            elif status == "failed":
                print("❌ Download failed!")
                error = final_status.get("error")
                if error:
                    print(f"Error: {error}")
            else:
                print(f"⚠️  Download status: {status}")
        
        return final_status

def main():
    """Main function to demonstrate the download client."""
    print("🔗 Enhanced Download API Client Demo")
    print("=" * 60)
    
    client = DownloadClient()
    
    # Test API connection
    try:
        response = requests.get(f"{client.base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API connection successful")
        else:
            print("❌ API connection failed")
            return
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API. Make sure the backend is running on http://localhost:8000")
        return
    
    print("\n1. Analyzing attachments...")
    analysis_result = client.analyze_attachments(content_length=100, download_filter="决定")
    
    if not analysis_result or not analysis_result.get("success"):
        print("❌ No attachments found or analysis failed")
        return
    
    attachments = analysis_result.get("data", [])
    if not attachments:
        print("❌ No attachments available for download")
        return
    
    print(f"✅ Found {len(attachments)} attachments")
    
    # Select first few for testing
    test_positions = list(range(min(3, len(attachments))))
    print(f"📋 Will download positions: {test_positions}")
    
    # Ask user for confirmation
    user_input = input(f"\nProceed with downloading {len(test_positions)} attachments? (y/N): ").strip().lower()
    
    if user_input != 'y':
        print("❌ Download cancelled by user")
        return
    
    # Start download with progress monitoring
    print("\n" + "🔄" * 20)
    result = client.download_with_progress(test_positions)
    
    if result:
        print("\n🎉 Demo completed successfully!")
    else:
        print("\n❌ Demo failed")

if __name__ == "__main__":
    main()