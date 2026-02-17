"""
InsightQL - Main Entry Point
Provides CLI and programmatic interface for the analytics agent.
"""

import asyncio
import logging
import sys
from typing import Optional

from src.agent import create_analytics_agent, create_initial_state
from src.config import get_config
from src.observability import setup_tracing, TracingContext
from src.mcp.client import cleanup_mcp_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def run_query(
    query: str,
    user_id: str = "anonymous",
    org_id: str = "default",
    timezone: str = "America/Bogota",
    verbose: bool = False,
) -> dict:
    """
    Run an analytics query through the agent.
    
    Args:
        query: Natural language question
        user_id: User identifier
        org_id: Organization identifier
        timezone: User's timezone
        verbose: Enable verbose output
        
    Returns:
        Agent response with answer, evidence, and recommendations
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Setup tracing
    setup_tracing()
    
    # Create initial state
    initial_state = create_initial_state(
        user_query=query,
        user_context={
            "user_id": user_id,
            "org_id": org_id,
            "timezone": timezone,
            "lang": "es",
        },
    )
    
    # Create and run the graph
    with TracingContext(query, user_id) as ctx:
        graph = create_analytics_agent()
        final_state = await graph.ainvoke(initial_state)
        
        ctx.add_attribute("intent", final_state.get("intent", "unknown"))
        ctx.add_attribute("validation_passed", final_state.get("validation_passed", False))
    
    return {
        "answer": final_state.get("final_answer", ""),
        "evidence": final_state.get("evidence"),
        "recommendations": final_state.get("recommendations", []),
        "intent": final_state.get("intent"),
        "entities": final_state.get("entities", []),
        "validation_passed": final_state.get("validation_passed"),
    }


async def interactive_mode():
    """
    Run the agent in interactive mode (REPL).
    """
    print("\n" + "=" * 60)
    print("  InsightQL - Agente Analítico")
    print("  Escribe tus preguntas en lenguaje natural")
    print("  Escribe 'salir' o 'exit' para terminar")
    print("=" * 60 + "\n")
    
    conversation_history = []
    
    try:
        while True:
            try:
                query = input("\n🔍 Tu pregunta: ").strip()
            except EOFError:
                break
            
            if not query:
                continue
            
            if query.lower() in ["salir", "exit", "quit", "q"]:
                print("\n¡Hasta luego! 👋")
                break
            
            print("\n⏳ Procesando...")
            
            try:
                result = await run_query(query)
                
                print("\n" + "-" * 50)
                print("💡 Respuesta:")
                print(result["answer"])
                
                if result.get("recommendations"):
                    print("\n📊 Recomendaciones:")
                    for rec in result["recommendations"]:
                        print(f"  • {rec}")
                
                if result.get("evidence"):
                    evidence = result["evidence"]
                    print(f"\n📎 Evidencia: {evidence.get('row_count', 0)} filas consultadas")
                
                print("-" * 50)
                
                # Add to history
                conversation_history.append({
                    "role": "user",
                    "content": query,
                })
                conversation_history.append({
                    "role": "assistant",
                    "content": result["answer"],
                })
                
            except Exception as e:
                logger.error(f"Error processing query: {e}")
                print(f"\n❌ Error: {e}")
                
    finally:
        await cleanup_mcp_client()


async def main():
    """
    Main entry point.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="InsightQL - Agente Analítico sobre Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python -m src.main --interactive
  python -m src.main --query "¿Cuál fue el revenue de Q4 2025?"
  python -m src.main --query "Compara enterprise vs SMB" --verbose
        """,
    )
    
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Modo interactivo (REPL)",
    )
    
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="Pregunta a ejecutar",
    )
    
    parser.add_argument(
        "--user-id",
        type=str,
        default="anonymous",
        help="ID del usuario",
    )
    
    parser.add_argument(
        "--org-id",
        type=str,
        default="default",
        help="ID de la organización",
    )
    
    parser.add_argument(
        "--timezone",
        type=str,
        default="America/Bogota",
        help="Zona horaria del usuario",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Modo verbose (debug logging)",
    )
    
    args = parser.parse_args()
    
    # Validate configuration
    config = get_config()
    if not config.github_models.token:
        print("❌ Error: GITHUB_TOKEN no configurado. Copia .env.example a .env y configura.")
        sys.exit(1)
    
    if args.interactive:
        await interactive_mode()
    elif args.query:
        result = await run_query(
            query=args.query,
            user_id=args.user_id,
            org_id=args.org_id,
            timezone=args.timezone,
            verbose=args.verbose,
        )
        
        print("\n💡 Respuesta:")
        print(result["answer"])
        
        if result.get("recommendations"):
            print("\n📊 Recomendaciones:")
            for rec in result["recommendations"]:
                print(f"  • {rec}")
        
        await cleanup_mcp_client()
    else:
        parser.print_help()
        print("\n💡 Tip: Usa --interactive para modo interactivo o --query para una pregunta.")


if __name__ == "__main__":
    asyncio.run(main())
