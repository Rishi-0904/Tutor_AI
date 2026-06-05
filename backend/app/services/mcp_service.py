import os
import sys
import json
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from google import genai as google_genai
from google.genai import types
from app.core.config import settings

# Attempt to import mcp client, if it fails we will rely on fallbacks
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

class MCPService:
    def __init__(self):
        self.client_sessions: Dict[str, Any] = {}
        self.server_processes: Dict[str, Any] = {}

    async def connect_to_server(self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """Connects to a stdio-based MCP server."""
        if not MCP_AVAILABLE:
            print(f"[MCP] SDK not available. Cannot connect to {server_name}.")
            return False

        try:
            print(f"[MCP] Connecting to server {server_name} via {command} {' '.join(args)}...")
            server_params = StdioServerParameters(command=command, args=args, env=env)
            
            # Note: client connection requires keeping the stdio_client context open,
            # so we start it as an async task that maintains the session.
            transport = stdio_client(server_params)
            read_stream, write_stream = await transport.__aenter__()
            
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()
            
            self.client_sessions[server_name] = {
                'session': session,
                'transport': transport,
                'tools': await session.list_tools()
            }
            print(f"[MCP] Successfully connected to {server_name}!")
            return True
        except Exception as e:
            print(f"[MCP] Error connecting to {server_name}: {e}")
            return False

    async def disconnect_all(self):
        """Clean up all active MCP connections."""
        for name, conn in list(self.client_sessions.items()):
            try:
                await conn['session'].__aexit__(None, None, None)
                await conn['transport'].__aexit__(None, None, None)
                print(f"[MCP] Disconnected from {name}")
            except Exception as e:
                print(f"[MCP] Error disconnecting {name}: {e}")
        self.client_sessions.clear()

    async def call_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        """Calls a tool on a connected MCP server."""
        if server_name not in self.client_sessions:
            print(f"[MCP] Server {server_name} is not connected.")
            return None
        
        try:
            session = self.client_sessions[server_name]['session']
            result = await session.call_tool(tool_name, arguments=arguments)
            # FastMCP tools return stringified or raw structured results in content
            if result and result.content:
                # Extract the text from the first content block if possible
                text_content = result.content[0].text
                # Try parsing as JSON if it looks like a JSON string
                try:
                    return json.loads(text_content)
                except:
                    return text_content
            return None
        except Exception as e:
            print(f"[MCP] Error calling tool {tool_name} on {server_name}: {e}")
            return None

    # =====================================================================
    # INTERNAL MCP CLIENT WRAPPERS
    # =====================================================================
    
    async def get_student_profile(self, user_id: str) -> Dict[str, Any]:
        """Queries the internal MCP server for student details and masteries."""
        res = await self.call_mcp_tool("tutor_mcp", "get_student_profile", {"user_id": user_id})
        return res if isinstance(res, dict) else {}

    async def update_mastery_score(self, user_id: str, topic: str, score: int) -> Dict[str, Any]:
        """Queries the internal MCP server to upsert a topic mastery score."""
        res = await self.call_mcp_tool("tutor_mcp", "update_mastery_score", {"user_id": user_id, "topic": topic, "score": score})
        return res if isinstance(res, dict) else {}

    async def get_weak_topics(self, user_id: str) -> List[str]:
        """Queries the internal MCP server for the student's weak topics."""
        res = await self.call_mcp_tool("tutor_mcp", "get_weak_topics", {"user_id": user_id})
        return res if isinstance(res, list) else []

    async def get_learning_context(self, user_id: str) -> Dict[str, Any]:
        """Queries the internal MCP server for goals, weak/strong/recent topics, and tests."""
        res = await self.call_mcp_tool("tutor_mcp", "get_learning_context", {"user_id": user_id})
        return res if isinstance(res, dict) else {}

    async def search_pdf(self, query: str, user_id: str) -> str:
        """Queries the internal MCP server to perform pgvector similarity search on uploaded PDFs."""
        res = await self.call_mcp_tool("tutor_mcp", "search_pdf", {"query": query, "user_id": user_id})
        if isinstance(res, dict) and "results" in res:
            return res["results"]
        return str(res) if res else "No relevant textbook passages found."

    async def save_sketch(self, user_id: str, conversation_id: str, title: str, svg_data: str) -> Dict[str, Any]:
        """Queries the internal MCP server to save a whiteboard vector sketch."""
        res = await self.call_mcp_tool("tutor_mcp", "save_sketch", {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "title": title,
            "svg_data": svg_data
        })
        return res if isinstance(res, dict) else {}

    async def load_sketches(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        """Queries the internal MCP server to retrieve sketches for a conversation thread."""
        res = await self.call_mcp_tool("tutor_mcp", "load_sketches", {
            "user_id": user_id,
            "conversation_id": conversation_id
        })
        return res if isinstance(res, list) else []

# Singleton instance
mcp_service = MCPService()

# =====================================================================
# LOCAL LANGCHAIN / NATIVE EXTERNAL TOOLS
# =====================================================================

async def web_search_tool(query: str) -> str:
    """
    Search the web for tutoring context.
    Uses Gemini Search Grounding natively or falls back to public search endpoints.
    """
    # Native Fallback using Gemini Search Grounding
    api_key = settings.gemini_api_key
    if api_key:
        try:
            print(f"[Research Tool] Running Gemini Search Grounding for: '{query}'")
            client = google_genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=f"Search the web and summarize details for: {query}",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                )
            )
            # Check if search grounding metadata is returned
            grounding_metadata = response.candidates[0].grounding_metadata if response.candidates else None
            summary = response.text or ""
            
            if grounding_metadata and grounding_metadata.grounding_chunks:
                sources = []
                for chunk in grounding_metadata.grounding_chunks:
                    if chunk.web:
                        sources.append(f"- [{chunk.web.title}]({chunk.web.uri})")
                if sources:
                    summary += "\n\n**Sources:**\n" + "\n".join(sources[:4])
            return summary
        except Exception as e:
            print(f"[Research Tool] Gemini Search Grounding failed: {e}")

    # DuckDuckGo HTML Scraping fallback
    try:
        print(f"[Research Tool] Falling back to DuckDuckGo search scraper for: '{query}'")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://html.duckduckgo.com/html/?q={query}", headers=headers)
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                results = []
                for a in soup.find_all('a', class_='result__snippet')[:3]:
                    results.append(a.get_text().strip())
                if results:
                    return "\n\n".join(results)
    except Exception as e:
        print(f"[Research Tool] DuckDuckGo fallback failed: {e}")

    return f"Mock search results for: '{query}'. Unable to reach live web search index."

