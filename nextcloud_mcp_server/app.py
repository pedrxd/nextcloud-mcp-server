import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastmcp import FastMCP, Context
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from nextcloud_mcp_server.client import NextcloudClient
from nextcloud_mcp_server.config import setup_logging
from nextcloud_mcp_server.server import (
    configure_calendar_tools,
    configure_contacts_tools,
    configure_notes_tools,
    configure_tables_tools,
    configure_webdav_tools,
)

setup_logging()


@dataclass
class AppContext:
    client: NextcloudClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    # Initialize on startup
    logging.info("Creating Nextcloud client")
    client = NextcloudClient.from_env()
    logging.info("Client initialization wait complete.")
    try:
        yield AppContext(client=client)
    finally:
        # Cleanup on shutdown
        await client.close()


verifier = None
if os.environ.get('FASTMCP_BEARER_TOKEN'):
    verifier = StaticTokenVerifier(
        tokens={
            os.environ['FASTMCP_BEARER_TOKEN']: {
                "client_id": "guest-user",
                "scopes": ["read:data"]
            }
        },
        required_scopes=["read:data"]
    )

# Create an MCP server
mcp = FastMCP("Nextcloud MCP", lifespan=app_lifespan, auth=verifier if verifier else None)

logger = logging.getLogger(__name__)


@mcp.resource("nc://capabilities")
async def nc_get_capabilities():
    """Get the Nextcloud Host capabilities"""
    ctx: Context = (
        mcp.get_context()
    )  # https://github.com/modelcontextprotocol/python-sdk/issues/244
    client: NextcloudClient = ctx.request_context.lifespan_context.client
    return await client.capabilities()


configure_notes_tools(mcp)
configure_tables_tools(mcp)
configure_webdav_tools(mcp)
configure_calendar_tools(mcp)
configure_contacts_tools(mcp)


if __name__ == "__main__":
    mcp.run()
