#!/usr/bin/env python3
"""
Performance testing suite for DBCSRC Enhanced API using Locust
Tests various endpoints under different load conditions
"""

import json
import random
import time

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner

# Test data for various endpoints
TEST_DATA = {
    "classify_requests": [
        {
            "article": "This is a sample legal document about contract disputes and commercial law.",
            "candidate_labels": ["contract", "criminal", "civil", "commercial"],
            "multi_label": False,
        },
        {
            "article": "Criminal case involving theft and burglary charges in the metropolitan area.",
            "candidate_labels": ["criminal", "civil", "administrative", "family"],
            "multi_label": True,
        },
        {
            "article": "Family law case regarding child custody and divorce proceedings.",
            "candidate_labels": ["family", "criminal", "civil", "administrative"],
            "multi_label": False,
        },
    ],
    "batch_classify_requests": [
        {
            "texts": [
                "Contract violation case in commercial court.",
                "Personal injury lawsuit filed yesterday.",
                "Intellectual property dispute ongoing.",
            ],
            "candidate_labels": ["contract", "tort", "ip", "criminal"],
        }
    ],
    "amount_analysis_requests": [
        {
            "text": "The plaintiff seeks damages of $50,000 for breach of contract and additional $10,000 in legal fees."
        },
        {
            "text": "Settlement amount agreed upon: two hundred thousand dollars ($200,000) plus court costs."
        },
    ],
    "location_analysis_requests": [
        {
            "text": "The incident occurred in New York City, specifically in Manhattan district court."
        },
        {"text": "Case filed in Los Angeles Superior Court, California jurisdiction."},
    ],
    "people_analysis_requests": [
        {
            "text": "Judge Smith presided over the case with attorneys John Doe and Jane Smith representing the parties."
        },
        {
            "text": "Plaintiff Michael Johnson vs Defendant ABC Corporation, represented by law firm Wilson & Associates."
        },
    ],
}


