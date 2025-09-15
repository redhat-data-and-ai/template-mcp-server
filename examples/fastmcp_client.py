#!/usr/bin/env python3
"""MCP Server Demo - Using FastMCP Client.

This example demonstrates how to connect to the running template MCP server
using the FastMCP Client and make actual MCP protocol calls.
"""

import asyncio
import json

import requests
from fastmcp import Client


class FastMCPClient:
    """Demo client for the template MCP server using FastMCP Client."""

    def __init__(self, server_url: str):
        """Initialize the MCP client demo.

        Args:
            server_url: URL of the MCP server
        """
        self.server_url = server_url
        self.health_endpoint = f"{server_url}/health"

        # MCP configuration
        self.config = {
            "mcpServers": {"template_mcp_server": {"url": f"{server_url}/mcp"}}
        }

    def check_server_health(self):
        """Check if the MCP server is healthy."""
        try:
            response = requests.get(self.health_endpoint, timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                print("✅ MCP Server is healthy!")
                print(f"   Service: {health_data.get('service')}")
                print(f"   Transport Protocol: {health_data.get('transport_protocol')}")
                print(f"   Version: {health_data.get('version')}")
                return True
            else:
                print(f"❌ MCP Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error connecting to MCP server: {e}")
            return False

    async def demonstrate_tools(self, client):
        """Demonstrate the available tools using actual MCP calls."""
        print("\n" + "=" * 60)
        print("Available MCP Tools")
        print("=" * 60)

        try:
            # List available tools
            tools = await client.list_tools()
            print(f"Found {len(tools)} tool(s):")
            for tool in tools:
                print(f"   - {tool.name}: {tool.description}")
                print(f"     Arguments: {tool.inputSchema}")

            # Test multiply tool
            print("\n🔧 Testing multiply_numbers tool:")
            result = await client.call_tool("multiply_numbers", {"a": 15, "b": 7})
            print(f"   Result: {result}")

        except Exception as e:
            print(f"   Error accessing tools: {e}")

    async def demonstrate_resources(self, client):
        """Demonstrate the available resources using actual MCP calls."""
        print("\n" + "=" * 60)
        print("Available MCP Resources")
        print("=" * 60)

        try:
            # List available resources
            resources = await client.list_resources()
            print(f"Found {len(resources)} resource(s):")
            for resource in resources:
                print(f"   - {resource.name}: {resource.description}")
                print(f"     URI: {resource.uri}")

            # Test Red Hat logo resource
            print("\n📁 Testing Red Hat logo resource:")
            result = await client.read_resource("resource://redhat-logo")
            print(f"   Result: {json.loads(result[0].text)['text'][:100]}")

        except Exception as e:
            print(f"   Error accessing resources: {e}")

    async def demonstrate_prompts(self, client):
        """Demonstrate the available prompts using actual MCP calls."""
        print("\n" + "=" * 60)
        print("Available MCP Prompts")
        print("=" * 60)

        try:
            # List available prompts
            prompts = await client.list_prompts()
            print(f"Found {len(prompts)} prompt(s):")
            for prompt in prompts:
                print(f"   - {prompt.name}: {prompt.description}")

            # Test code review prompt
            print("\n💬 Testing code review prompt:")
            result = await client.get_prompt(
                "get_code_review_prompt",
                {"code": "def add(a, b): return a + b", "language": "python"},
            )
            print(f"   Result: {result}")

        except Exception as e:
            print(f"   Error accessing prompts: {e}")

    async def run_demo(self):
        """Run the complete demo using FastMCP Client."""
        print("Template MCP Server Demo with FastMCP Client")
        print("=" * 60)

        # Check server health
        if not self.check_server_health():
            print("❌ Cannot proceed without a healthy MCP server")
            return

        # Create MCP client
        client = Client(self.config)

        try:
            async with client:
                print("✅ Connected to MCP server")

                # Demonstrate capabilities
                await self.demonstrate_tools(client)
                await self.demonstrate_resources(client)
                await self.demonstrate_prompts(client)

                print("\n✅ Demo completed successfully!")
                print("\nThis demonstrates actual MCP protocol calls for:")
                print("- Tools for mathematical operations")
                print("- Resources for file and asset access")
                print("- Prompts for code review and analysis")

        except Exception as e:
            print(f"❌ Error during demo: {e}")


async def main():
    """Main function to run the demo."""
    # Test MCP server deployed locally
    demo = FastMCPClient(server_url="http://0.0.0.0:8080")

    # Test MCP server deployed on openshift
    # demo = FastMCPClient(server_url="https://template-mcp-server.apps.int.spoke.preprod.us-west-2.aws.paas.redhat.com")
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
