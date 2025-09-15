"""LangGraph MCP Client Example - Template MCP Server Integration.

This example demonstrates how to create a LangGraph agent that connects to the
template MCP server and uses its available tools for mathematical operations.

The example shows:
- Setting up a LangGraph ReAct agent with Google's Gemini model
- Connecting to the template MCP server via HTTP transport
- Using MCP tools for mathematical calculations
- Handling tool calls and responses in a conversational context

Prerequisites:
- Template MCP server must be running on http://0.0.0.0:4000
- Google Generative AI credentials must be configured via
    GEMINI_API_KEY environment variable or
    GOOGLE_APPLICATION_CREDENTIALS environment variable
- All required Python packages must be installed
- Required dependencies: langchain-google-genai, langchain-mcp-adapters, langgraph

Note:
- LangGraph's create_react_agent only supports MCP tools, not MCP resources or prompts
- It's recommended to stick to MCP tools when using LangGraph agents
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

current_date = datetime.now().strftime("%B %d, %Y")


def check_gemini_credentials():
    """Check for GEMINI API key or Google credentials JSON.

    This function verifies that either:
    1. GEMINI_API_KEY environment variable is set, or
    2. GOOGLE_APPLICATION_CREDENTIALS environment variable points to a valid JSON file

    Returns:
        bool: True if valid credentials are found, False otherwise

    Raises:
        SystemExit: If no valid credentials are found, with helpful error message
    """
    # Check for GEMINI_API_KEY environment variable
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        print("✅ GEMINI_API_KEY environment variable found")
        return True

    # Check for GOOGLE_APPLICATION_CREDENTIALS environment variable
    google_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if google_creds_path:
        creds_file = Path(google_creds_path)
        if creds_file.exists():
            try:
                # Try to read and validate the JSON file
                import json

                with open(creds_file, "r") as f:
                    creds_data = json.load(f)

                # Check if it has the required fields for Google service account
                if isinstance(creds_data, dict) and "type" in creds_data:
                    print(f"✅ Google credentials JSON file found at: {creds_file}")
                    return True
                else:
                    print(f"❌ Invalid Google credentials JSON format in: {creds_file}")
                    print("   Expected a JSON object with 'type' field")
                    return False
            except json.JSONDecodeError:
                print(
                    f"❌ Invalid JSON format in Google credentials file: {creds_file}"
                )
                return False
            except Exception as e:
                print(f"❌ Error reading Google credentials file: {e}")
                return False
        else:
            print(f"❌ Google credentials file not found at: {creds_file}")
            return False

    # No valid credentials found
    print("❌ No valid GEMINI credentials found!")
    print("\nTo fix this, set one of the following:")
    print("1. GEMINI_API_KEY environment variable:")
    print("   export GEMINI_API_KEY='your-api-key-here'")
    print("\n2. GOOGLE_APPLICATION_CREDENTIALS environment variable:")
    print(
        "   export GOOGLE_APPLICATION_CREDENTIALS='/path/to/your/service-account-key.json'"
    )
    print("\nFor more information, visit:")
    print("   https://ai.google.dev/tutorials/setup")
    print("   https://cloud.google.com/docs/authentication/getting-started")

    return False


# Check credentials before proceeding
if not check_gemini_credentials():
    sys.exit(1)


system_prompt = f"""
    You are an Agent, a helpful assistant with the ability to use specialized tools.

    Today's date is {current_date}.

    A few things to remember:
    - **Only use the tools you are given to answer the user's question.** Do not answer directly from internal knowledge.
    - **You must always reason before acting.**
    - **Every Final Answer must be grounded in tool observations.**
    - **Always make sure your answer is *FORMATTED WELL*.**
    """


@asynccontextmanager
async def get_agent_redhat():
    """Create and yield a fully initialized LangGraph agent with MCP integration.

    This function sets up a LangGraph ReAct agent that connects to the template
    MCP server and uses Google's Gemini model for reasoning and tool usage.

    The agent is configured with:
    - Google Generative AI (Gemini 2.0 Flash) as the language model
    - Tools from the template MCP server (e.g., multiply_numbers)
    - A system prompt that guides tool usage and response formatting

    Note:
    - LangGraph agents only support MCP tools, not MCP resources or prompts
    - For resources and prompts, use MultiServerMCPClient directly
    - This example focuses on tool usage which is the recommended approach

    Yields:
        A configured LangGraph agent that can use MCP tools for calculations
        and other operations provided by the template MCP server.

    Example:
        async with get_agent_redhat() as agent:
            result = await agent.ainvoke({
                "messages": [{"role": "user", "content": "What is 5 * 3?"}]
            })
    """
    # Test MCP server deployed locally
    # Initialize MCP client and get tools
    client = MultiServerMCPClient(
        {
            "template_mcp_server": {
                "url": "http://0.0.0.0:8080/mcp/",
                "transport": "streamable_http",
            },
        }
    )

    tools = await client.get_tools()
    # resources = await client.get_resources(tools)

    agent_redhat = create_react_agent(
        model=ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.5,
        ),
        prompt=system_prompt,
        tools=tools,
    )
    yield agent_redhat


async def demonstrate_tool_calls():
    """Demonstrate MCP tool calls using the LangGraph agent.

    This function shows how the LangGraph agent can use tools from the template
    MCP server to perform mathematical operations. It demonstrates:

    1. Tool Selection: How the agent decides which tool to use
    2. Parameter Formatting: How the agent formats tool parameters
    3. Response Processing: How the agent interprets tool responses
    4. Final Answer Generation: How the agent provides user-friendly responses

    The example uses the multiply_numbers tool to perform calculations
    and shows the complete conversation flow including tool calls.
    """
    print("\n" + "=" * 60)
    print("🔧 Tool Call Examples")
    print("=" * 60)

    async with get_agent_redhat() as agent:
        # Example 1: Mathematical operation
        print("\n📊 Example 1: Mathematical Operation")
        print("Question: What is 15 multiplied by 7?")

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "What is 15 multiplied by 7?"}]}
        )
        print(f"Agent Response: {result}")


async def main():
    """Run the complete LangGraph MCP client demonstration.

    This main function orchestrates all the demonstration examples and provides
    a comprehensive overview of LangGraph integration with the template MCP server.

    The demonstration includes:
    - Tool call examples showing mathematical operations
    - Error handling for connection issues
    - Summary of demonstrated capabilities

    Raises:
        Exception: If the MCP server is not accessible or other connection issues occur
    """
    print("🚀 LangGraph MCP Client Examples")
    print("=" * 60)
    print("This demonstrates various capabilities of the LangGraph agent")
    print("connected to the template MCP server.")

    try:
        # Run all examples
        await demonstrate_tool_calls()

        print("\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        print("\nThis demonstrates:")
        print("- 🔧 Tool calls for mathematical operations")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure the template MCP server is running on http://0.0.0.0:4000")


if __name__ == "__main__":
    asyncio.run(main())
