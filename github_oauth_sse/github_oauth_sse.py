import os
from typing import Any
import httpx
import uvicorn
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth
from mcp.server.fastmcp import FastMCP
from starlette.config import Config
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse # Added JSONResponse
from starlette.routing import Mount, Route
from mcp.server import Server

load_dotenv()

# Initialize FastMCP server for Github OAuth tools (SSE)
mcp = FastMCP("github_oauth_sse")

SECRET_KEY = os.getenv('SECRET_KEY')
middleware = [
    Middleware(SessionMiddleware, secret_key=SECRET_KEY)
]

# 配置 OAuth
oauth = OAuth(Config('.env'))
oauth.register(
    name='github',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

@mcp.tool()
async def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: integer
        b: integer
    """
    return a + b

async def login(request: Request):
    redirect_uri = request.url_for('callback')
    print(redirect_uri)
    return await oauth.github.authorize_redirect(request, redirect_uri)

async def callback(request: Request):
    try:
        token = await oauth.github.authorize_access_token(request)
        request.session['github_token'] = token # Store token in session
        # Optionally fetch user info and store it too
        # resp = await oauth.github.get('user', token=token)
        # user = resp.json()
        # request.session['user'] = user
        print("GitHub OAuth successful, token stored in session.")
        # Redirect to a success page or return JSON
        return JSONResponse({'message': 'Login successful', 'token_type': token.get('token_type')})
    except Exception as e:
        print(f"Error during GitHub OAuth callback: {e}")
        return JSONResponse({'error': 'Authentication failed', 'details': str(e)}, status_code=400)

async def logout(request: Request):
    request.session.pop('github_token', None)
    # request.session.pop('user', None) # Also clear user info if stored
    print("User logged out, session cleared.")
    return JSONResponse({'message': 'Logout successful'})


async def handle_sse(request: Request) -> None:
    # --- Authentication Check ---
    if 'github_token' not in request.session:
        print("SSE connection attempt failed: User not authenticated.")
        redirect_uri = str(request.url_for('callback'))
        print(f"Callback redirect_uri --- {redirect_uri}")
        # return await oauth.github.authorize_redirect(request, redirect_uri)
        auth_url_info = await oauth.github.create_authorization_url(redirect_uri)
        auth_url = auth_url_info['url']
        return RedirectResponse(url=auth_url, status_code=401)
        # Return an error response instead of establishing connection
        # Note: SSE clients might not handle standard HTTP error responses well during the connection phase.
        # A more robust solution might involve sending an error event through SSE if connection starts,
        # but preventing connection entirely is simpler here.
        # We'll send a 401 Unauthorized status code.
        # response = JSONResponse({'error': 'Unauthorized. Please login via /login first.'}, status_code=401)
        # await response(request.scope, request.receive, request._send) # Send the response
        # return # Stop processing

    print("SSE connection authorized.")
    # Proceed with SSE connection if authenticated
    async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,  # noqa: SLF001
    ) as (read_stream, write_stream):
        # Here you could potentially pass auth details from the session
        # to the MCP server if its tools need it, e.g., via initialization options.
        init_options = mcp_server.create_initialization_options()
        # Example: init_options['auth_token'] = request.session['github_token']['access_token']
        await mcp_server.run(
            read_stream,
            write_stream,
            init_options,
        )


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")
    return Starlette(
        debug=debug,
        routes=[
            Route("/login", endpoint=login, methods=['GET']),
            Route("/callback", endpoint=callback, methods=['GET']),
            Route("/logout", endpoint=logout, methods=['GET']),
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
        middleware=middleware
    )

if __name__ == "__main__":
    mcp_server = mcp._mcp_server  # noqa: WPS437

    import argparse
    
    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)