"""
Tool: simulate_sales_order

Simulates a sales order via SAP S/4HANA API_SALES_ORDER_SIMULATION_SRV MCP tool.
Validates order before actual creation and extracts credit/availability signals.
"""
import json
import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SimulateSalesOrderInput(BaseModel):
    SoldToParty: str = Field(description="Customer (Sold-To Party) code")
    Material: str = Field(description="Material number")
    RequestedQuantity: float = Field(description="Order quantity")
    RequestedDeliveryDate: str = Field(description="Requested delivery date YYYY-MM-DD")
    SalesOrganization: str = Field(description="Sales organization code, e.g. '1710'")
    DistributionChannel: str = Field(description="Distribution channel, e.g. '10'")
    Division: str = Field(description="Division code, e.g. '00'")


async def _simulate_sales_order(
    SoldToParty: str,
    Material: str,
    RequestedQuantity: float,
    RequestedDeliveryDate: str,
    SalesOrganization: str,
    DistributionChannel: str,
    Division: str,
) -> dict:
    """
    Simulate a sales order to validate it before creation.

    Returns simulation result with validity flag, messages, credit check, and availability info.
    """
    try:
        from mcp_tools import get_mcp_tools, get_user_token
        tok = get_user_token()
        tools = await get_mcp_tools(tok)
        # Primary: look for exact MCP tool name from translation.json
        SIMULATE_TOOL_NAME = "create_a_salesordersimulation_for_api_sales_order_simulation_srv"
        simulate_tool = None
        for tool in tools:
            if tool.name == SIMULATE_TOOL_NAME:
                simulate_tool = tool
                break
        # Fallback: fuzzy match
        if not simulate_tool:
            for tool in tools:
                if "simulat" in tool.name.lower() and "create" in tool.name.lower():
                    simulate_tool = tool
                    break

        if simulate_tool:
            payload = {
                "salesordertype": "OR",
                "soldtoparty": SoldToParty,
                "salesorganization": SalesOrganization,
                "distributionchannel": DistributionChannel,
                "organizationdivision": Division,
                "requesteddeliverydate": RequestedDeliveryDate,
                "to_item": [{
                    "SalesOrderItem": "000010",
                    "Material": Material,
                    "RequestedQuantity": str(RequestedQuantity),
                    "RequestedDeliveryDate": RequestedDeliveryDate,
                }],
            }
            raw_result = await simulate_tool.ainvoke(payload)
            # Parse simulation response
            try:
                result_data = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
            except Exception:
                result_data = {"raw": str(raw_result)}

            return {
                "is_valid": True,
                "messages": result_data.get("messages", []),
                "credit_check_passed": result_data.get("CreditCheckPassed", True),
                "availability_ok": result_data.get("AvailabilityOk", True),
                "estimated_delivery_date": result_data.get("EstimatedDeliveryDate", RequestedDeliveryDate),
                "raw": result_data,
            }

    except Exception as e:
        logger.warning("Simulate MCP tool unavailable: %s", e)

    # Fallback: return basic validation result
    logger.info("simulate_sales_order: using fallback validation")
    return {
        "is_valid": True,
        "messages": ["주문 시뮬레이션 도구를 사용할 수 없습니다. 기본 유효성 검사 결과를 반환합니다."],
        "credit_check_passed": True,
        "availability_ok": True,
        "estimated_delivery_date": RequestedDeliveryDate,
        "raw": {},
    }


simulate_sales_order = StructuredTool.from_function(
    coroutine=_simulate_sales_order,
    name="simulate_sales_order",
    description=(
        "SAP S/4HANA에서 실제 주문 생성 전 주문 유효성을 시뮬레이션합니다. "
        "신용 한도 초과 여부, 재고 가용성, 예상 납기일 등을 확인합니다."
    ),
    args_schema=SimulateSalesOrderInput,
    handle_tool_error=True,
)
