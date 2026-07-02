"""
Tool: get_order_status

Retrieves the status of an existing SAP sales order,
including DeliveryBlockReason and OverallDeliveryStatus.
"""
import json
import logging

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GetOrderStatusInput(BaseModel):
    SalesOrder: str = Field(description="SAP Sales Order number, e.g. '0000000001'")


async def _get_order_status(SalesOrder: str) -> dict:
    """
    Retrieve order header data including DeliveryBlockReason and OverallDeliveryStatus.
    """
    try:
        from mcp_tools import get_mcp_tools, get_user_token
        tok = get_user_token()
        tools = await get_mcp_tools(tok)
        # Primary: look for exact MCP tool name from translation.json
        GET_TOOL_NAME = "get_a_salesorder_for_api_sales_order_srv"
        get_tool = None
        for tool in tools:
            if tool.name == GET_TOOL_NAME:
                get_tool = tool
                break
        # Fallback: fuzzy match
        if not get_tool:
            for tool in tools:
                tool_lower = tool.name.lower()
                if ("sales_order" in tool_lower or "salesorder" in tool_lower) and (
                    "get" in tool_lower
                ) and "simulat" not in tool_lower:
                    get_tool = tool
                    break

        if get_tool:
            # Use lowercase parameter name as per translation.json newParameterName mapping
            raw_result = await get_tool.ainvoke({"salesorder": SalesOrder})
            try:
                result_data = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
            except Exception:
                result_data = {"raw": str(raw_result)}

            order_data = result_data.get("d", result_data)
            return {
                "SalesOrder": SalesOrder,
                "DeliveryBlockReason": order_data.get("DeliveryBlockReason", ""),
                "OverallDeliveryStatus": order_data.get("OverallDeliveryStatus", ""),
                "SalesOrderStatus": order_data.get("OverallSDProcessStatus", ""),
                "raw": order_data,
            }

    except Exception as e:
        logger.warning("get_order_status MCP tool unavailable: %s", e)

    return {
        "SalesOrder": SalesOrder,
        "DeliveryBlockReason": "조회 불가",
        "OverallDeliveryStatus": "조회 불가",
        "error": "주문 상태 조회 도구를 사용할 수 없습니다.",
    }


get_order_status = StructuredTool.from_function(
    coroutine=_get_order_status,
    name="get_order_status",
    description=(
        "SAP 주문 번호로 주문 상태를 조회합니다. "
        "DeliveryBlockReason(배송 차단 사유), OverallDeliveryStatus(전체 배송 상태)를 반환합니다."
    ),
    args_schema=GetOrderStatusInput,
    handle_tool_error=True,
)
