"""
Quick API test script for Flask backend.

Tests all endpoints to ensure the RAG system is working.
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:5000/api"

def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def test_health():
    """Test health check endpoint."""
    print_section("Testing Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Overall Status: {result.get('status')}")
        print("\nServices:")
        for service, status in result.get('services', {}).items():
            print(f"  • {service}: {status.get('status')}")
            if 'model' in status:
                print(f"    Model: {status['model']}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_ping():
    """Test ping endpoint."""
    print_section("Testing Ping")
    
    try:
        response = requests.get(f"{BASE_URL}/ping", timeout=5)
        result = response.json()
        
        print(f"Status: {result.get('status')}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ping failed: {e}")
        return False

def test_upload(pdf_path: str = None):
    """Test PDF upload endpoint."""
    print_section("Testing PDF Upload")
    
    if not pdf_path:
        print("⚠️  No PDF path provided, skipping upload test")
        print("To test upload, provide PDF path: python test_flask_api.py <path_to_pdf>")
        return True
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    try:
        print(f"Uploading: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            data = {
                'company': 'TestCorp',
                'period': '2024Q3'
            }
            
            response = requests.post(
                f"{BASE_URL}/upload",
                files=files,
                data=data,
                timeout=300  # 5 minutes for processing
            )
        
        result = response.json()
        
        if response.status_code == 200:
            print("✓ Upload successful!")
            print("\nStatistics:")
            stats = result.get('statistics', {})
            print(f"  • Company: {stats.get('company')}")
            print(f"  • Period: {stats.get('period')}")
            print(f"  • Text chunks: {stats.get('text_chunks')}")
            print(f"  • Table chunks: {stats.get('table_chunks')}")
            print(f"  • Total chunks: {stats.get('total_chunks')}")
            print(f"  • Embedding dimension: {stats.get('embedding_dimension')}")
            return True
        else:
            print(f"❌ Upload failed: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def test_chat(query: str = "What is the revenue?"):
    """Test chat endpoint."""
    print_section("Testing Chat Query")
    
    try:
        print(f"Query: {query}")
        
        payload = {
            "query": query,
            "session_id": "test-session-123",
            "top_k": 3
        }
        
        print("\nSending request...")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=120
        )
        
        elapsed_time = time.time() - start_time
        result = response.json()
        
        if response.status_code == 200:
            print(f"✓ Chat successful! (took {elapsed_time:.2f}s)")
            
            print(f"\nAnswer:")
            print(f"  {result.get('answer', '')[:300]}...")
            
            print(f"\nSources Retrieved: {result.get('metadata', {}).get('chunks_retrieved', 0)}")
            
            sources = result.get('sources', [])
            if sources:
                print("\nTop Sources:")
                for i, source in enumerate(sources[:3], 1):
                    print(f"\n  [{i}] Similarity: {source.get('similarity', 0):.3f}")
                    print(f"      Company: {source.get('company')}")
                    print(f"      Period: {source.get('period')}")
                    print(f"      Snippet: {source.get('snippet', '')[:100]}...")
            
            return True
        else:
            print(f"❌ Chat failed: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return False

def test_documents():
    """Test document listing endpoint."""
    print_section("Testing Document Listing")
    
    try:
        response = requests.get(f"{BASE_URL}/documents", timeout=10)
        result = response.json()
        
        if response.status_code == 200:
            print(f"✓ Listed documents successfully")
            print(f"\nTotal documents: {result.get('total_documents', 0)}")
            
            companies = result.get('companies', [])
            if companies:
                print(f"Companies: {', '.join(companies)}")
            
            return True
        else:
            print(f"❌ Listing failed")
            return False
            
    except Exception as e:
        print(f"❌ Listing error: {e}")
        return False

def main():
    """Run all tests."""
    import sys
    
    print("=" * 80)
    print("  Flask Backend API Test Suite")
    print("=" * 80)
    
    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/ping", timeout=2)
    except:
        print("\n❌ Error: Flask server is not running!")
        print("Please start the server first: python app.py")
        return
    
    results = {}
    
    # Run tests
    results['health'] = test_health()
    results['ping'] = test_ping()
    results['documents'] = test_documents()
    
    # Upload test (only if PDF path provided)
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        results['upload'] = test_upload(pdf_path)
    else:
        results['upload'] = test_upload()
    
    # Chat test
    results['chat'] = test_chat()
    
    # Summary
    print_section("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Backend is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
