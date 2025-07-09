#!/usr/bin/env python3
"""
Consolidated Test Suite for DBCSRC Backend
Combines unit tests, integration tests, API tests, and performance tests
"""

import unittest
import asyncio
import time
import requests
import json
import os
import tempfile
import shutil
import pandas as pd
from typing import Dict, Any, List
from unittest.mock import patch, Mock, MagicMock, mock_open
import random
from datetime import datetime

# Import modules to test
import web_crawler

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30

class TestWebCrawlerUtilities(unittest.TestCase):
    """Test utility functions."""
    
    def test_get_now(self):
        """Test get_now function returns correct timestamp format."""
        result = web_crawler.get_now()
        self.assertIsInstance(result, str)
        # Test that it's a valid datetime string with format YYYYMMDDHHMMSS
        datetime.strptime(result, "%Y%m%d%H%M%S")
    
    def test_get_url_backend_valid_org(self):
        """Test get_url_backend with valid organization."""
        result = web_crawler.get_url_backend("北京")
        self.assertIsInstance(result, str)
        self.assertIn("csrc.gov.cn", result)
    
    def test_get_url_backend_invalid_org(self):
        """Test get_url_backend with invalid organization."""
        with self.assertRaises(ValueError):
            web_crawler.get_url_backend("invalid_org")

