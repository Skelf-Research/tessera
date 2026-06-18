"""
API server startup for CLI.
"""

import asyncio
from typing import Optional

import uvicorn

from ..network.async_node import AsyncDecentralizedNode
from ..network.embedded_api import create_embedded_api


async def start_api_server(
    node: AsyncDecentralizedNode,
    host: str,
    port: int,
    jwt_secret: Optional[str] = None,
    rate_limit_rpm: int = 60
):
    """Start the embedded API server.

    Args:
        node: The node to serve API for
        host: Host to bind to
        port: Port to listen on
        jwt_secret: JWT secret for org node authentication
        rate_limit_rpm: Rate limit requests per minute
    """
    # Get commitment storage if this is an org node
    commitment_storage = getattr(node, 'commitment_storage', None)

    # Create the FastAPI app
    app = create_embedded_api(
        node=node,
        push_service=None,
        commitment_storage=commitment_storage,
        jwt_secret=jwt_secret,
        rate_limit_rpm=rate_limit_rpm
    )

    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False
    )

    server = uvicorn.Server(config)
    await server.serve()
