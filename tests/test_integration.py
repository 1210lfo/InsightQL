"""
Integration tests for the full agent flow
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.agent.state import create_initial_state
from src.agent.graph import create_analytics_agent, run_analytics_query


class TestFullAgentFlow:
    """End-to-end tests for the agent"""
    
    @pytest.mark.asyncio
    async def test_simple_kpi_query_flow(self):
        """Test a simple KPI query goes through all nodes"""
        
        # Mock all external dependencies
        with patch('src.agent.nodes.get_llm') as mock_llm_factory:
            mock_llm = MagicMock()
            
            # Configure mock responses for each node
            mock_llm.ainvoke = AsyncMock(side_effect=[
                # Parse response
                MagicMock(content='{"intent": "kpi_query", "entities": ["revenue", "Q4_2025"], "missing_params": []}'),
                # Plan response
                MagicMock(content='''{
                    "rpc_function": "get_revenue_by_segment",
                    "parameters": {"start_date": "2025-10-01", "end_date": "2025-12-31"},
                    "metric": "revenue",
                    "expects_data": true
                }'''),
                # Synthesize response
                MagicMock(content="El revenue de Q4 2025 fue de **$1,725,000**. Enterprise contribuyó $1.25M y SMB $475K."),
            ])
            mock_llm_factory.return_value = mock_llm
            
            with patch('src.agent.nodes.validate_query_plan') as mock_validate:
                mock_validate.return_value = {"valid": True, "errors": [], "estimated_cost": "low"}
                
                with patch('src.agent.nodes.execute_analytics_query') as mock_execute:
                    mock_execute.return_value = {
                        "success": True,
                        "data": [
                            {"segment": "enterprise", "revenue": 1250000},
                            {"segment": "smb", "revenue": 475000},
                        ],
                        "row_count": 2,
                        "execution_time_ms": 150,
                        "query_id": "qry_test123",
                    }
                    
                    result = await run_analytics_query(
                        query="¿Cuál fue el revenue de Q4 2025?",
                        user_id="test_user",
                        org_id="test_org",
                    )
                    
                    assert result["answer"] is not None
                    assert "revenue" in result["answer"].lower() or "1,725,000" in result["answer"]
                    assert result["validation_passed"] is True
    
    @pytest.mark.asyncio
    async def test_clarification_flow(self):
        """Test that missing params trigger clarification"""
        
        with patch('src.agent.nodes.get_llm') as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(side_effect=[
                # Parse response - missing timeframe
                MagicMock(content='{"intent": "kpi_query", "entities": ["new_customers"], "missing_params": ["timeframe"]}'),
                # Clarify response
                MagicMock(content="¿En qué periodo te gustaría ver los clientes nuevos? Por ejemplo: último mes, Q4 2025, o este año."),
            ])
            mock_llm_factory.return_value = mock_llm
            
            result = await run_analytics_query(
                query="¿Cuántos clientes nuevos tuvimos?",
            )
            
            # Should ask for clarification, not execute
            assert "periodo" in result["answer"].lower() or "mes" in result["answer"].lower()
    
    @pytest.mark.asyncio
    async def test_validation_failure_flow(self):
        """Test that validation failures are reported gracefully"""
        
        with patch('src.agent.nodes.get_llm') as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(side_effect=[
                # Parse response
                MagicMock(content='{"intent": "kpi_query", "entities": ["revenue", "Q4_2025"], "missing_params": []}'),
                # Plan response
                MagicMock(content='''{
                    "rpc_function": "get_revenue_by_segment",
                    "parameters": {"start_date": "2025-10-01", "end_date": "2025-12-31"},
                    "metric": "revenue",
                    "expects_data": true
                }'''),
                # Synthesize response (after validation)
                MagicMock(content="No se encontraron datos para el periodo especificado. Esto puede deberse a que no hubo transacciones en Q4 2025."),
            ])
            mock_llm_factory.return_value = mock_llm
            
            with patch('src.agent.nodes.validate_query_plan') as mock_validate:
                mock_validate.return_value = {"valid": True, "errors": [], "estimated_cost": "low"}
                
                with patch('src.agent.nodes.execute_analytics_query') as mock_execute:
                    # Return empty results
                    mock_execute.return_value = {
                        "success": True,
                        "data": [],
                        "row_count": 0,
                        "execution_time_ms": 50,
                        "query_id": "qry_empty",
                    }
                    
                    result = await run_analytics_query(
                        query="¿Cuál fue el revenue de Q4 2025?",
                    )
                    
                    # Should report validation issue
                    assert result["validation_passed"] is False


class TestGraphRouting:
    """Tests for graph routing logic"""
    
    def test_route_after_parse_to_clarify(self):
        """Test routing to clarify when params are missing"""
        from src.agent.graph import route_after_parse
        
        state = create_initial_state("test")
        state["missing_params"] = ["timeframe"]
        
        result = route_after_parse(state)
        assert result == "clarify"
    
    def test_route_after_parse_to_plan(self):
        """Test routing to plan when all params present"""
        from src.agent.graph import route_after_parse
        
        state = create_initial_state("test")
        state["missing_params"] = []
        state["intent"] = "kpi_query"
        
        result = route_after_parse(state)
        assert result == "plan"
    
    def test_route_after_parse_unsupported(self):
        """Test routing unsupported queries to synthesize"""
        from src.agent.graph import route_after_parse
        
        state = create_initial_state("test")
        state["intent"] = "unsupported"
        
        result = route_after_parse(state)
        assert result == "synthesize"
    
    def test_route_after_plan_success(self):
        """Test routing after successful plan"""
        from src.agent.graph import route_after_plan
        
        state = create_initial_state("test")
        state["query_plan"] = {"rpc_function": "test"}
        
        result = route_after_plan(state)
        assert result == "execute"
    
    def test_route_after_plan_failure(self):
        """Test routing after failed plan"""
        from src.agent.graph import route_after_plan
        
        state = create_initial_state("test")
        state["query_plan"] = None
        
        result = route_after_plan(state)
        assert result == "synthesize"
    
    def test_route_after_execute_to_validate(self):
        """Test routing to validate after successful execute"""
        from src.agent.graph import route_after_execute
        
        state = create_initial_state("test")
        state["raw_results"] = [{"data": "test"}]
        state["retry_count"] = 0
        
        result = route_after_execute(state)
        assert result == "validate"
    
    def test_route_after_execute_retry(self):
        """Test retry routing after failed execute"""
        from src.agent.graph import route_after_execute
        
        state = create_initial_state("test")
        state["raw_results"] = []
        state["error_message"] = "Timeout"
        state["retry_count"] = 0
        state["max_retries"] = 2
        
        result = route_after_execute(state)
        assert result == "execute"  # Should retry
    
    def test_route_after_execute_max_retries(self):
        """Test routing to synthesize after max retries"""
        from src.agent.graph import route_after_execute
        
        state = create_initial_state("test")
        state["raw_results"] = []
        state["error_message"] = "Timeout"
        state["retry_count"] = 2
        state["max_retries"] = 2
        
        result = route_after_execute(state)
        assert result == "synthesize"
