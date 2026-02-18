import asyncio
import uuid
import sys
import logging
from dotenv import load_dotenv

from graph_orchestrator import GraphOrchestrator
from slack_approver import governor  # Using the humanized 'governor' instance
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Configure logging for the main runner
logging.basicConfig(level=logging.INFO, format='%(asctime)s - NexusOps - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

async def run_session():
    """
    Main execution loop for the NexusOps SRE agent.
    Handles graph orchestration, state-based breakpoints, and HITL resumption.
    """
    orchestrator = GraphOrchestrator()
    nexus_app = orchestrator.build_graph()
    
    # Persistent thread ID for state management across breakpoints
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}
    
    print("\n" + "="*60)
    print(f" NEXUSOPS: AGENTIC SRE RUNTIME | SESSION: {session_id[:8]}")
    print("="*60)
    print("System ready. Type 'exit' to terminate.\n")

    while True:
        try:
            query = input("SRE-Prompt >> ").strip()
            
            if query.lower() in ["exit", "quit"]:
                print("Gracefully shutting down.")
                break
            if not query:
                continue

            state_input = {"messages": [HumanMessage(content=query)]}
            
            # Streaming the graph execution
            async for event in nexus_app.astream(state_input, config=config, stream_mode="values"):
                msg = event["messages"][-1]
                
                if isinstance(msg, ToolMessage):
                    logger.info(f"Execution successful: {msg.name}")
                elif isinstance(msg, AIMessage):
                    if msg.tool_calls:
                        for call in msg.tool_calls:
                            print(f"[*] Agent planning action: {call['name']}...")
                    elif msg.content:
                        print(f"\n[NexusOps]: {msg.content}\n")

            # Check for Governor Breakpoints (Human-in-the-Loop)
            current_state = nexus_app.get_state(config)
            
            if current_state.next and current_state.next[0] == "sensitive_tools":
                # Intercept sensitive actions for manual validation
                pending_call = current_state.values["messages"][-1].tool_calls[0]
                context = f"{pending_call['name']} ({pending_call['args']})"
                
                governor.dispatch_alert(context)
                if governor.await_validation():
                    print("[!] Authorization received. Resuming workflow...")
                    
                    # Passing None to resume from the checkpointed state
                    async for event in nexus_app.astream(None, config=config, stream_mode="values"):
                        msg = event["messages"][-1]
                        
                        if isinstance(msg, ToolMessage):
                            logger.info(f"Resumed execution successful: {msg.name}")
                        elif isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                            print(f"\n[NexusOps Final]: {msg.content}\n")
                else:
                    logger.warning("Action aborted by operator. Returning to standby.")

        except EOFError:
            break
        except Exception as e:
            logger.error(f"Runtime Exception: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(run_session())
    except KeyboardInterrupt:
        sys.exit(0)
