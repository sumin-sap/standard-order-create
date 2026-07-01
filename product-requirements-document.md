# Product Requirements Document (PRD)

**Title:** Standard Order 생성 및 Delivery Block 사전 예측 AI 에이전트  
**Date:** 2026-07-01  
**Owner:** Sales Operations  
**Solution Category:** AI Agent

---

## Business Context

### 비즈니스 배경 (Business Background)

글로벌 제조·유통 기업의 영업팀은 매일 수백 건의 표준 주문(Standard Order)을 SAP S/4HANA에 입력한다. 이 중 일부는 주문 생성 이후 **Delivery Block(배송 차단)** 상태로 전환되어 배송이 지연되며, 이는 고객 불만, 계약 위반, 수익 손실로 이어진다.

현재 프로세스의 핵심 문제는 **Delivery Block이 사후(事後) 감지**된다는 점이다. 영업 담당자는 주문을 생성한 뒤, 물류팀이나 고객으로부터 문제를 통보받은 후에야 원인을 파악하고 대응한다. 이 시점에는 이미 고객의 기대를 저버린 상태다.

### 비즈니스 프로세스 위치 (Process Placement)

본 솔루션은 SAP 참조 비즈니스 아키텍처(RBA)의 **Lead to Cash (L2C)** 프로세스 내, **Order to Fulfill** 단계의 **고객 주문 관리(BPS-361)** 서브프로세스에 위치한다.

```
Lead to Cash (E2E)
└── Order to Fulfill
    └── Manage Customer Orders and Contracts (BPS-361)
        ├── Create Standard Sales Order          ← 기존 프로세스
        ├── Predict Delivery Block Risk (RPT-1)  ← AI 증강 (신규)
        └── Alert & Guide Sales Representative   ← AI 증강 (신규)
```

### 영향 받는 이해관계자 (Affected Stakeholders)

| 역할 | 현재 불편 | 기대 효과 |
|------|-----------|-----------|
| **영업 담당자** | 주문 생성 후 배송 차단 통보를 사후에 받음 | 주문 입력 시점에 위험 경고 및 권장 조치 수신 |
| **물류/창고 팀** | 갑작스러운 배송 차단 처리로 운영 혼란 | 선제적 물류 계획 수립 가능 |
| **신용 관리 부서** | 신용 한도 초과 주문 사후 승인 요청 과다 | 고위험 주문 사전 식별로 승인 프로세스 최적화 |
| **고객** | 납기일 미준수로 인한 불만 | 정확한 납기 약속 및 배송 신뢰도 향상 |

### 핵심 지표 (Key Metrics)

- **배송 차단 발생률**: AI 도입 전후 Delivery Block 건수 비교
- **사전 경고 적중률**: RPT-1 예측 경고 중 실제 배송 차단으로 전환된 비율
- **주문 처리 시간**: 위험 예측 포함 주문 생성 완료까지의 평균 소요 시간
- **영업 담당자 만족도**: 경고 메시지의 유용성 및 실행 가능성 평가

### AI 도입 근거 (AI Justification)

SAP **RPT-1(Risk Prediction Tool-1)** 모델은 주문 데이터(고객 신용 등급, 재고 수준, 요청 납기일, 과거 배송 이력 등)를 종합하여 배송 차단 발생 가능성을 0~100점 척도로 예측한다. 이 모델을 주문 생성 워크플로우에 통합함으로써, 영업 담당자가 **데이터 기반 의사결정**을 주문 입력 시점에 수행할 수 있도록 지원한다.

LLM(Large Language Model)은 RPT-1의 위험 점수와 위험 인자를 **한국어 자연어**로 해석하여, 영업 담당자가 즉시 이해하고 행동할 수 있는 경고 메시지와 권장 조치를 생성한다.

---

## Product Purpose & Value Proposition

