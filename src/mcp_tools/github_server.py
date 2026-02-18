import os
import asyncio
import logging
from typing import Any, Sequence
from pydantic import BaseModel, Field, ValidationError
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Initialize SRE-grade logging for MCP orchestration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - NexusMCP - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PullRequestSchema(BaseModel):
    """
    Strict validation schema for GitHub PR creation.
    """
    repo_name: str = Field(..., description="Target repository (format: owner/repo)")
    title: str = Field(..., description="Concise PR title")
    body: str = Field(..., description="Detailed description of the remediation logic")
    head: str = Field(..., description="Source branch containing the fix")
    base: str = Field("main", description="Destination branch for the merge")

# Initializing the NexusOps GitHub MCP Server
server = Server("nexus-github-provider")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    Advertises available SRE automation tools to the Nexus orchestrator.
    """
    return [
        types.Tool(
            name="create_remediation_pr",
            description="Automates the creation of a GitHub Pull Request for system fixes.",
            inputSchema=PullRequestSchema.model_json_schema()
        )
    ]

@server.call_tool()
async def execute_tool(name: str, arguments: Any) -> Sequence[types.TextContent]:
    """
    Secure execution handler for MCP tool calls.
    """
    if name != "create_remediation_pr":
        logger.error(f"Unsupported tool invocation: {name}")
        raise ValueError(f"Provider error: Tool '{name}' is not registered.")
        
    try:
        # Validate arguments against Pydantic schema
        params = PullRequestSchema(**arguments)
        gh_token = os.getenv("GITHUB_TOKEN")
        
        if not gh_token:
            logger.warning(f"GITHUB_TOKEN missing. Simulation mode active for {params.repo_name}")
            return [types.TextContent(
                type="text", 
                text=f"DRY-RUN: PR '{params.title}' drafted. (Reason: Missing Authentication)"
            )]

        # Lazy-load PyGithub to keep the MCP server footprint light
        from github import Github, GithubException
        
        client = Github(gh_token)
        repo = client.get_repo(params.repo_name)
        
        logger.info(f"Initiating PR on {params.repo_name} from branch {params.head}")
        
        pr = repo.create_pull(
            title=params.title, 
            body=params.body, 
            head=params.head, 
            base=params.base
        )
        
        return [types.TextContent(
            type="text", 
            text=f"SUCCESS: Remediation PR #{pr.number} initialized at {pr.html_url}"
        )]

    except ValidationError as ve:
        logger.error(f"Payload validation failed: {ve.json()}")
        return [types.TextContent(type="text", text=f"Schema Error: {str(ve)}")]
    except Exception as e:
        logger.critical(f"MCP Tool Execution Failure: {str(e)}")
        return [types.TextContent(type="text", text=f"Runtime Error: Internal MCP failure.")]

if __name__ == "__main__":
    async def bootstrap():
        """
        Initializes the MCP server over Stdio for LangGraph integration.
        """
        logger.info("NexusMCP Server starting...")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=server.create_initialization_options()
            )
            
    try:
        asyncio.run(bootstrap())
    except KeyboardInterrupt:
        logger.info("NexusMCP Server offline.")