async def youtube_search_tool(query: str) -> str:
    """Searches YouTube for lecture videos and returns markdown links."""
    print(f"[YouTube Tool] Generating YouTube lecture resources for: '{query}'")
    search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}+jee"
    return (
        f"Here are recommended YouTube Lecture searches for **{query}**:\n"
        f"- [Search YouTube Lectures for {query}]({search_url})\n"
        f"- Recommended Channels for IIT-JEE: *Physics Galaxy*, *Mohit Tyagi*, *Vedantu JEE*, *Unacademy JEE*."
    )

async def code_executor_tool(code: str, language: str = "python") -> str:
    """Safe local Python interpreter logic."""
    if language.lower() == "python":
        print(f"[Code Tool] Running safe local python executor for math check...")
        try:
            allowed_globals = {
                "__builtins__": {
                    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
                    "float": float, "int": int, "len": len, "list": list, "max": max,
                    "min": min, "pow": pow, "range": range, "round": round, "set": set,
                    "str": str, "sum": sum, "tuple": tuple
                },
                "math": __import__("math")
            }
            local_vars = {}
            exec_code = f"def __run__():\n" + "\n".join(f"    {line}" for line in code.splitlines()) + "\n__res__ = __run__()"
            exec(exec_code, allowed_globals, local_vars)
            return f"Code executed successfully.\nResult variables: {local_vars.get('__res__', 'Success')}"
        except Exception as e:
            return f"Execution error: {e}"

    return "Code execution is only supported for Python in local sandbox mode."
