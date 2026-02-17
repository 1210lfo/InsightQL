"""
Agent State Definition for LangGraph
Defines the TypedDict state that flows through all nodes.
"""

from typing import Any, List, Literal, TypedDict


class UserContext(TypedDict):
    """Context about the current user making the request."""
    user_id: str
    org_id: str
    timezone: str
    lang: str


class QueryPlan(TypedDict, total=False):
    """Plan for executing an analytics query."""
    metric: str
    filters: dict[str, Any]
    groupby: str | None
    timeframe: dict[str, str]  # {"start": "2025-01-01", "end": "2025-01-31"}
    rpc_function: str
    parameters: dict[str, Any]
    expects_data: bool
    steps: List[dict[str, Any]]  # For multi-step queries


class RPCCall(TypedDict):
    """Record of an RPC function call."""
    function: str
    params: dict[str, Any]
    result: Any
    execution_time_ms: int
    query_id: str


class Evidence(TypedDict):
    """Evidence supporting the response."""
    sql_template: str
    params_used: dict[str, Any]
    row_count: int
    query_ids: List[str]


class AnalyticsAgentState(TypedDict, total=False):
    """
    Complete state for the Analytics Agent.
    This state flows through all LangGraph nodes.
    """
    # === Input original ===
    user_query: str
    user_context: UserContext
    
    # === Parsing ===
    intent: Literal[
        "kpi_query",
        "comparison",
        "trend",
        "drill_down",
        "clarification_needed",
        "unsupported"
    ]
    entities: List[str]  # ["revenue", "customers", "Q4_2025"]
    missing_params: List[str]  # ["date_range", "segment"]
    
    # === Planning ===
    query_plan: QueryPlan | None
    validation_errors_plan: List[str]  # Errors from plan validation
    
    # === Execution ===
    rpc_calls: List[RPCCall]
    raw_results: List[dict[str, Any]]
    
    # === Validation ===
    validation_passed: bool
    validation_errors: List[str]
    
    # === Output ===
    final_answer: str
    evidence: Evidence | None
    recommendations: List[str]
    
    # === Control flow ===
    retry_count: int
    max_retries: int  # default: 2
    conversation_history: List[dict[str, str]]  # [{"role": "user", "content": "..."}]
    current_node: str  # For debugging/tracing
    error_message: str | None  # Last error encountered


def create_initial_state(
    user_query: str,
    user_context: UserContext | None = None,
    conversation_history: List[dict[str, str]] | None = None,
    max_retries: int = 2,
) -> AnalyticsAgentState:
    """
    Create an initial state for a new agent run.
    
    Args:
        user_query: The user's natural language question
        user_context: Context about the user (optional)
        conversation_history: Previous conversation turns (optional)
        max_retries: Maximum retry attempts for failed executions
        
    Returns:
        Initial AnalyticsAgentState ready for the agent graph
    """
    default_context: UserContext = {
        "user_id": "anonymous",
        "org_id": "default",
        "timezone": "UTC",
        "lang": "es",
    }
    
    return AnalyticsAgentState(
        # Input
        user_query=user_query,
        user_context=user_context or default_context,
        
        # Parsing (will be filled by Parse node)
        intent="kpi_query",
        entities=[],
        missing_params=[],
        
        # Planning (will be filled by Plan node)
        query_plan=None,
        validation_errors_plan=[],
        
        # Execution (will be filled by Execute node)
        rpc_calls=[],
        raw_results=[],
        
        # Validation (will be filled by Validate node)
        validation_passed=False,
        validation_errors=[],
        
        # Output (will be filled by Synthesize node)
        final_answer="",
        evidence=None,
        recommendations=[],
        
        # Control flow
        retry_count=0,
        max_retries=max_retries,
        conversation_history=conversation_history or [],
        current_node="start",
        error_message=None,
    )
