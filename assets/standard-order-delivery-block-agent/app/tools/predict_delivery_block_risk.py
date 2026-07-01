"""
Tool: predict_delivery_block_risk

Calls the SAP RPT-1 AI model via MCP tool to predict Delivery Block risk.
Falls back to rule-based scoring when the RPT-1 MCP tool is unavailable.
"""
import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Risk thresholds
HIGH_RISK_THRESHOLD = 70
MEDIUM_RISK_THRESHOLD = 40


class PredictDeliveryBlockRiskInput(BaseModel):
    SoldToParty: str = Field(description="Customer (Sold-To Party) code, e.g. '0000001000'")
    Material: str = Field(description="Material number, e.g. 'TG11'")
    RequestedQuantity: float = Field(description="Order quantity")
    RequestedDeliveryDate: str = Field(description="Requested delivery date in YYYY-MM-DD format")
    SalesOrganization: str = Field(description="Sales organization code, e.g. '1710'")
    DistributionChannel: str = Field(description="Distribution channel code, e.g. '10'")
    Division: str = Field(description="Division code, e.g. '00'")
    CreditLimit: float = Field(default=0.0, description="Customer credit limit (optional, used for rule-based fallback)")
    CurrentExposure: float = Field(default=0.0, description="Current credit exposure (optional, used for rule-based fallback)")


def _rule_based_risk_score(
    sold_to_party: str,
    requested_quantity: float,
    credit_limit: float,
    current_exposure: float,
    requested_delivery_date: str,
) -> dict:
    """Fallback rule-based risk scoring when RPT-1 is unavailable."""
    risk_score = 20  # base score
    risk_factors = []

    # Credit check
    if credit_limit > 0 and current_exposure > 0:
        credit_usage_pct = (current_exposure / credit_limit) * 100
        if credit_usage_pct > 90:
            risk_score += 50
            risk_factors.append(f"신용 한도 사용률 {credit_usage_pct:.1f}% — 초과 위험")
        elif credit_usage_pct > 75:
            risk_score += 25
            risk_factors.append(f"신용 한도 사용률 {credit_usage_pct:.1f}% — 주의")

    # Quantity check (large orders carry more risk)
    if requested_quantity > 1000:
        risk_score += 10
        risk_factors.append(f"대량 주문({requested_quantity}개) — 재고 가용성 확인 필요")

    if not risk_factors:
        risk_factors.append("특이 위험 인자 없음")

    risk_score = min(risk_score, 100)

    if risk_score >= HIGH_RISK_THRESHOLD:
        risk_level = "high"
        recommendation = "신용 부서의 사전 승인을 받거나 납기일을 조정한 후 주문을 생성하세요."
    elif risk_score >= MEDIUM_RISK_THRESHOLD:
        risk_level = "medium"
        recommendation = "배송 일정 및 재고 상황을 확인한 후 주문을 진행하세요."
    else:
        risk_level = "low"
        recommendation = "위험 수준이 낮습니다. 주문을 정상 진행할 수 있습니다."

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "recommendation": recommendation,
        "model_used": "rule-based-fallback",
    }


async def _predict_delivery_block_risk(
    SoldToParty: str,
    Material: str,
    RequestedQuantity: float,
    RequestedDeliveryDate: str,
    SalesOrganization: str,
    DistributionChannel: str,
    Division: str,
    CreditLimit: float = 0.0,
    CurrentExposure: float = 0.0,
) -> dict:
    """
    Predict Delivery Block risk using SAP RPT-1 model via MCP.

    M2 milestone: Delivery Block 위험 예측
    Returns risk_score (0-100), risk_level, risk_factors, recommendation.
    """
    try:
        # Try to call RPT-1 via MCP tool (if available at runtime)
        from mcp_tools import get_mcp_tools, get_user_token
        tok = get_user_token()
        tools = await get_mcp_tools(tok)
        rpt1_tool = None
        for tool in tools:
            if "rpt" in tool.name.lower() or "delivery_block" in tool.name.lower() or "risk" in tool.name.lower():
                rpt1_tool = tool
                break

        if rpt1_tool:
            result = await rpt1_tool.ainvoke({
                "SoldToParty": SoldToParty,
                "Material": Material,
                "RequestedQuantity": RequestedQuantity,
                "RequestedDeliveryDate": RequestedDeliveryDate,
                "SalesOrganization": SalesOrganization,
                "DistributionChannel": DistributionChannel,
                "Division": Division,
            })
            logger.info("M2.achieved: delivery block risk predicted via RPT-1, score=%s", result.get("risk_score"))
            return result

    except Exception as e:
        logger.warning("RPT-1 MCP tool unavailable, using rule-based fallback: %s", e)

    # Fallback to rule-based scoring
    result = _rule_based_risk_score(
        sold_to_party=SoldToParty,
        requested_quantity=RequestedQuantity,
        credit_limit=CreditLimit,
        current_exposure=CurrentExposure,
        requested_delivery_date=RequestedDeliveryDate,
    )
    logger.info(
        "M2.achieved: delivery block risk predicted, score=%s",
        result["risk_score"],
        extra={"milestone": "M2", "status": "achieved", "risk_score": result["risk_score"]},
    )
    return result


predict_delivery_block_risk = StructuredTool.from_function(
    coroutine=_predict_delivery_block_risk,
    name="predict_delivery_block_risk",
    description=(
        "SAP RPT-1 AI 모델을 사용하여 주문의 Delivery Block 발생 가능성을 예측합니다. "
        "위험 점수(0-100), 위험 수준(high/medium/low), 위험 인자 목록, 권장 조치를 반환합니다."
    ),
    args_schema=PredictDeliveryBlockRiskInput,
    handle_tool_error=True,
)
