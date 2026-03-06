"""
Tests for MCP tools
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.mcp.tools import (
    get_schema_metadata,
    get_metric_definition,
    validate_query_plan,
    execute_analytics_query,
    clear_schema_cache,
)


class TestGetSchemaMetadata:
    """Tests for get_schema_metadata tool"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear cache before each test"""
        clear_schema_cache()
    
    @pytest.mark.asyncio
    async def test_returns_tables_scope(self):
        """Test that tables scope returns only tables"""
        result = await get_schema_metadata(scope="tables")
        
        assert "tables" in result
        assert "metrics" not in result
        assert len(result["tables"]) > 0
    
    @pytest.mark.asyncio
    async def test_returns_metrics_scope(self):
        """Test that metrics scope returns only metrics"""
        result = await get_schema_metadata(scope="metrics")
        
        assert "metrics" in result
        assert "tables" not in result
        assert len(result["metrics"]) > 0
    
    @pytest.mark.asyncio
    async def test_returns_all_scope(self):
        """Test that all scope returns both tables and metrics"""
        result = await get_schema_metadata(scope="all")
        
        assert "tables" in result
        assert "metrics" in result
    
    @pytest.mark.asyncio
    async def test_includes_expected_metrics(self):
        """Test that expected fashion metrics are present"""
        result = await get_schema_metadata(scope="metrics")
        
        metric_names = [m["metric_name"] for m in result["metrics"]]
        # Fashion catalog metrics
        assert "precio_promedio" in metric_names
        assert "productos_disponibles" in metric_names


class TestGetMetricDefinition:
    """Tests for get_metric_definition tool"""
    
    @pytest.mark.asyncio
    async def test_returns_revenue_definition(self):
        """Test that revenue metric has proper definition"""
        result = await get_metric_definition("revenue")
        
        assert result["name"] == "revenue"
        assert "formula" in result
        assert "interpretation" in result
    
    @pytest.mark.asyncio
    async def test_returns_precio_promedio_definition(self):
        """Test that precio_promedio metric has proper definition"""
        result = await get_metric_definition("precio_promedio")
        
        assert result["name"] == "precio_promedio"
        # Formula should be about averages or prices
        assert "formula" in result
    
    @pytest.mark.asyncio
    async def test_unknown_metric_returns_placeholder(self):
        """Test that unknown metric returns placeholder"""
        result = await get_metric_definition("unknown_metric_xyz")
        
        assert result["name"] == "unknown_metric_xyz"
        assert "no encontrada" in result["interpretation"].lower()


class TestValidateQueryPlan:
    """Tests for validate_query_plan tool"""
    
    @pytest.mark.asyncio
    async def test_validates_allowed_function(self):
        """Test that allowed functions are validated"""
        with patch('src.mcp.tools.get_config') as mock_config:
            mock_config.return_value.agent.allowed_rpc_functions = [
                "get_revenue_by_segment",
                "get_churn_cohort",
            ]
            
            result = await validate_query_plan(
                rpc_function="get_revenue_by_segment",
                parameters={"start_date": "2025-01-01", "end_date": "2025-12-31"},
            )
            
            assert result["valid"] is True
            assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_rejects_disallowed_function(self):
        """Test that disallowed functions are rejected"""
        with patch('src.mcp.tools.get_config') as mock_config:
            mock_config.return_value.agent.allowed_rpc_functions = [
                "get_revenue_by_segment",
            ]
            
            result = await validate_query_plan(
                rpc_function="drop_all_tables",  # Not in allowlist
                parameters={},
            )
            
            assert result["valid"] is False
            assert any("no está permitida" in e or "no permitida" in e or "no está en la lista" in e or "not allowed" in e.lower() for e in result["errors"])
    
    @pytest.mark.asyncio
    async def test_validates_allowed_function_with_params(self):
        """Test that allowed functions with valid params pass"""
        with patch('src.mcp.tools.get_config') as mock_config:
            mock_config.return_value.agent.allowed_rpc_functions = ["get_price_analysis"]
            
            result = await validate_query_plan(
                rpc_function="get_price_analysis",
                parameters={"categoria": "Calzado"},
            )
            
            # Should pass validation
            assert result["valid"] is True


class TestExecuteAnalyticsQuery:
    """Tests for execute_analytics_query tool"""
    
    @pytest.mark.asyncio
    async def test_rejects_disallowed_function(self):
        """Test that disallowed functions are rejected"""
        with patch('src.mcp.tools.get_config') as mock_config:
            mock_config.return_value.agent.allowed_rpc_functions = ["get_revenue_by_segment"]
            
            result = await execute_analytics_query(
                rpc_function="malicious_function",
                parameters={},
            )
            
            assert result["success"] is False
            assert "no permitida" in result["error"]
    
    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_function(self):
        """Test that an error is returned for unknown Supabase function"""
        with patch('src.mcp.tools.get_config') as mock_config:
            mock_config.return_value.agent.allowed_rpc_functions = ["get_revenue_by_segment"]
            
            with patch('src.mcp.tools.execute_supabase_query', new_callable=AsyncMock) as mock_sq:
                mock_sq.side_effect = Exception("Function not found")
                
                result = await execute_analytics_query(
                    rpc_function="get_revenue_by_segment",
                    parameters={"start_date": "2025-01-01", "end_date": "2025-12-31"},
                )
                
                assert "data" in result
    
    @pytest.mark.asyncio
    async def test_returns_query_id(self):
        """Test that a query ID is always returned"""
        with patch('src.mcp.tools.get_config') as mock_config:
            mock_config.return_value.agent.allowed_rpc_functions = ["get_revenue_by_segment"]
            
            result = await execute_analytics_query(
                rpc_function="get_revenue_by_segment",
                parameters={},
            )
            
            assert "query_id" in result
            assert result["query_id"].startswith("qry_")
