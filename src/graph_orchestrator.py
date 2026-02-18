import os
import asyncio
import operator
import logging
from typing import Annotated, List, TypedDict, Union, Literal

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from dotenv import load_dotenv
from github import Github, Auth
from vector_store_wrapper import NexusVectorClient # Updated reference

load_dotenv()

# Audit-level logging for SRE tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - NexusGraph - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """
    Maintains the conversational state and tool history.
    """
    messages: Annotated[List[BaseMessage], operator.add]

# --- SRE Toolset Implementation ---

@tool
async def search_playbooks(query: str):
    """
    Queries the RAG knowledge base for incident remediation playbooks.
    Essential for root-cause analysis and identifying established fix patterns.
    """
    try:
        # Initializing client with a local scope to ensure fresh connection per call
        store = NexusVectorClient()
        await store.connect()
        
        results = await store.retrieve_context(query, limit=2)
        if not results:
            return "No matching playbooks identified for this incident signature."
            
        return "\n".join([f"- [Confidence: {r['score']:.2f}] {r['data'].get('text')}" for r in results])
    except Exception as e:
        logger.error(f"Knowledge Base Retrieval Failure: {e}")
        return "Internal Error: Unable to access remediation playbooks."

@tool
def fetch_k8s_logs(pod_name: str, namespace: str = "default"):
    """
    Direct log retrieval from Kubernetes runtime. Used to diagnose OOM or CrashLoopBackOff.
    """
    # Simulated cluster logs for the NexusOps demo environment
    mock_registry = {
        "backend-api": "CRITICAL: java.lang.OutOfMemoryError: Java heap space",
        "payment-gw": "ERROR: upstream connection timeout - database-replica-01",
    }
    content = mock_registry.get(pod_name, "Logstream clear: No active exceptions found in pod.")
    return f"Runtime Logs [{pod_name} | {namespace}]:\n{content}"

@tool
def create_github_remediation_pr(repo_name: str, title: str, body: str):
    """
    Automates the final stage of remediation by proposing a code-level fix via PR.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN not configured in environment.")
        return "System Restriction: GitHub automation disabled (Token missing)."

    try:
        gh = Github(auth=Auth.Token(token))
        repo = gh.get_user().get_repo(repo_name)
        
        # Note: We simulate a PR by creating an Issue to keep the demo environment non-destructive
        pr_sim = repo.create_issue(title=f"[NexusOps-Fix] {title}", body=body)
        logger.info(f"Remediation Proposal Dispatched: Issue #{pr_sim.number}")
        return f"Remediation Plan Proposed: {pr_sim.html_url}"
    except Exception as e:
        logger.error(f"GitHub Integration Failure: {e}")
        return f"Automation Error: Failed to dispatch PR to {repo_name}."

# --- Graph Orchestration Strategy ---



class GraphOrchestrator:
    def __init__(self):
        # Initializing LLM with zero-temperature for deterministic SRE routing
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        
        # Defining logical tool isolation for security-aware routing
        self.diagnostic_tools = [search_playbooks, fetch_k8s_logs]
        self.execution_tools = [create_github_remediation_pr]
        
        self.all_tools = self.diagnostic_tools + self.execution_tools
        self.llm_engine = self.llm.bind_tools(self.all_tools)

    def agent_brain(self, state: AgentState):
        """
        Inference node: Analyzes the current message stack and decides the next action.
        """
        response = self.llm_engine.invoke(state['messages'])
        return {"messages": [response]}

    def route_decision(self, state: AgentState) -> Literal["safe_zone", "governor_gate", "__end__"]:
        """
        Router logic: Separates read-only diagnostics from destructive execution.
        """
        last_msg = state['messages'][-1]
        
        if not last_msg.tool_calls:
            return "__end__"
            
        # Inspect for high-risk operations requiring a 'Governor' interrupt
        exec_tool_names = [t.name for t in self.execution_tools]
        for call in last_msg.tool_calls:
            if call['name'] in exec_tool_names:
                return "governor_gate"
        
        return "safe_zone"

    def build_graph(self):
        """
        Compiles the state machine with persistence and safety interrupts.
        """
        builder = StateGraph(AgentState)

        # Node Registration
        builder.add_node("agent", self.agent_brain)
        builder.add_node("safe_zone", ToolNode(self.diagnostic_tools))
        builder.add_node("governor_gate", ToolNode(self.execution_tools))

        # Lifecycle Edges
        builder.set_entry_point("agent")
        builder.add_conditional_edges("agent", self.route_decision)
        builder.add_edge("safe_zone", "agent")
        builder.add_edge("governor_gate", "agent")

        # Persistence Layer for HITL (Human-in-the-Loop)
        checkpointer = MemorySaver()
        
        # The 'interrupt_before' is crucial—it's the safety brake for the agent
        return builder.compile(
            checkpointer=checkpointer, 
            interrupt_before=["governor_gate"]
        )
