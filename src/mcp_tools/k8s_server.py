from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from pydantic import BaseModel, Field
import asyncio

# Mock K8s Library for demo if not configured
try:
    from kubernetes import client, config
    config.load_kube_config()
    K8S_AVAILABLE = True
except Exception:
    K8S_AVAILABLE = False

# --- Schema Definition ---
class GetPodLogsParams(BaseModel):
    pod_name: str = Field(..., description="Name of the pod to fetch logs from")
    namespace: str = Field("default", description="Namespace of the pod")
    tail_lines: int = Field(100, description="Number of lines to return from the end of the logs")

# --- Server Setup ---
server = Server("k8s-mcp-server")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_pod_logs",
            description="Fetch logs from a Kubernetes pod",
            inputSchema=GetPodLogsParams.model_json_schema(),
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "get_pod_logs":
        # Validate Arguments
        try:
            params = GetPodLogsParams(**arguments)
        except Exception as e:
            return [types.TextContent(type="text", text=f"Validation Error: {str(e)}")]

        if not K8S_AVAILABLE:
            # Return Mock Data for the prototype environment
            return [types.TextContent(
                type="text",
                text=f"[MOCK K8S] Logs for {params.pod_name} in {params.namespace}:\n... [Previous logs] ...\nError: OOMKilled\nTimestamp: 2026-02-13 10:00:00"
            )]

        try:
            v1 = client.CoreV1Api()
            logs = v1.read_namespaced_pod_log(
                name=params.pod_name,
                namespace=params.namespace,
                tail_lines=params.tail_lines
            )
            return [types.TextContent(type="text", text=logs)]
        except Exception as e:
            return [types.TextContent(type="text", text=f"K8s Error: {str(e)}")]

    raise ValueError(f"Tool {name} not found")

async def run():
    # Run the server using stdio
    async with stdio_server() as (read, write):
        await server.run(read_stream=read, write_stream=write, initialization_options=server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(run())