**Elevator Pitch:**  
영업 담당자가 표준 주문을 입력하는 순간, AI 에이전트가 SAP RPT-1 모델을 호출하여 배송 차단(Delivery Block) 발생 가능성을 즉시 예측하고 경고를 제공함으로써, 배송 지연을 선제적으로 방지한다.

**Business Need:**  
현재 Delivery Block은 주문 생성 이후에야 사후적으로 감지된다. 이로 인해 영업팀은 고객 불만을 접수한 뒤에야 문제를 인지하며, 배송 지연 해소에 많은 시간과 비용이 소요된다. 주문 입력 시점에 위험을 사전 식별할 수 있다면 이를 원천 차단할 수 있다.

**Product Objectives:**
1. 주문 생성 전 Delivery Block 위험 자동 예측 및 경고 제공
2. SAP S/4HANA API를 통한 Standard Order 자동 생성
3. 위험 사유에 기반한 자연어 권장 조치 제공

---

## Requirements

### Must-Have Requirements

**R1: 주문 정보 수집 및 파라미터 추출**

- **User Story**: 영업 담당자로서 자연어로 주문 정보를 입력하면, 에이전트가 SAP 주문 생성에 필요한 파라미터(고객 코드, 자재번호, 수량, 요청 납기일 등)를 자동으로 추출해주길 원한다.
- **Acceptance Criteria**:
  - 주문에 필요한 필수 항목이 누락된 경우 에이전트가 재질문
  - 추출된 파라미터를 사용자에게 확인 요청
- **Priority Rank**: 1

**R2: Delivery Block 위험 예측 (RPT-1 연동)**

- **User Story**: 영업 담당자로서 주문 정보를 기반으로 Delivery Block 발생 가능성과 그 사유를 사전에 알고 싶다.
- **Acceptance Criteria**:
  - RPT-1 모델에 주문 데이터 전달 후 위험 점수(0~100) 및 주요 위험 인자 반환
  - 위험 점수 임계값(예: 70 이상) 초과 시 명시적 경고 메시지 표시
  - 위험 사유를 한국어 자연어로 설명
- **Priority Rank**: 2

**R3: 경고 메시지 및 권장 조치 제공**

- **User Story**: 위험이 높은 경우, 어떤 조치를 취해야 할지 구체적인 권장 사항을 받고 싶다.
- **Acceptance Criteria**:
  - 신용 한도 초과 위험 → 신용 부서 사전 승인 권장
  - 재고 부족 위험 → 납기일 조정 또는 분할 배송 권장
  - 경고 없이 주문 강행 여부를 사용자가 선택 가능
- **Priority Rank**: 3

**R4: SAP S/4HANA Standard Order 생성**

- **User Story**: 위험 확인 후 사용자가 승인하면 실제 주문이 SAP에 자동으로 생성되길 원한다.
- **Acceptance Criteria**:
  - `API_SALES_ORDER_SRV` OData API를 통해 주문 유형 OR(Standard Order) 생성
  - 성공 시 주문 번호 반환
  - 실패 시 SAP 오류 메시지를 사용자에게 전달
- **Priority Rank**: 4

**R5: 최종 결과 요약**

- **User Story**: 주문 생성 후 전체 과정(예측 결과 + 주문 번호)을 한 눈에 볼 수 있는 요약이 필요하다.
- **Acceptance Criteria**:
  - 주문 번호, 위험 점수, 경고 여부, 생성 시각을 포함한 요약 출력
- **Priority Rank**: 5

---

## Solution Architecture

**Architecture Overview:**  
SAP BTP에서 실행되는 Python 기반 AI 에이전트(A2A 프로토콜). 사용자 자연어 입력 → 파라미터 추출 → RPT-1 위험 예측 → 경고/권장 조치 → 주문 생성 순으로 동작한다.

**Key Components:**

