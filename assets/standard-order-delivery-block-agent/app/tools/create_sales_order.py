"""
Tool: create_sales_order

Creates a Standard Order (OR) in SAP S/4HANA via API_SALES_ORDER_SRV MCP tool.
"""
import json
import logging
from datetime import datetime
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CreateSalesOrderInput(BaseModel):
    SoldToParty: str = Field(description="Customer (Sold-To Party) code")
    Material: str = Field(description="Material number")
    RequestedQuantity: float = Field(description="Order quantity")
    RequestedDeliveryDate: str = Field(description="Requested delivery date YYYY-MM-DD")
    SalesOrganization: str = Field(description="Sales organization code, e.g. '1710'")
    DistributionChannel: str = Field(description="Distribution channel code, e.g. '10'")
    Division: str = Field(description="Division code, e.g. '00'")
    PurchaseOrderByCustomer: str = Field(default="", description="Customer PO number (optional)")


async def _create_sales_order(
    SoldToParty: str,
    Material: str,
    RequestedQuantity: float,
    RequestedDeliveryDate: str,
    SalesOrganization: str,
    DistributionChannel: str,
    Division: str,
    PurchaseOrderByCustomer: str = "",
) -> dict:
    """
    Create a Standard Order in SAP S/4HANA.

    M4 milestone: 주문 생성 실행
    Returns order number on success, error details on failure.
    """
    try:
        from mcp_tools import get_mcp_tools, get_user_token
        tok = get_user_token()
        tools = await get_mcp_tools(tok)
        # Primary: look for exact MCP tool name from translation.json
        CREATE_TOOL_NAME = "create_a_salesorder_for_api_sales_order_srv"
        create_tool = None
        for tool in tools:
            if tool.name == CREATE_TOOL_NAME:
                create_tool = tool
                break
        # Fallback: fuzzy match
        if not create_tool:
            for tool in tools:
                tool_lower = tool.name.lower()
                if ("sales_order" in tool_lower or "salesorder" in tool_lower) and (
                    "create" in tool_lower or "post" in tool_lower
                ) and "simulat" not in tool_lower:
                    create_tool = tool
                    break

        if not create_tool:
            return {
                "success": False,
                "error": "주문 생성 MCP 도구를 찾을 수 없습니다. MCP 서버 설정을 확인하세요.",
            }

        if create_tool:
            # Use lowercase parameter names as per translation.json newParameterName mappings
            payload = {
                "salesordertype": "OR",
                "soldtoparty": SoldToParty,
                "salesorganization": SalesOrganization,
                "distributionchannel": DistributionChannel,
                "organizationdivision": Division,
                "purchaseorderbycustomer": PurchaseOrderByCustomer,
                "to_item": [{
                    "SalesOrderItem": "000010",
                    "Material": Material,
                    "RequestedQuantity": str(RequestedQuantity),
                    "RequestedDeliveryDate": RequestedDeliveryDate.replace("-", ""),
                }],
            }
            raw_result = await create_tool.ainvoke(payload)
            try:
                result_data = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
            except Exception:
                result_data = {"raw": str(raw_result)}

            sales_order = result_data.get("SalesOrder") or result_data.get("d", {}).get("SalesOrder", "")
            if sales_order:
                logger.info(
                    "M4.achieved: sales order created, order_id=%s",
                    sales_order,
                    extra={"milestone": "M4", "status": "achieved", "order_id": sales_order},
                )
                return {
                    "success": True,
                    "SalesOrder": sales_order,
                    "created_at": datetime.now().isoformat(),
                    "status": "Created",
                    "raw": result_data,
                }
            else:
                error_msg = str(result_data.get("error", result_data))
                logger.warning(
                    "M4.missed: sales order creation failed, reason=%s",
                    error_msg,
                    extra={"milestone": "M4", "status": "missed", "error": error_msg},
                )
                return {"success": False, "error": error_msg, "raw": result_data}

    except Exception as e:
        logger.warning(
            "M4.missed: sales order creation failed, reason=%s",
            str(e),
            extra={"milestone": "M4", "status": "missed", "error": str(e)},
        )
        return {
            "success": False,
            "error": f"주문 생성 도구를 사용할 수 없습니다: {str(e)}",
        }


create_sales_order = StructuredTool.from_function(
    coroutine=_create_sales_order,
    name="create_sales_order",
    description=(
        "SAP S/4HANA에 Standard Order(주문유형 OR)를 생성합니다. "
        "생성 성공 시 주문 번호를 반환합니다."
    ),
    args_schema=CreateSalesOrderInput,
    handle_tool_error=True,
)
