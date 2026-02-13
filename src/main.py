import asyncio
import os
from dotenv import load_dotenv

# Import the Orchestrator and Knowledge Base
from graph_orchestrator import GraphOrchestrator, search_knowledge_base
from slack_approver import slack_approver

# LangChain core components
# Added ToolMessage here to fix the Execution Error
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage 
from langchain_core.tools import tool

# MCP Server call wrappers
from mcp_tools.k8s_server import call_tool as k8s_call
from mcp_tools.github_server import call_tool as gh_call

load_dotenv()

# --- Production Tools with Human-in-the-Loop (HITL) ---

@tool
async def get_pod_logs(pod_name: str, namespace: str = "default"):
    """Fetches real-time logs from a Kubernetes pod via MCP to diagnose crashes."""
    res = await k8s_call("get_pod_logs", {"pod_name": pod_name, "namespace": namespace})
    # MCP returns a list of content blocks; we extract the text
    return res[0].text if hasattr(res[0], 'text') else str(res)

@tool
async def create_pull_request(repo_name: str, title: str, body: str, head: str):
    """Drafts a Pull Request on GitHub. Requires manual approval via Slack."""
    print(f"\n[INTERCEPT] High-Risk Action Detected: Create PR on {repo_name}")
    
    # Request Approval via Slack Webhook
    approved = slack_approver.request_approval(
        f"PROPOSAL: Create PR '{title}' on {repo_name}\nSummary: {body[:100]}..."
    )
    
    if approved:
        try:
            res = await gh_call("create_pull_request", {
                "repo_name": repo_name,
                "title": title,
                "body": body,
                "head": head
            })
            return res[0].text if hasattr(res[0], 'text') else "PR Created Successfully."
        except Exception as e:
            return f"Failed to create PR: {str(e)}"
    else:
        return "Action Denied by User via Slack Gatekeeper."

# --- Execution Logic ---

async def main():
    # 1. Define the toolset for the agent
    # We pass these into the orchestrator so the graph nodes can bind them
    tools = [search_knowledge_base, get_pod_logs, create_pull_request]
    
    # 2. Initialize orchestrator with specific tools
    orchestrator = GraphOrchestrator(tools=tools)
    app = orchestrator.build_graph()
    
    print("\n=== NexusOps: Autonomous Agentic RAG System (Production) ===")
    print("--- Agent Ready. Monitoring Cluster Status ---")

    while True:
        user_input = input("\nUser: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break

        print("\n[Processing] Sending query to LangGraph orchestrator...")
        
        # Initialize the state with the user's message
        inputs = {"messages": [HumanMessage(content=user_input)]}
        
        try:
            # Stream the graph execution to observe node transitions (agent -> tools -> agent)
            async for output in app.astream(inputs):
                for key, value in output.items():
                    if "messages" in value:
                        last_msg = value["messages"][-1]
                        
                        # Handle varied message formats (tuples vs objects)
                        if isinstance(last_msg, tuple):
                            content = last_msg[0].content
                        elif hasattr(last_msg, 'content'):
                            content = last_msg.content
                        else:
                            content = str(last_msg)

                        # Logic to display output based on node type
                        if isinstance(last_msg, ToolMessage):
                            print(f"[{key}] 🛠️ Tool Result: {content[:200]}...")
                        elif isinstance(last_msg, AIMessage):
                            if last_msg.tool_calls:
                                print(f"[{key}] 🤔 Thinking: Calling {last_msg.tool_calls[0]['name']}...")
                            else:
                                print(f"[{key}] 🤖 Agent: {content}")

            print("\n--- Cycle Complete ---")
            
        except Exception as e:
            # This will now catch structural errors without crashing the loop
            print(f"Execution Error: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nNexusOps shutting down gracefully.")