- **AI Agent (Python)**: 대화 관리, 의도 파악, 도구 오케스트레이션
- **RPT-1 Prediction Tool**: SAP RPT-1 모델 API 래퍼 — Delivery Block 위험 점수 반환
- **Sales Order Tool**: `API_SALES_ORDER_SRV` OData API 래퍼 — 주문 생성/조회
- **Sales Order Simulate Tool**: `API_SALES_ORDER_SIMULATION_SRV` — 생성 전 유효성 검증
- **SAP AI Core**: LLM 추론 및 자연어 경고 메시지 생성

**Integration Points:**

- SAP S/4HANA `API_SALES_ORDER_SRV` (OData, 주문 생성)
- SAP S/4HANA `API_SALES_ORDER_SIMULATION_SRV` (OData, 주문 시뮬레이션)
- SAP RPT-1 모델 (REST, 위험 예측)

### Agent Extensibility & Instrumentation

**Agent Extensibility:**
- 도구(tool) 기반 아키텍처로 RPT-1 외 추가 예측 모델 플러그인 가능
- 새로운 위험 인자(신용, 재고, 운송 등) 추가를 위한 확장 포인트 제공

**Business Step Instrumentation:**
- 각 주요 단계에서 구조화된 로그를 emit하여 운영 모니터링 지원
- 로그 패턴: `[MILESTONE_ID].[achieved|missed]: [description]`

### Automation & Agent Behaviour

**Automation Level:** Hybrid (AI 추론 + Human-in-the-loop 승인)

**사람 승인 없이 자동 수행:**
- 주문 파라미터 추출
- RPT-1 위험 점수 조회
- 주문 시뮬레이션 실행

**사람 검토/승인 필요:**
- 경고 발생 시 주문 계속 진행 여부 확인
- 최종 SAP 주문 생성 전 사용자 확인

**사용 모델:** SAP AI Core (GPT-4o / Generative AI Hub)

**도구 목록:**
- `create_sales_order` — SAP에 Standard Order 생성 (쓰기)
- `simulate_sales_order` — 주문 유효성 사전 검증 (읽기)
- `predict_delivery_block_risk` — RPT-1 모델로 위험 점수 반환 (읽기)

**Guardrails:**
- 위험 점수 ≥ 70일 경우 사용자 확인 없이 주문 생성 불가
- SAP API 오류 발생 시 사용자에게 오류 상세 전달 후 중단
- 주문 생성은 항상 사용자 최종 승인 후 실행

---

## Milestones

### M1: 주문 정보 수집 완료

- **Achieved when**: 필수 파라미터(고객, 자재, 수량, 납기일) 모두 수집
- **Log on achievement**: `M1.achieved: order parameters collected successfully`
- **Log on miss**: `M1.missed: required order parameters incomplete`

### M2: Delivery Block 위험 예측 완료

- **Achieved when**: RPT-1 모델로부터 위험 점수 및 위험 인자 반환
- **Log on achievement**: `M2.achieved: delivery block risk predicted, score={score}`
- **Log on miss**: `M2.missed: rpt1 model call failed or returned no score`

### M3: 경고 판단 및 사용자 통보

- **Achieved when**: 위험 점수 기반 경고 메시지 및 권장 조치 사용자에게 전달
- **Log on achievement**: `M3.achieved: warning issued, risk_level={high|medium|low}`
- **Log on miss**: `M3.missed: warning generation failed`

### M4: 주문 생성 실행

- **Achieved when**: SAP S/4HANA에 Standard Order 성공적으로 생성, 주문 번호 수신
- **Log on achievement**: `M4.achieved: sales order created, order_id={order_id}`
- **Log on miss**: `M4.missed: sales order creation failed, reason={error}`

### M5: 최종 결과 요약 제공

- **Achieved when**: 주문 번호, 위험 점수, 경고 여부 포함 요약을 사용자에게 전달
- **Log on achievement**: `M5.achieved: final summary delivered to user`
- **Log on miss**: `M5.missed: summary generation failed`