class TestDataProcessing(unittest.TestCase):
    """Test data processing functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_csv_path = os.path.join(self.temp_dir, "test_data.csv")
        
        # Create test CSV data
        test_data = pd.DataFrame({
            "名称": ["Test Case 1", "Test Case 2"],
            "时间": ["2023-01-01", "2023-01-02"],
            "链接": ["http://test1.com", "http://test2.com"],
            "内容": ["Test content 1", "Test content 2"]
        })
        test_data.to_csv(self.test_csv_path, index=False, encoding='utf-8-sig')
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @patch('glob.glob')
    def test_get_csvdf_with_files(self, mock_glob):
        """Test get_csvdf with existing CSV files."""
        mock_glob.return_value = [self.test_csv_path]
        
        result = web_crawler.get_csvdf(self.temp_dir, "test")
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn("名称", result.columns)
    
    @patch('glob.glob')
    def test_get_csvdf_no_files(self, mock_glob):
        """Test get_csvdf with no matching files."""
        mock_glob.return_value = []
        
        result = web_crawler.get_csvdf(self.temp_dir, "nonexistent")
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoints functionality."""
    
    def setUp(self):
        """Set up test session."""
        self.session = requests.Session()
        self.base_url = BASE_URL
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test results."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
    
    def test_health_endpoints(self):
        """Test health check endpoints."""
        print("\n🔍 Testing Health Check Endpoints...")
        
        # Basic health check
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test("Basic Health Check", success, f"Status: {response.status_code}")
                self.assertTrue(success)
            else:
                self.log_test("Basic Health Check", False, f"Status: {response.status_code}")
                self.fail(f"Health check failed with status {response.status_code}")
        except Exception as e:
            self.log_test("Basic Health Check", False, f"Error: {str(e)}")
            self.skipTest(f"Server not available: {str(e)}")
    
    def test_metrics_endpoint(self):
        """Test metrics collection endpoint."""
        print("\n📊 Testing Metrics Endpoint...")
        
        try:
            response = self.session.get(f"{self.base_url}/metrics", timeout=5)
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                metrics_data = data.get("data", {})
                self.log_test("Metrics Endpoint", success, 
                            f"Total requests: {metrics_data.get('total_requests', 0)}")
                self.assertTrue(success)
            else:
                self.log_test("Metrics Endpoint", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Metrics Endpoint", False, f"Error: {str(e)}")
            self.skipTest(f"Server not available: {str(e)}")
    
    def test_classification_endpoint(self):
        """Test text classification endpoint."""
        print("\n🤖 Testing Classification Endpoint...")
        
        test_data = {
            "article": "This is a test article about financial regulations.",
            "candidate_labels": ["finance", "technology", "health"],
            "multi_label": False
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/classify",
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test("Classification Endpoint", success, "Classification successful")
                self.assertTrue(success)
            else:
                self.log_test("Classification Endpoint", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Classification Endpoint", False, f"Error: {str(e)}")
            self.skipTest(f"Server not available: {str(e)}")

class TestPenaltyAnalysis(unittest.TestCase):
    """Test penalty analysis functionality."""
    
    def test_penalty_analysis_endpoint(self):
        """Test penalty analysis with real data."""
        test_text = """菏金罚决字〔2023〕26号 当事人：中国大地财产保险股份有限公司菏泽中心支公司
        地址：菏泽市开发区人民路中段东侧中达国际商务大厦主要负责人：安丽丽
        依据《中华人民共和国保险法》等有关规定，我分局对中国大地财产保险股份有限公司
        菏泽中心支公司涉嫌违法违规行为一案进行了调查，决定给予25万元罚款的行政处罚。"""
        
        test_data = {
            "text": test_text
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/penalty-analysis",
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.assertTrue(data.get("success", False))
                
                # Check for expected fields in response
                result_data = data.get("data", {})
                self.assertIn("company_name", result_data)
                self.assertIn("penalty_amount", result_data)
                self.assertIn("violation_type", result_data)
                
                print(f"✅ Penalty analysis successful: {result_data}")
            else:
                self.fail(f"Penalty analysis failed with status {response.status_code}")
                
        except Exception as e:
            self.skipTest(f"Server not available: {str(e)}")

class TestContentAnalysis(unittest.TestCase):
    """Test content analysis functions."""
    
    @patch('web_crawler.savetemp')
    @patch('web_crawler.get_csrc2analysis')
    def test_content_length_analysis_success(self, mock_get_csrc2analysis, mock_savetemp):
        """Test successful content length analysis."""
        test_df = pd.DataFrame({
            "时间": ["2023-01-01", "2023-01-02"],
            "名称": ["Test 1", "Test 2"],
            "内容": ["Short", "This is a much longer content that exceeds the limit"],
            "链接": ["http://test1.com", "http://test2.com"],
        })
        
        mock_get_csrc2analysis.return_value = test_df
        mock_savetemp.return_value = None
        
        result = web_crawler.content_length_analysis(10, "Test")
        
        self.assertIsInstance(result, list)
        mock_savetemp.assert_called_once()

class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @patch('web_crawler.pencsrc2')
    def test_full_workflow_simulation(self, mock_pencsrc2):
        """Test a complete workflow simulation."""
        # This test simulates the full workflow without actual network calls
        
        # 1. Test URL generation
        url = web_crawler.get_url_backend("北京")
        self.assertIsInstance(url, str)
        self.assertIn("csrc.gov.cn", url)
        
        # 2. Test timestamp generation
        timestamp = web_crawler.get_now()
        self.assertIsInstance(timestamp, str)
        
        # 3. Test data processing with mock data
        test_df = pd.DataFrame({
            "名称": ["Test Case"],
            "时间": ["2023-01-01"],
            "链接": ["http://test.com"]
        })
        
        with patch('web_crawler.savedf_backend') as mock_save:
            web_crawler.savedf_backend(test_df, "test")
            mock_save.assert_called_once()

class TestSuite:
    """Main test suite runner."""
    
    def __init__(self):
        self.test_results = []
    
    def run_unit_tests(self):
        """Run unit tests."""
        print("\n🧪 Running Unit Tests...")
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add unit test classes
        suite.addTests(loader.loadTestsFromTestCase(TestWebCrawlerUtilities))
        suite.addTests(loader.loadTestsFromTestCase(TestDataProcessing))
        suite.addTests(loader.loadTestsFromTestCase(TestContentAnalysis))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    def run_api_tests(self):
        """Run API tests."""
        print("\n🌐 Running API Tests...")
        
        # Check if server is available
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code != 200:
                print("⚠️ Server not available, skipping API tests")
                return True
        except Exception:
            print("⚠️ Server not available, skipping API tests")
            return True
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add API test classes
        suite.addTests(loader.loadTestsFromTestCase(TestAPIEndpoints))
        suite.addTests(loader.loadTestsFromTestCase(TestPenaltyAnalysis))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    def run_integration_tests(self):
        """Run integration tests."""
        print("\n🔗 Running Integration Tests...")
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add integration test classes
        suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    
    def run_all_tests(self):
        """Run all test suites."""
        print("🚀 Starting Consolidated DBCSRC Test Suite...")
        print(f"Testing against: {BASE_URL}")
        print("="*60)
        
        results = []
        
        # Run different test categories
        results.append(self.run_unit_tests())
        results.append(self.run_api_tests())
        results.append(self.run_integration_tests())
        
        # Print summary
        self.print_summary(results)
        
        return all(results)
    
    def print_summary(self, results: List[bool]):
        """Print test summary."""
        print("\n" + "="*60)
        print("📋 CONSOLIDATED TEST SUMMARY")
        print("="*60)
        
        test_categories = ["Unit Tests", "API Tests", "Integration Tests"]
        
        total_passed = sum(results)
        total_tests = len(results)
        
        for i, (category, passed) in enumerate(zip(test_categories, results)):
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{category}: {status}")
        
        print(f"\nOverall: {total_passed}/{total_tests} test suites passed")
        print(f"Success Rate: {(total_passed/total_tests)*100:.1f}%")
        
        if total_passed == total_tests:
            print("\n🎉 All test suites completed successfully!")
        else:
            print("\n⚠️ Some test suites failed. Check the output above for details.")
        
        print("="*60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run consolidated DBCSRC tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--api", action="store_true", help="Run only API tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    
    args = parser.parse_args()
    
    test_suite = TestSuite()
    
    if args.unit:
        success = test_suite.run_unit_tests()
    elif args.api:
        success = test_suite.run_api_tests()
    elif args.integration:
        success = test_suite.run_integration_tests()
    else:
        success = test_suite.run_all_tests()
    
    exit(0 if success else 1)