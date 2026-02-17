"""
LangGraph Definition
Creates the analytics agent graph with 6 nodes and conditional routing.
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from src.agent.state import AnalyticsAgentState
from src.agent.nodes import (
    parse_node,
    clarify_node,
    plan_node,
    execute_node,
    validate_node,
    synthesize_node,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Routing Functions
# =============================================================================

def route_after_parse(state: AnalyticsAgentState) -> Literal["clarify", "plan", "synthesize"]:
    """
    Route after Parse node:
    - If greeting -> synthesize (friendly response)
    - If missing_params -> clarify
    - If unsupported intent -> synthesize (with limitation message)
    - Otherwise -> plan
    """
    intent = state.get("intent", "")
    missing_params = state.get("missing_params", [])
    
    # Greetings and unsupported go directly to synthesis
    if intent in ("greeting", "unsupported"):
        return "synthesize"
    
    if missing_params:
        return "clarify"
    
    return "plan"


def route_after_plan(state: AnalyticsAgentState) -> Literal["execute", "synthesize"]:
    """
    Route after Plan node:
    - If plan is None (validation failed) -> synthesize
    - Otherwise -> execute
    """
    if state.get("query_plan") is None:
        return "synthesize"
    return "execute"


def route_after_execute(state: AnalyticsAgentState) -> Literal["execute", "validate", "synthesize"]:
    """
    Route after Execute node:
    - If retry needed and under limit -> execute (retry)
    - If max retries reached with no results -> synthesize (error)
    - Otherwise -> validate
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    raw_results = state.get("raw_results", [])
    error_message = state.get("error_message")
    
    # If we have an error and haven't exceeded retries
    if error_message and retry_count < max_retries and not raw_results:
        logger.info(f"Retrying execution, attempt {retry_count + 1}/{max_retries}")
        return "execute"
    
    # If max retries reached with no results
    if retry_count >= max_retries and not raw_results:
        return "synthesize"
    
    return "validate"


# =============================================================================
# Graph Builder
# =============================================================================

def create_analytics_agent() -> StateGraph:
    """
    Create the LangGraph for the analytics agent.
    
    Graph structure:
    ```
    START → Parse → [Clarify → END] | [Plan → Execute → Validate → Synthesize → END]
                           ↑_______________retry_loop________________|
    ```
    
    Returns:
        Compiled LangGraph ready for invocation
    """
    # Create the graph with our state type
    graph = StateGraph(AnalyticsAgentState)
    
    # Add all nodes
    graph.add_node("parse", parse_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("validate", validate_node)
    graph.add_node("synthesize", synthesize_node)
    
    # Set entry point
    graph.set_entry_point("parse")
    
    # Add conditional edges
    graph.add_conditional_edges(
        "parse",
        route_after_parse,
        {
            "clarify": "clarify",
            "plan": "plan",
            "synthesize": "synthesize",
        }
    )
    
    graph.add_conditional_edges(
        "plan",
        route_after_plan,
        {
            "execute": "execute",
            "synthesize": "synthesize",
        }
    )
    
    graph.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "execute": "execute",  # Retry loop
            "validate": "validate",
            "synthesize": "synthesize",
        }
    )
    
    # Direct edges
    graph.add_edge("clarify", END)
    graph.add_edge("validate", "synthesize")
    graph.add_edge("synthesize", END)
    
    # Compile the graph
    compiled = graph.compile()
    
    logger.info("Analytics agent graph created successfully")
    return compiled


# =============================================================================
# Convenience Functions
# =============================================================================

async def run_analytics_query(
    query: str,
    user_id: str = "anonymous",
    org_id: str = "default",
    timezone: str = "UTC",
    lang: str = "es",
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Run an analytics query through the agent.
    
    Args:
        query: Natural language query
        user_id: User identifier
        org_id: Organization identifier
        timezone: User's timezone
        lang: Language preference
        conversation_history: Previous conversation turns
        
    Returns:
        Dict with final_answer, evidence, recommendations, and full state
    """
    from src.agent.state import create_initial_state
    
    # Create initial state
    initial_state = create_initial_state(
        user_query=query,
        user_context={
            "user_id": user_id,
            "org_id": org_id,
            "timezone": timezone,
            "lang": lang,
        },
        conversation_history=conversation_history or [],
    )
    
    # Create and run the graph
    graph = create_analytics_agent()
    final_state = await graph.ainvoke(initial_state)
    
    return {
        "answer": final_state.get("final_answer", ""),
        "evidence": final_state.get("evidence"),
        "recommendations": final_state.get("recommendations", []),
        "intent": final_state.get("intent"),
        "validation_passed": final_state.get("validation_passed"),
        "state": final_state,
    }


async def run_voice_query(
    audio_data: bytes,
    audio_format: str = "wav",
    user_id: str = "anonymous",
    org_id: str = "default",
    timezone: str = "UTC",
    lang: str = "es",
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Run an analytics query from voice audio input.
    
    Pipeline: Audio → Groq Whisper STT → Text → LangGraph Agent
    
    Args:
        audio_data: Raw audio bytes
        audio_format: Audio format (wav, mp3, m4a, webm, ogg)
        user_id: User identifier
        org_id: Organization identifier
        timezone: User's timezone
        lang: Language preference
        conversation_history: Previous conversation turns
        
    Returns:
        Dict with transcription, answer, evidence, recommendations
    """
    from src.voice.transcriber import VoiceTranscriber

    # Step 1: Transcribe audio to text
    transcriber = VoiceTranscriber()
    
    if not transcriber.is_enabled():
        return {
            "answer": "🎙️ La función de voz no está habilitada. Configura VOICE_ENABLED=true y GROQ_API_KEY en tu .env",
            "transcription": None,
            "voice_error": "Voice not enabled",
        }

    transcription = await transcriber.transcribe(audio_data, audio_format, lang)
    
    if not transcription.success:
        return {
            "answer": f"🎙️ No pude procesar el audio: {transcription.error}",
            "transcription": None,
            "voice_error": transcription.error,
        }

    logger.info(
        f"Voice transcription: '{transcription.text}' "
        f"({transcription.duration_seconds:.1f}s, {transcription.provider})"
    )

    # Step 2: Run the text query through the existing agent
    result = await run_analytics_query(
        query=transcription.text,
        user_id=user_id,
        org_id=org_id,
        timezone=timezone,
        lang=lang,
        conversation_history=conversation_history,
    )

    # Step 3: Enrich result with voice metadata
    result["transcription"] = {
        "text": transcription.text,
        "language": transcription.language,
        "duration_seconds": transcription.duration_seconds,
        "provider": transcription.provider,
        "processing_time_ms": transcription.processing_time_ms,
    }
    result["input_type"] = "voice"

    # Update state with voice info
    if "state" in result:
        result["state"]["input_type"] = "voice"
        result["state"]["audio_transcript"] = transcription.text
        result["state"]["audio_duration_seconds"] = transcription.duration_seconds
        result["state"]["voice_provider"] = transcription.provider

    return result
