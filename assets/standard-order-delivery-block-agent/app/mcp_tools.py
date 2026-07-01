"""MCP tool loader.

Owned indirection layer between agent code and the Agent Gateway.
All agent code imports get_mcp_tools from here.

In local/test mode (IBD_TESTING=1): reads mcp-mock.json from the asset root
and returns LangChain StructuredTool instances - no network calls.
In production: uses Agent Gateway client via mTLS.
"""

import json
import logging
import os
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any, Optional

from pydantic import Field, create_model
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)

StrOrNone = Optional[str]

_user_token_context: ContextVar[StrOrNone] = ContextVar("user_token", default=None)
_agw_client: Optional[Any] = None
_MOCK_FILE = Path(__file__).parent.parent / "mcp-mock.json"


def _build_mock_tools() -> list:
    if not _MOCK_FILE.exists():
        return []
    try:
        mock_data = json.loads(_MOCK_FILE.read_text())
    except Exception:
        logger.warning("Failed to parse mcp-mock.json at %s", _MOCK_FILE, exc_info=True)
        return []
    tools = []
    for _server_slug, server in mock_data.get("servers", {}).items():
        for tool_name, tool_def in server.get("tools", {}).items():
            description = tool_def.get("description", "")
            mock_response = tool_def.get("mock_response", {})
            input_schema = tool_def.get("input_schema", {})
            props = input_schema.get("properties", {})
            required_fields = set(input_schema.get("required", []))
            field_definitions: dict = {}
            for field_name, field_info in props.items():
                json_type = field_info.get("type", "string")
                if json_type == "integer":
                    python_type: Any = int
                elif json_type == "number":
                    python_type = float
                elif json_type == "boolean":
                    python_type = bool
                else:
                    python_type = str
                if field_name in required_fields:
                    field_definitions[field_name] = (python_type, Field(description=field_info.get("description", "")))
                else:
                    field_definitions[field_name] = (
                        python_type,
                        Field(default=None, description=field_info.get("description", "")),
                    )
            args_schema = (
                create_model(f"{tool_name}_args", **field_definitions)
                if field_definitions
                else create_model(f"{tool_name}_args")
            )
            _response = json.dumps(mock_response)

            async def _coroutine(_resp: str = _response, **kwargs: Any) -> str:
                return _resp

            tools.append(
                StructuredTool(
                    name=tool_name,
                    description=description,
                    args_schema=args_schema,
                    coroutine=_coroutine,
                    handle_tool_error=True,
                )
            )
    logger.info("Loaded %d mock MCP tool(s) from %s", len(tools), _MOCK_FILE)
    return tools


async def get_mcp_tools(user_token=None) -> list:
    """Return the list of available MCP tools as LangChain StructuredTool instances."""
    global _agw_client
    if os.environ.get("IBD_TESTING") == "1":
        return _build_mock_tools()
    if not user_token:
        raise ValueError("user_token is required for listing and calling MCP tools")
    try:
        from sap_cloud_sdk.agentgateway import create_client  # type: ignore

        if _agw_client is None:
            _agw_client = create_client()
        tok = user_token
        mcp_tools_list = await _agw_client.list_mcp_tools(user_token=tok)
        if not mcp_tools_list:
            return []
        langchain_tools = []
        for mcp_tool in mcp_tools_list:
            try:
                tool = _convert_mcp_tool_to_langchain(mcp_tool, _agw_client)
                langchain_tools.append(tool)
            except Exception as e:
                logger.warning("Failed to convert tool '%s': %s", mcp_tool.name, e)
        return langchain_tools
    except Exception:
        logger.exception("Failed to load MCP tools from Agent Gateway")
        _agw_client = None
        return []


def _convert_mcp_tool_to_langchain(mcp_tool: Any, agw_client: Any) -> StructuredTool:
    from util import enhance_tool_description, enhance_tool_name, call_mcp_tool_with_retry

    async def run(**kwargs: Any) -> str:
        tok = _user_token_context.get()
        return await call_mcp_tool_with_retry(agw_client, mcp_tool, user_token=tok, **kwargs)

    properties = mcp_tool.input_schema.get("properties", {})
    required = set(mcp_tool.input_schema.get("required", []))
    fields: dict = {}
    for name, prop in properties.items():
        prop_type = prop.get("type", "string")
        if prop_type == "integer":
            python_type_inner: Any = int
        elif prop_type == "number":
            python_type_inner = float
        elif prop_type == "boolean":
            python_type_inner = bool
        else:
            python_type_inner = str
        if name in required:
            fields[name] = (python_type_inner, ...)
        else:
            fields[name] = (Optional[python_type_inner], None)
    args_schema = create_model(f"{mcp_tool.name}_args", **fields) if fields else None
    return StructuredTool.from_function(
        coroutine=run,
        name=enhance_tool_name(mcp_tool),
        description=enhance_tool_description(mcp_tool),
        args_schema=args_schema,
        handle_tool_error=True,
    )


def set_user_token(user_token) -> Token:
    return _user_token_context.set(user_token)


def get_user_token() -> StrOrNone:
    return _user_token_context.get()