class DBCSRCUser(HttpUser):
    """Simulated user for DBCSRC API performance testing"""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Called when a user starts"""
        self.client.verify = False  # Disable SSL verification for testing

    @task(3)
    def health_check(self):
        """Test basic health check endpoint (high frequency)"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure("Health check returned success=False")
            else:
                response.failure(
                    f"Health check failed with status {response.status_code}"
                )

    @task(1)
    def detailed_health_check(self):
        """Test detailed health check endpoint"""
        with self.client.get("/health/detailed", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "data" in data:
                    response.success()
                else:
                    response.failure("Detailed health check missing data")
            else:
                response.failure(
                    f"Detailed health check failed with status {response.status_code}"
                )

    @task(1)
    def metrics_endpoint(self):
        """Test metrics endpoint"""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "data" in data:
                    response.success()
                else:
                    response.failure("Metrics endpoint missing data")
            else:
                response.failure(
                    f"Metrics endpoint failed with status {response.status_code}"
                )

    @task(5)
    def classify_text(self):
        """Test text classification endpoint"""
        request_data = random.choice(TEST_DATA["classify_requests"])

        with self.client.post(
            "/classify", json=request_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "data" in data:
                    response.success()
                else:
                    response.failure("Classification failed or missing data")
            else:
                response.failure(
                    f"Classification failed with status {response.status_code}"
                )

    @task(2)
    def batch_classify(self):
        """Test batch classification endpoint"""
        request_data = random.choice(TEST_DATA["batch_classify_requests"])

        with self.client.post(
            "/batch-classify", json=request_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "data" in data:
                    response.success()
                else:
                    response.failure("Batch classification failed or missing data")
            else:
                response.failure(
                    f"Batch classification failed with status {response.status_code}"
                )

    @task(2)
    def amount_analysis(self):
        """Test amount analysis endpoint"""
        request_data = random.choice(TEST_DATA["amount_analysis_requests"])

        with self.client.post(
            "/amount-analysis", json=request_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure("Amount analysis failed")
            else:
                response.failure(
                    f"Amount analysis failed with status {response.status_code}"
                )

    @task(2)
    def location_analysis(self):
        """Test location analysis endpoint"""
        request_data = random.choice(TEST_DATA["location_analysis_requests"])

        with self.client.post(
            "/location-analysis", json=request_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure("Location analysis failed")
            else:
                response.failure(
                    f"Location analysis failed with status {response.status_code}"
                )

    @task(2)
    def people_analysis(self):
        """Test people analysis endpoint"""
        request_data = random.choice(TEST_DATA["people_analysis_requests"])

        with self.client.post(
            "/people-analysis", json=request_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure("People analysis failed")
            else:
                response.failure(
                    f"People analysis failed with status {response.status_code}"
                )

    @task(1)
    def test_rate_limiting(self):
        """Test rate limiting by making rapid requests"""
        # Make multiple rapid requests to test rate limiting
        for i in range(5):
            with self.client.get("/health", catch_response=True) as response:
                if response.status_code == 429:
                    response.success()  # Rate limiting is working
                    break
                elif response.status_code == 200:
                    continue  # Normal response
                else:
                    response.failure(f"Unexpected status code: {response.status_code}")
                    break
            time.sleep(0.1)  # Small delay between rapid requests

    @task(1)
    def test_invalid_requests(self):
        """Test error handling with invalid requests"""
        # Test invalid JSON
        with self.client.post(
            "/classify",
            data="invalid json",
            headers={"Content-Type": "application/json"},
            catch_response=True,
        ) as response:
            if response.status_code in [400, 422]:
                response.success()  # Expected error response
            else:
                response.failure(
                    f"Expected 400/422 for invalid JSON, got {response.status_code}"
                )

        # Test missing required fields
        with self.client.post("/classify", json={}, catch_response=True) as response:
            if response.status_code in [400, 422]:
                response.success()  # Expected validation error
            else:
                response.failure(
                    f"Expected 400/422 for missing fields, got {response.status_code}"
                )


class StressTestUser(HttpUser):
    """High-load stress testing user"""

    wait_time = between(0.1, 0.5)  # Very short wait times for stress testing

    @task
    def stress_health_check(self):
        """Rapid health check requests for stress testing"""
        self.client.get("/health")

    @task
    def stress_classify(self):
        """Rapid classification requests for stress testing"""
        request_data = random.choice(TEST_DATA["classify_requests"])
        self.client.post("/classify", json=request_data)


# Event handlers for performance monitoring
@events.request.add_listener
def on_request(
    request_type, name, response_time, response_length, exception, context, **kwargs
):
    """Log performance metrics for each request"""
    if exception:
        print(f"Request failed: {request_type} {name} - {exception}")
    elif response_time > 2000:  # Log slow requests (>2 seconds)
        print(f"Slow request detected: {request_type} {name} - {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("🚀 Starting DBCSRC API performance tests...")
    print(f"Target host: {environment.host}")

    if isinstance(environment.runner, MasterRunner):
        print(
            f"Running in distributed mode with {environment.runner.worker_count} workers"
        )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("\n📊 Performance test completed!")

    # Print summary statistics
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {stats.total.current_rps:.2f}")

    # Check if performance thresholds are met
    if stats.total.avg_response_time > 1000:  # 1 second threshold
        print("⚠️  WARNING: Average response time exceeds 1 second")

    if (
        stats.total.num_failures / stats.total.num_requests > 0.01
    ):  # 1% error rate threshold
        print("⚠️  WARNING: Error rate exceeds 1%")

    if stats.total.current_rps < 10:  # Minimum 10 RPS threshold
        print("⚠️  WARNING: Request rate below 10 RPS")


if __name__ == "__main__":
    print(
        "Use 'locust -f performance_tests.py --host=http://localhost:8000' to run tests"
    )
    print("\nExample commands:")
    print("  # Web UI mode:")
    print("  locust -f performance_tests.py --host=http://localhost:8000")
    print("\n  # Headless mode:")
    print(
        "  locust -f performance_tests.py --headless --users 50 --spawn-rate 5 --run-time 60s --host=http://localhost:8000"
    )
    print("\n  # Stress test:")
    print(
        "  locust -f performance_tests.py --headless --users 100 --spawn-rate 10 --run-time 120s --host=http://localhost:8000 StressTestUser"
    )
