"""MCP (Model Context Protocol) Gateway for Reflex AI Assistant."""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MCPMessageType(Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_id: str


@dataclass
class MCPResource:
    """Represents an MCP resource."""
    uri: str
    name: str
    description: str
    mime_type: str
    server_id: str


class MCPGateway:
    """MCP Gateway for consuming external servers and tools."""
    
    def __init__(self):
        self.servers: Dict[str, 'MCPServer'] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def register_server(self, server_id: str, server_url: str, config: Dict[str, Any]) -> bool:
        """Register an MCP server."""
        try:
            server = MCPServer(server_id, server_url, config)
            await server.initialize(self.session)
            
            self.servers[server_id] = server
            
            # Register tools and resources
            for tool in server.tools:
                self.tools[tool.name] = tool
            
            for resource in server.resources:
                self.resources[resource.uri] = resource
            
            logger.info(f"Registered MCP server: {server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register MCP server {server_id}: {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        
        tool = self.tools[tool_name]
        server = self.servers[tool.server_id]
        
        return await server.call_tool(tool_name, arguments)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "server_id": tool.server_id
            }
            for tool in self.tools.values()
        ]
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources."""
        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mime_type": resource.mime_type,
                "server_id": resource.server_id
            }
            for resource in self.resources.values()
        ]
    
    async def get_resource(self, uri: str) -> Optional[Dict[str, Any]]:
        """Get a specific resource."""
        if uri not in self.resources:
            return None
        
        resource = self.resources[uri]
        server = self.servers[resource.server_id]
        
        return await server.get_resource(uri)


class MCPServer:
    """Represents an MCP server connection."""
    
    def __init__(self, server_id: str, server_url: str, config: Dict[str, Any]):
        self.server_id = server_id
        self.server_url = server_url
        self.config = config
        self.tools: List[MCPTool] = []
        self.resources: List[MCPResource] = []
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self, session: aiohttp.ClientSession):
        """Initialize the server connection."""
        self.session = session
        
        # Initialize the server
        await self._send_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "clientInfo": {
                    "name": "Reflex AI Assistant",
                    "version": "1.0.0"
                }
            }
        })
        
        # Get tools and resources
        await self._load_tools()
        await self._load_resources()
    
    async def _send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to the MCP server."""
        if not self.session:
            raise RuntimeError("Server not initialized")
        
        async with self.session.post(
            self.server_url,
            json=message,
            headers={"Content-Type": "application/json"}
        ) as response:
            return await response.json()
    
    async def _load_tools(self):
        """Load available tools from the server."""
        try:
            response = await self._send_message({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            })
            
            if "result" in response and "tools" in response["result"]:
                for tool_data in response["result"]["tools"]:
                    tool = MCPTool(
                        name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        server_id=self.server_id
                    )
                    self.tools.append(tool)
                    
        except Exception as e:
            logger.error(f"Failed to load tools from {self.server_id}: {e}")
    
    async def _load_resources(self):
        """Load available resources from the server."""
        try:
            response = await self._send_message({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/list"
            })
            
            if "result" in response and "resources" in response["result"]:
                for resource_data in response["result"]["resources"]:
                    resource = MCPResource(
                        uri=resource_data["uri"],
                        name=resource_data.get("name", ""),
                        description=resource_data.get("description", ""),
                        mime_type=resource_data.get("mimeType", "text/plain"),
                        server_id=self.server_id
                    )
                    self.resources.append(resource)
                    
        except Exception as e:
            logger.error(f"Failed to load resources from {self.server_id}: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on this server."""
        response = await self._send_message({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        })
        
        if "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")
        
        return response.get("result", {})
    
    async def get_resource(self, uri: str) -> Optional[Dict[str, Any]]:
        """Get a resource from this server."""
        response = await self._send_message({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        })
        
        if "error" in response:
            logger.error(f"Failed to get resource {uri}: {response['error']}")
            return None
        
        return response.get("result", {})


