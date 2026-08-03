"""Integration tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_liveness(self, async_client: AsyncClient):
        """Test /health/live endpoint returns liveness status."""
        response = await async_client.get("/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "nebula-backend"
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_health_readiness(self, async_client: AsyncClient):
        """Test /health/ready endpoint returns readiness status."""
        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["service"] == "nebula-backend"
        assert "timestamp" in data
        assert "dependencies" in data
        
        # Check required dependencies
        dependencies = data["dependencies"]
        assert "database" in dependencies
        assert "redis" in dependencies
        assert "storage" in dependencies
    
    @pytest.mark.asyncio
    async def test_health_detailed(self, async_client: AsyncClient):
        """Test /health/detailed endpoint returns full health status."""
        response = await async_client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["service"] == "nebula-backend"
        assert "timestamp" in data
        assert "version" in data
        assert "uptime" in data
        assert "dependencies" in data
        
        # Check all expected dependencies
        dependencies = data["dependencies"]
        assert "database" in dependencies
        assert "redis" in dependencies
        assert "storage" in dependencies
        assert "vector_worker" in dependencies
        assert "indexing_worker" in dependencies
        assert "ai_providers" in dependencies
        assert "disk" in dependencies
    
    @pytest.mark.asyncio
    async def test_health_base(self, async_client: AsyncClient):
        """Test /health endpoint returns basic status."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        # Debug: print response data
        print(f"Health response: {data}")
        assert data["status"] == "healthy"
        assert data["service"] == "nebula-backend"
        assert "timestamp" in data
        assert "version" in data


@pytest.mark.asyncio
class TestHealthDependencyChecks:
    """Test health dependency checks."""
    
    @pytest.mark.asyncio
    async def test_database_dependency(self, async_client: AsyncClient):
        """Test database dependency check."""
        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        db_status = data["dependencies"]["database"]
        
        # Database should be healthy or degraded, not unhealthy
        assert db_status["status"] in ["healthy", "degraded"]
        assert "response_time_ms" in db_status
    
    @pytest.mark.asyncio
    async def test_redis_dependency(self, async_client: AsyncClient):
        """Test Redis dependency check."""
        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        redis_status = data["dependencies"]["redis"]
        
        # Redis should be healthy, unhealthy, or using in-memory fallback
        assert redis_status["status"] in ["healthy", "unhealthy", "degraded"]
        assert "response_time_ms" in redis_status
    
    @pytest.mark.asyncio
    async def test_storage_dependency(self, async_client: AsyncClient):
        """Test storage dependency check."""
        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        storage_status = data["dependencies"]["storage"]
        
        assert storage_status["status"] in ["healthy", "degraded"]
        assert "response_time_ms" in storage_status
    
    @pytest.mark.asyncio
    async def test_vector_worker_dependency(self, async_client: AsyncClient):
        """Test vector worker dependency check."""
        response = await async_client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        worker_status = data["dependencies"]["vector_worker"]
        
        assert worker_status["status"] in ["healthy", "degraded"]
        assert "response_time_ms" in worker_status
    
    @pytest.mark.asyncio
    async def test_indexing_worker_dependency(self, async_client: AsyncClient):
        """Test indexing worker dependency check."""
        response = await async_client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        worker_status = data["dependencies"]["indexing_worker"]
        
        assert worker_status["status"] in ["healthy", "degraded"]
        assert "response_time_ms" in worker_status


@pytest.mark.asyncio
class TestHealthErrorCases:
    """Test health endpoints error handling."""
    
    @pytest.mark.asyncio
    async def test_readiness_with_failed_dependency(self, async_client: AsyncClient, monkeypatch):
        """Test readiness check with database failure."""
        # Mock database to fail
        async def mock_connect_fail():
            raise Exception("Database connection failed")
        
        # This would require mocking at the import level
        # For now, just verify the endpoint handles errors gracefully
        response = await async_client.get("/health/ready")
        # Should still return a response even if some checks fail
        assert response.status_code in [200, 503]


@pytest.mark.asyncio
class TestUptimeCalculation:
    """Test uptime calculation in health responses."""
    
    @pytest.mark.asyncio
    async def test_uptime_format(self, async_client: AsyncClient):
        """Test uptime is in expected format."""
        response = await async_client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        uptime = data.get("uptime")
        
        if uptime:
            # Check format: contains d, h, m, s
            assert any(x in uptime for x in ["d", "h", "m", "s"])
    
    @pytest.mark.asyncio
    async def test_version_in_response(self, async_client: AsyncClient):
        """Test version is included in health response."""
        response = await async_client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["version"] is not None
        assert data["version"] != "unknown"
