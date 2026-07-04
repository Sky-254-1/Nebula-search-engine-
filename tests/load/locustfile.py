"""
Load testing suite for Nebula Search Engine using Locust.

Performance Targets:
- Search endpoints: <500ms (p95)
- Document operations: <2s
- Authentication: <200ms
- Normal load: 10 users
- Peak load: 50 users
- Stress test: 100 users
"""

from locust import HttpUser, task, between, SequentialTaskSet
from typing import Dict, List
import json


class UserBehavior(SequentialTaskSet):
    """Simulates typical user behavior patterns."""
    
    def on_start(self):
        """Login and get access token on start."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    @task(10)
    def search_web(self):
        """Perform web search - most common operation."""
        if not self.token:
            return
        
        self.client.post(
            "/api/v1/search",
            headers=self.headers,
            json={
                "query": "artificial intelligence",
                "mode": "web",
                "limit": 10
            }
        )
    
    @task(5)
    def search_hybrid(self):
        """Perform hybrid search."""
        if not self.token:
            return
        
        self.client.post(
            "/api/v1/search",
            headers=self.headers,
            json={
                "query": "machine learning",
                "mode": "hybrid",
                "limit": 10
            }
        )
    
    @task(3)
    def search_vector(self):
        """Perform vector search."""
        if not self.token:
            return
        
        self.client.post(
            "/api/v1/search",
            headers=self.headers,
            json={
                "query": "deep learning neural networks",
                "mode": "vector",
                "limit": 10
            }
        )
    
    @task(2)
    def search_ai(self):
        """Perform AI-powered search."""
        if not self.token:
            return
        
        self.client.post(
            "/api/v1/search",
            headers=self.headers,
            json={
                "query": "explain quantum computing",
                "mode": "ai",
                "limit": 5
            }
        )
    
    @task(3)
    def list_documents(self):
        """List user documents."""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/documents/?page=1&page_size=20",
            headers=self.headers
        )
    
    @task(1)
    def get_profile(self):
        """Get user profile."""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/users/profile",
            headers=self.headers
        )
    
    @task(1)
    def get_notifications(self):
        """Get user notifications."""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/notifications/?page=1&page_size=20",
            headers=self.headers
        )


class AdminUserBehavior(SequentialTaskSet):
    """Simulates admin user behavior."""
    
    def on_start(self):
        """Login as admin."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "AdminPass123!"
            }
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    @task(5)
    def list_users(self):
        """List all users (admin only)."""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/admin/users?page=1&page_size=20",
            headers=self.headers
        )
    
    @task(3)
    def get_system_stats(self):
        """Get system statistics."""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/admin/stats",
            headers=self.headers
        )
    
    @task(2)
    def get_queue_stats(self):
        """Get queue statistics."""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/admin/queue",
            headers=self.headers
        )
    
    @task(2)
    def get_cache_stats(self):
        """Get cache statistics."""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/admin/cache",
            headers=self.headers
        )
    
    @task(1)
    def get_audit_logs(self):
        """Get audit logs."""
        if not self.token:
            return
        
        self.client.get(
            "/api/v1/admin/audit-logs?page=1&page_size=20",
            headers=self.headers
        )


class RegularUser(HttpUser):
    """Regular user load test."""
    tasks = [UserBehavior]
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    weight = 10  # 10 regular users


class AdminUser(HttpUser):
    """Admin user load test."""
    tasks = [AdminUserBehavior]
    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks
    weight = 1  # 1 admin user


# Custom metrics for performance tracking
class PerformanceMetrics:
    """Track performance metrics during load test."""
    
    def __init__(self):
        self.search_times = []
        self.document_list_times = []
        self.auth_times = []
    
    def record_search_time(self, time_ms: float):
        """Record search response time."""
        self.search_times.append(time_ms)
    
    def record_document_list_time(self, time_ms: float):
        """Record document list response time."""
        self.document_list_times.append(time_ms)
    
    def record_auth_time(self, time_ms: float):
        """Record authentication response time."""
        self.auth_times.append(time_ms)
    
    def get_percentile(self, times: List[float], percentile: int) -> float:
        """Calculate percentile from list of times."""
        if not times:
            return 0.0
        
        sorted_times = sorted(times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    def print_summary(self):
        """Print performance summary."""
        print("\n" + "="*60)
        print("PERFORMANCE TEST SUMMARY")
        print("="*60)
        
        if self.search_times:
            print(f"\nSearch Endpoints:")
            print(f"  Total requests: {len(self.search_times)}")
            print(f"  Min: {min(self.search_times):.2f}ms")
            print(f"  Max: {max(self.search_times):.2f}ms")
            print(f"  Avg: {sum(self.search_times)/len(self.search_times):.2f}ms")
            print(f"  p95: {self.get_percentile(self.search_times, 95):.2f}ms")
            print(f"  p99: {self.get_percentile(self.search_times, 99):.2f}ms")
        
        if self.document_list_times:
            print(f"\nDocument List Endpoints:")
            print(f"  Total requests: {len(self.document_list_times)}")
            print(f"  Min: {min(self.document_list_times):.2f}ms")
            print(f"  Max: {max(self.document_list_times):.2f}ms")
            print(f"  Avg: {sum(self.document_list_times)/len(self.document_list_times):.2f}ms")
            print(f"  p95: {self.get_percentile(self.document_list_times, 95):.2f}ms")
        
        if self.auth_times:
            print(f"\nAuthentication Endpoints:")
            print(f"  Total requests: {len(self.auth_times)}")
            print(f"  Min: {min(self.auth_times):.2f}ms")
            print(f"  Max: {max(self.auth_times):.2f}ms")
            print(f"  Avg: {sum(self.auth_times)/len(self.auth_times):.2f}ms")
            print(f"  p95: {self.get_percentile(self.auth_times, 95):.2f}ms")
        
        print("\n" + "="*60)


# Global metrics instance
metrics = PerformanceMetrics()


# Event hooks for custom metrics
def on_request_success(request_type, name, response_time, response_length, **kwargs):
    """Track successful request times."""
    if "search" in name.lower():
        metrics.record_search_time(response_time)
    elif "document" in name.lower() and "list" in name.lower():
        metrics.record_document_list_time(response_time)
    elif "auth" in name.lower() or "login" in name.lower():
        metrics.record_auth_time(response_time)


def on_quit():
    """Print summary when test completes."""
    metrics.print_summary()


# Register event hooks
from locust import events

events.request_success.add_listener(on_request_success)
events.quit.add_listener(on_quit)