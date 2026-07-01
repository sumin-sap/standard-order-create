# Standard Order 생성 및 Delivery Block 사전 예측 AI 에이전트

SAP S/4HANA 기반 주문 생성 + RPT-1 AI 모델을 활용한 배송 차단 위험 사전 경고 에이전트

## Business challenge

영업 담당자가 표준 주문(Standard Order)을 생성하는 시점에, 해당 주문이 추후 Delivery Block(배송 차단)을 받을 가능성을 SAP RPT-1 AI 모델로 사전 예측하여 경고를 제공함으로써, 배송 지연을 선제적으로 방지하고 고객 서비스 수준을 높이고자 한다.

## Key Milestones

1. **주문 정보 수집**: 사용자로부터 주문 생성에 필요한 정보(고객, 자재, 수량, 납기일 등)를 수집
2. **Delivery Block 위험 예측**: RPT-1 AI 모델을 호출하여 해당 주문의 배송 차단 발생 가능성 점수 및 사유 도출
3. **경고 판단 및 통보**: 위험 점수가 임계값 초과 시 경고 메시지 생성 및 사용자에게 전달
4. **주문 생성 실행**: 사용자 확인 후 SAP S/4HANA에 실제 Standard Order 생성 (API_SALES_ORDER_SRV 호출)
5. **결과 확인 및 요약**: 생성된 주문 번호와 예측 결과를 최종 요약하여 반환

## Business Architecture (RBA)

### End-to-End Process

Lead to Cash (L2C)

### Process Hierarchy

```
Lead to Cash
└── Order to Fulfill
    └── Manage Customer Orders and Contracts (BPS-361)
        └── Create Standard Sales Order
        └── Predict Delivery Block Risk (AI augmentation)
        └── Alert Sales Representative
```

### Summary

표준 주문 생성 및 AI 기반 배송 차단 위험 예측은 Lead to Cash E2E의 Order to Fulfill 단계 중 고객 주문 관리(BPS-361)에 해당하며, SAP S/4HANA의 판매 주문 관리 역량에 AI 추론 레이어를 추가하는 확장 시나리오이다.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Gap? | Notes / assumptions |
| ---------------------- | ----------------------- | ---------- | ----------------- | ------------------ | ---- | ------------------- |
| Standard Order 생성 | SAP S/4HANA Sales Order Management (SC5146 / SC1001) | `sap.s4:apiResource:API_SALES_ORDER_SRV:v1` | — | — | No | OData API로 주문 생성 가능 |
| 주문 시뮬레이션 (사전 검증) | Sales Order Simulate (SC1001) | `sap.s4:apiResource:API_SALES_ORDER_SIMULATION_SRV:v1` | — | — | No | 생성 전 유효성 시뮬레이션 |
| Delivery Block 위험 예측 | SAP RPT-1 (AI 예측 모델) | — | — | — | Yes | RPT-1 모델 API 호출 필요; 커스텀 도구로 구현 |
| 위험 경고 메시지 생성 | SAP AI Core / LLM | — | — | — | Yes | 위험 수준 기반 자연어 경고 생성 |
| Delivery Block 상태 조회 | Delivery Doc with Credit Block API | `sap.s4:apiResource:API_DEL_DOC_WITH_CREDIT_BLOCK:v1` | — | — | No | 기존 블록 상태 확인용 |

### Key findings

- SAP S/4HANA의 표준 Sales Order OData API(API_SALES_ORDER_SRV)로 주문 생성 완전 지원
- Sales Order Simulate API로 생성 전 사전 유효성 검증 가능
- RPT-1 AI 모델 연동은 커스텀 도구(tool)로 구현 필요 — 표준 MCP 서버 미확인
- Delivery Block 예측은 AI Agent가 주문 데이터(고객 신용, 재고, 납기 등)를 분석해 위험 점수를 산출하는 방식으로 구현
- 경고 임계값 및 위험 사유 설명은 LLM 추론을 통해 자연어로 제공

## Recommendations

### Standard Order 생성 + Delivery Block 사전 예측 AI 에이전트

#### Executive Summary

SAP S/4HANA API + RPT-1 모델 연동 Python AI 에이전트

#### Recommended Solution

SAP BTP 위에서 동작하는 Python 기반 AI 에이전트로 구현한다. 에이전트는 (1) 사용자 요청을 자연어로 받아 주문 파라미터를 추출하고, (2) Sales Order Simulate API로 사전 검증 후, (3) RPT-1 AI 모델을 호출하여 Delivery Block 발생 가능성을 예측하며, (4) 위험 점수가 임계값을 초과하면 구체적 경고와 권장 조치를 제공하고, (5) 사용자 확인 후 실제 주문을 SAP S/4HANA에 생성한다.

#### Recommended solution category

AI Agent

#### Intent fit

88%
