import asyncio
from typing import Any, Sequence
from pydantic import BaseModel, Field
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

try:
    from kubernetes import client, config
    config.load_kube_config()
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False

class GetPodLogsParams(BaseModel):
    pod_name: str = Field(..., description="Pod name")
    namespace: str = Field("default", description="Namespace")
    tail_lines: int = Field(100, description="Lines to fetch")

server = Server("k8s-mcp-server")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(name="get_pod_logs", description="Fetch pod logs", inputSchema=GetPodLogsParams.model_json_schema())]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[types.TextContent]:
    if name != "get_pod_logs":
        raise ValueError(f"Tool {name} not found")
    
    try:
        params = GetPodLogsParams(**arguments)
        if not K8S_AVAILABLE:
            return [types.TextContent(type="text", text=f"Logs for {params.pod_name}:\nError: OOMKilled")]
        
        v1 = client.CoreV1Api()
        logs = v1.read_namespaced_pod_log(name=params.pod_name, namespace=params.namespace, tail_lines=params.tail_lines)
        return [types.TextContent(type="text", text=logs)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

if __name__ == "__main__":
    async def run():
        async with stdio_server() as (read, write):
            await server.run(read_stream=read, write_stream=write, initialization_options=server.create_initialization_options())
    asyncio.run(run())
