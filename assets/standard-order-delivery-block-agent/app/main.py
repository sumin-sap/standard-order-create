# CRITICAL: Initialize telemetry BEFORE importing AI frameworks
from sap_cloud_sdk.aicore import set_aicore_config
from sap_cloud_sdk.core.telemetry import auto_instrument

set_aicore_config()
auto_instrument()

import logging
import os

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from starlette.middleware.base import BaseHTTPMiddleware

from agent_executor import AgentExecutor
from mcp_tools import set_user_token
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))


class JWTContextMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts JWT token from Authorization header and sets it in context."""

    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("authorization", "")
        token = None
        if auth_header.lower().startswith("bearer "):
            _jwt = next(reversed(auth_header.split(None, 1)), None)
            token = _jwt

        set_user_token(token)

        try:
            response = await call_next(request)
            return response
        finally:
            set_user_token(None)


@click.command()
@click.option("--host", default=HOST)
@click.option("--port", default=PORT)
def main(host: str, port: int):
    skill = AgentSkill(
        id="standard-order-delivery-block-agent",
        name="standard-order-delivery-block-agent",
        description=(
            "SAP Standard Order(OR) 생성 및 RPT-1 AI 모델 기반 "
            "Delivery Block 위험 사전 예측 에이전트. "
            "영업 담당자가 주문 생성 전 배송 차단 위험을 조기에 경고받을 수 있습니다."
        ),
        tags=["standard-order", "delivery-block", "agent", "rpt1"],
        examples=[
            "삼성전자(고객코드 1000) 앞으로 자재 TG11 100개, 납기 2026-08-15로 표준 주문 만들어줘.",
            "고객 3000번, 자재 HM-500 1000개 주문 전에 Delivery Block 위험 먼저 확인해줘.",
        ],
    )
    agent_card = AgentCard(
        name="standard-order-delivery-block-agent",
        description=(
            "SAP S/4HANA Standard Order 생성과 RPT-1 AI 모델을 활용한 "
            "Delivery Block 위험 사전 예측을 수행하는 AI 에이전트입니다."
        ),
        url=os.environ.get("AGENT_PUBLIC_URL", f"http://{host}:{port}/"),
        version="1.0.0",
        default_input_modes=["text", "text/plain"],
        default_output_modes=["text", "text/plain"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        skills=[skill],
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=DefaultRequestHandler(
            agent_executor=AgentExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    )
    app = server.build()
    app.add_middleware(JWTContextMiddleware)
    StarletteInstrumentor().instrument_app(app)
    logger.info(f"Starting A2A server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