class OpenAPIMCPServer(MCPServer):
    """OpenAPI MCP server for arbitrary OpenAPI tools."""
    
    def __init__(self, server_id: str, openapi_spec_url: str, base_url: str):
        super().__init__(server_id, base_url, {})
        self.openapi_spec_url = openapi_spec_url
        self.openapi_spec: Optional[Dict[str, Any]] = None
    
    async def initialize(self, session: aiohttp.ClientSession):
        """Initialize with OpenAPI specification."""
        self.session = session
        
        # Load OpenAPI specification
        await self._load_openapi_spec()
        
        # Convert OpenAPI operations to MCP tools
        await self._convert_openapi_to_tools()
    
    async def _load_openapi_spec(self):
        """Load OpenAPI specification."""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        async with self.session.get(self.openapi_spec_url) as response:
            self.openapi_spec = await response.json()
    
    async def _convert_openapi_to_tools(self):
        """Convert OpenAPI operations to MCP tools."""
        if not self.openapi_spec:
            return
        
        for path, path_item in self.openapi_spec.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    tool_name = f"{method.upper()}_{path.replace('/', '_').strip('_')}"
                    
                    # Extract parameters
                    parameters = operation.get("parameters", [])
                    request_body = operation.get("requestBody", {})
                    
                    # Build input schema
                    input_schema = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                    
                    # Add path parameters
                    for param in parameters:
                        if param.get("in") == "path":
                            input_schema["properties"][param["name"]] = {
                                "type": param.get("schema", {}).get("type", "string"),
                                "description": param.get("description", "")
                            }
                            if param.get("required", False):
                                input_schema["required"].append(param["name"])
                    
                    # Add query parameters
                    for param in parameters:
                        if param.get("in") == "query":
                            input_schema["properties"][param["name"]] = {
                                "type": param.get("schema", {}).get("type", "string"),
                                "description": param.get("description", "")
                            }
                    
                    # Add request body
                    if request_body:
                        content = request_body.get("content", {})
                        for content_type, schema in content.items():
                            if content_type == "application/json":
                                input_schema["properties"]["body"] = schema.get("schema", {})
                                if request_body.get("required", False):
                                    input_schema["required"].append("body")
                    
                    tool = MCPTool(
                        name=tool_name,
                        description=operation.get("summary", operation.get("description", "")),
                        input_schema=input_schema,
                        server_id=self.server_id
                    )
                    self.tools.append(tool)
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an OpenAPI tool."""
        # Parse tool name to extract method and path
        parts = tool_name.split("_", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid tool name format: {tool_name}")
        
        method, path = parts[0], parts[1].replace("_", "/")
        
        # Build URL
        url = f"{self.server_url}{path}"
        
        # Extract parameters
        params = {}
        body = None
        
        for key, value in arguments.items():
            if key == "body":
                body = value
            else:
                params[key] = value
        
        # Make HTTP request
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        async with self.session.request(
            method.lower(),
            url,
            params=params,
            json=body
        ) as response:
            result = await response.json()
            
            return {
                "status_code": response.status,
                "data": result
            }


class MCPIntegrationManager:
    """Manages MCP integrations for Reflex AI Assistant."""
    
    def __init__(self):
        self.gateway: Optional[MCPGateway] = None
        self.integrations: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """Initialize the MCP integration manager."""
        self.gateway = MCPGateway()
        await self.gateway.__aenter__()
        
        # Register default integrations
        await self._register_default_integrations()
    
    async def _register_default_integrations(self):
        """Register default MCP integrations."""
        
        # OpenAPI MCP server for arbitrary APIs
        openapi_server = OpenAPIMCPServer(
            "openapi-mcp",
            "https://api.example.com/openapi.json",
            "https://api.example.com"
        )
        
        # High-value servers
        high_value_servers = [
            {
                "id": "github-mcp",
                "url": "https://api.github.com",
                "type": "openapi",
                "description": "GitHub API integration"
            },
            {
                "id": "slack-mcp",
                "url": "https://slack.com/api",
                "type": "openapi",
                "description": "Slack API integration"
            },
            {
                "id": "notion-mcp",
                "url": "https://api.notion.com",
                "type": "openapi",
                "description": "Notion API integration"
            }
        ]
        
        for server_config in high_value_servers:
            try:
                if server_config["type"] == "openapi":
                    server = OpenAPIMCPServer(
                        server_config["id"],
                        f"{server_config['url']}/openapi.json",
                        server_config["url"]
                    )
                    await server.initialize(self.gateway.session)
                    self.gateway.servers[server_config["id"]] = server
                    
                    # Register tools
                    for tool in server.tools:
                        self.gateway.tools[tool.name] = tool
                    
                    self.integrations[server_config["id"]] = server_config
                    logger.info(f"Registered MCP server: {server_config['id']}")
                    
            except Exception as e:
                logger.error(f"Failed to register {server_config['id']}: {e}")
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available MCP tools."""
        if not self.gateway:
            return []
        
        return await self.gateway.list_tools()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        if not self.gateway:
            raise RuntimeError("MCP Gateway not initialized")
        
        return await self.gateway.call_tool(tool_name, arguments)
    
    async def register_custom_server(self, server_id: str, server_url: str, config: Dict[str, Any]) -> bool:
        """Register a custom MCP server."""
        if not self.gateway:
            return False
        
        return await self.gateway.register_server(server_id, server_url, config)
    
    async def cleanup(self):
        """Cleanup MCP resources."""
        if self.gateway:
            await self.gateway.__aexit__(None, None, None)


# Global MCP integration manager instance
mcp_manager: Optional[MCPIntegrationManager] = None


async def get_mcp_manager() -> MCPIntegrationManager:
    """Get the global MCP integration manager."""
    global mcp_manager
    
    if mcp_manager is None:
        mcp_manager = MCPIntegrationManager()
        await mcp_manager.initialize()
    
    return mcp_manager


async def cleanup_mcp_manager():
    """Cleanup the global MCP integration manager."""
    global mcp_manager
    
    if mcp_manager:
        await mcp_manager.cleanup()
        mcp_manager = None 