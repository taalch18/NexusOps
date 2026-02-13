from typing import TypedDict, Annotated, List, Union, Any
from langgraph.graph import StateGraph, END
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage 
from langchain_core.tools import tool
from vector_store_wrapper import VectorStoreWrapper
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    next_step: str

# --- Tools ---
@tool
async def search_knowledge_base(query: str):
    """Searches the internal knowledge base."""
    store = VectorStoreWrapper()
    results = await store.search(query, top_k=3)
    context_str = "\n".join([f"- {r['metadata'].get('text', 'No text')}" for r in results])
    return f"Knowledge Base Results:\n{context_str}"

# --- Nodes ---

class GraphOrchestrator:
    def __init__(self, tools: List[Any] = None):
        # No LLM used. Pure heuristic/rule-based.
        self.tools = tools if tools else [search_knowledge_base]

    async def reason_node(self, state: AgentState):
        """
        Rule-Based Reasoning:
        1. Always search knowledge base.
        2. Check keywords for specific tools.
        """
        messages = state['messages']
        last_msg = messages[-1]
        
        # If the last message is from a tool, we are done
        if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
             # Already produced final answer
             return {"next_step": END}
             
        query = messages[0].content.lower()
        tool_calls = []
        
        # Heuristic 1: Inspect Logs
        if "log" in query or "error" in query or "oom" in query:
             # Basic extraction of pod name (mock/simple)
             pod_name = "backend-api" # Default for demo
             if "pod" in query:
                 # Simple parsing could go here
                 pass
             tool_calls.append({
                 "name": "get_pod_logs",
                 "args": {"pod_name": pod_name},
                 "id": "call_logs"
             })
             
        # Heuristic 2: Search Knowledge (Always useful)
        tool_calls.append({
             "name": "search_knowledge_base",
             "args": {"query": messages[0].content},
             "id": "call_search"
        })

        # Heuristic 3: Fix/PR (Only if requested)
        if "fix" in query or "pr" in query:
             tool_calls.append({
                 "name": "create_pull_request",
                 "args": {
                     "repo_name": "nexus/app",
                     "title": "Fix: Automated Remediation",
                     "body": f"Remediation for: {query}",
                     "head": "fix/automated-patch"
                 },
                 "id": "call_pr"
             })

        # Avoid infinite loops: if we just called tools, don't call them again in next turn
        # In a real ReAct loop, we'd check previous messages. 
        # For this concise demo, we'll do: Input -> Tools -> Final Answer.
        
        # If we have tool results in history? No, LangGraph `messages` appends.
        # If the last message was a ToolMessage, generating final answer.
        # Check if the last message was NOT from user (i.e. we just ran tools)
        if len(messages) > 1:
             # We assume we ran tools. Now summarize.
             return {"messages": [AIMessage(content="I have executed the requested actions based on the available tools.")]}
        
        return {"messages": [AIMessage(content="", tool_calls=tool_calls)]}

    async def tool_node(self, state: AgentState):
        messages = state['messages']
        last_message = messages[-1]
        
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {"next_step": END}
            
        tool_results = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            matched_tool = next((t for t in self.tools if t.name == tool_name), None)
            
            if matched_tool:
                try:
                    if hasattr(matched_tool, "ainvoke"):
                         res = await matched_tool.ainvoke(tool_args)
                    else:
                         res = matched_tool.invoke(tool_args)
                except Exception as e:
                    res = f"Error: {str(e)}"
            else:
                 res = f"Tool {tool_name} not found."
            
            from langchain_core.messages import ToolMessage
            tool_results.append(ToolMessage(
                tool_call_id=tool_call['id'],
                content=str(res),
                name=tool_name
            ))
            
        return {"messages": tool_results}

    def should_continue(self, state: AgentState):
        messages = state['messages']
        last_message = messages[-1]
        
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        # If we just got tool output, loop back to agent to finalize?
        # In my logic above, agent sees >1 msg and finalizes.
        if len(messages) > 1 and isinstance(messages[-1], ToolMessage): # Error: messages[-1] is ToolMessage
             # Check if last msg is ToolMessage
             return "agent" # Go back to agent to generate final string
             
        # Actually LangGraph specific:
        # If last was AIMessage with tools -> go tools.
        # If last was ToolMessage -> go agent.
        # If last was AIMessage w/o tools -> END.
        
        if isinstance(last_message, AIMessage) and not last_message.tool_calls:
            return END
            
        return "agent"

    def build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self.reason_node)
        workflow.add_node("tools", self.tool_node)
        workflow.set_entry_point("agent")
        
        workflow.add_conditional_edges("agent", self.should_continue, {"tools": "tools", END: END})
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
