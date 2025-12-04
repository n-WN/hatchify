import asyncio

from loguru import logger

from hatchify.core.factory.tool_factory import ToolRouter
from hatchify.core.manager.mcp_manager import mcp_manager
from hatchify.core.mcp.mcp_tool_loader import MCPToolLoader
from hatchify.core.tools.math_tool import math_router

tool_factory = ToolRouter()

tool_factory.include_router(math_router)


def load_strands_tools():
    try:
        from strands.tools.loader import load_tools_from_module
        from strands_tools import file_read, image_reader, editor, file_write

        modules = {
            "file_read": file_read,
            "image_reader": image_reader,
            "editor": editor,
            "file_write": file_write
        }

        for module_name, module in modules.items():
            tools = load_tools_from_module(module, module_name)
            for tool in tools:
                tool_factory.register(tool)
                logger.info(f"Loaded strands_tool: {tool.tool_name}")
    except ImportError as e:
        logger.warning(f"Failed to load strands_tools: {e}")


async def async_load_strands_tools():
    await asyncio.to_thread(load_strands_tools)


def load_mcp_server():
    if enabled_servers := mcp_manager.get_enabled_servers():
        mcp_tools = MCPToolLoader.load_mcp_tools(enabled_servers)
        for tool in mcp_tools:
            tool_factory.register(tool)
            logger.info(tool.tool_name)


async def async_load_mcp_server():
    if enabled_servers := mcp_manager.get_enabled_servers():
        mcp_tools = await MCPToolLoader.async_load_mcp_tools(enabled_servers)
        for tool in mcp_tools:
            tool_factory.register(tool)
            logger.info(tool.tool_name)


async def get_tool_info():
    await asyncio.gather(
        async_load_strands_tools(),
        async_load_mcp_server()
    )
    for tool, desc in tool_factory.get_all_tools().items():
        print(desc.tool_name, desc.tool_spec)


if __name__ == '__main__':
    asyncio.run(get_tool_info())