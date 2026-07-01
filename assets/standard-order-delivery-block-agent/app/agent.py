import logging
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver
from opentelemetry import trace
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# ── Risk threshold constant (not a decorator – plain Python constant) ────────
DELIVERY_BLOCK_HIGH_RISK_THRESHOLD = 70
DELIVERY_BLOCK_MEDIUM_RISK_THRESHOLD = 40


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-4.5-sonnet"


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.1


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return """당신은 SAP S/4HANA 표준 주문(Standard Order) 생성 및 Delivery Block 위험 사전 예측 AI 에이전트입니다.

## 역할
영업 담당자가 새로운 표준 주문을 생성할 때, RPT-1 AI 모델을 활용하여 배송 차단(Delivery Block) 발생 가능성을 사전 예측하고, 위험이 높은 경우 경고와 함께 구체적인 권장 조치를 제공합니다.

## 처리 흐름
1. **주문 정보 수집**: 고객코드, 자재번호, 수량, 요청납기일, 판매조직, 유통채널, 사업부를 수집합니다. 누락 시 재질문합니다.
2. **주문 시뮬레이션**: `simulate_sales_order` 도구로 유효성을 사전 검증합니다.
3. **Delivery Block 위험 예측**: `predict_delivery_block_risk` 도구로 위험 점수(0-100)와 위험 인자를 분석합니다.
4. **경고 및 권장 조치 제공**:
   - 위험 점수 ≥ 70 (고위험): 명시적 경고 + 구체적 권장 조치 + 계속 진행 여부 확인 (사용자 승인 필수)
   - 위험 점수 40-69 (중위험): 주의 사항 안내 + 진행 여부 확인
   - 위험 점수 < 40 (저위험): 간단 확인 후 주문 생성
5. **주문 생성**: `create_sales_order` 도구로 SAP에 Standard Order(주문유형 OR) 생성
6. **결과 요약**: 주문번호, 위험점수, 경고여부, 생성시각을 포함한 요약 제공

## 중요 규칙
- 모든 응답은 한국어로 합니다 (사용자가 다른 언어를 사용하면 해당 언어로 전환)
- 주문 데이터를 절대 추측하거나 임의로 생성하지 마세요. 모든 값은 사용자 입력에서 가져와야 합니다.
- 고위험(점수 ≥ 70) 시 반드시 사용자 확인 없이 주문을 생성하지 마세요.
- 도구 오류 발생 시 오류 메시지를 그대로 사용자에게 전달하세요.
- 페이지 조회 도구 사용 시 `top` 파라미터를 최대 100으로 설정하세요.

## 도구 안내
- `predict_delivery_block_risk`: RPT-1 모델로 주문 데이터의 배송 차단 위험 분석
- `simulate_sales_order`: 실제 생성 전 주문 유효성 시뮬레이션
- `create_sales_order`: SAP S/4HANA에 Standard Order 생성
- `get_order_status`: 기존 주문의 배송 차단 상태 조회
"""


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


THREAD_TTL_SECONDS = 3600


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.llm = ChatLiteLLM(model=get_model_name(), temperature=get_temperature())
        self._checkpointer = InMemorySaver()
        self._last_active: dict[str, float] = {}
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
            keep=("messages", 4),
        )

    def _touch(self, thread_id: str) -> None:
        now = time.monotonic()
        expired = [
            tid
            for tid, ts in list(self._last_active.items())
            if now - ts > THREAD_TTL_SECONDS
        ]
        for tid in expired:
            self._checkpointer.delete_thread(tid)
            del self._last_active[tid]
            logger.info("Evicted inactive thread: %s", tid)
        self._last_active[thread_id] = now

    async def _run_agent(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> dict:
        """Core agent logic — extracted from stream() so spans don't wrap yields."""
        system_prompt = get_system_prompt()
        if not tools:
            system_prompt += "\n\nIMPORTANT: No tools are currently available. Do not attempt to call any tools. Respond to the user explaining that tools are temporarily unavailable."

        tool_names = [tool.name for tool in tools] if tools else []
        logger.info("Running agent with %d tool(s): %s", len(tool_names), tool_names)

        graph = create_agent(
            self.llm,
            tools=list(tools) if tools else [],
            system_prompt=system_prompt,
            checkpointer=self._checkpointer,
            middleware=[self._summarization_middleware],
        )
        config = {"configurable": {"thread_id": context_id}}
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=query)]}, config
        )
        self._touch(context_id)
        return result

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream agent responses."""
        self._touch(context_id)
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "처리 중...",
        }

        try:
            result = await self._run_agent(query, context_id, tools=tools)
            response = result["messages"][-1].content
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }
        except Exception as e:
            logger.exception("Agent stream() failed")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"요청 처리 중 오류가 발생했습니다: {str(e)}. 다시 시도해 주세요.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        """Invoke agent and return final response."""
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(
            status="error", message=last.get("content", "Unknown error")
        )
