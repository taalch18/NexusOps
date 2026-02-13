from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from pydantic import BaseModel, Field
import asyncio
import os

# --- Schema Definition ---
class CreatePRParams(BaseModel):
    repo_name: str = Field(..., description="Repository name in format 'owner/repo'")
    title: str = Field(..., description="Title of the Pull Request")
    body: str = Field(..., description="Description/Body of the Pull Request")
    head: str = Field(..., description="Name of the branch where changes are implemented")
    base: str = Field("main", description="Name of the branch you want to merge into")

# --- Server Setup ---
server = Server("github-mcp-server")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="create_pull_request",
            description="Draft a new Pull Request on GitHub",
            inputSchema=CreatePRParams.model_json_schema(),
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "create_pull_request":
        # Validate Arguments
        try:
            params = CreatePRParams(**arguments)
        except Exception as e:
            return [types.TextContent(type="text", text=f"Validation Error: {str(e)}")]

        token = os.getenv("GITHUB_TOKEN")
        if not token:
             return [types.TextContent(
                type="text",
                text=f"[MOCK GITHUB] Drafted PR '{params.title}' in {params.repo_name} from {params.head} to {params.base}.\n(No GITHUB_TOKEN set, operating in mock mode)"
            )]

        try:
            from github import Github
            g = Github(token)
            repo = g.get_repo(params.repo_name)
            pr = repo.create_pull(
                title=params.title,
                body=params.body,
                head=params.head,
                base=params.base
            )
            return [types.TextContent(type="text", text=f"Successfully created PR #{pr.number}: {pr.html_url}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"GitHub API Error: {str(e)}")]

    raise ValueError(f"Tool {name} not found")

async def run():
    async with stdio_server() as (read, write):
        await server.run(read_stream=read, write_stream=write, initialization_options=server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(run())
