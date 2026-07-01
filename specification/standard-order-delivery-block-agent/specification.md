# Specification: standard-order-delivery-block-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read the project input (`product-requirements-document.md`, `intent.md`)
- [x] Bootstrap agent code in `assets/standard-order-delivery-block-agent/` using skill `sap-agent-bootstrap`
- [ ] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

## API Spec Discovery

- [ ] Re-run API discovery for Sales Order and Sales Order Simulate APIs (pre-signed URLs expired):
  - Target APIs: `sap.s4:apiResource:API_SALES_ORDER_SRV:v1`, `sap.s4:apiResource:API_SALES_ORDER_SIMULATION_SRV:v1`
  - Call `sap_knowledge_graph_api_discovery` with query: "Create standard sales order SAP S/4HANA SD"
  - Download `.edmx` spec files to `specification/standard-order-delivery-block-agent/api-specs/`
- [ ] Invoke `mcp-translation-file` skill for each downloaded API spec to generate MCP translation files
  - If `mcp-translation-file` skill is unavailable, skip and note: agent will rely on direct OData tool wrappers
- [ ] Invoke `setup-solution` skill to register new MCP server assets (if translation files were generated)

## Project-Specific Tasks

### Tool: predict_delivery_block_risk

- [x] Create `assets/standard-order-delivery-block-agent/app/tools/predict_delivery_block_risk.py`
  - Input: order data dict (SoldToParty, Material, RequestedQuantity, RequestedDeliveryDate, SalesOrganization, DistributionChannel, Division)
  - Calls SAP RPT-1 model endpoint via MCP tool (or SAP AI Core inference if no MCP available)
  - Returns: `{ "risk_score": int (0-100), "risk_level": "high"|"medium"|"low", "risk_factors": list[str], "recommendation": str }`
  - Risk threshold: score ≥ 70 → "high", 40–69 → "medium", < 40 → "low"
  - If RPT-1 endpoint unavailable, use rule-based fallback: check credit limit, stock availability signals from order data
- [x] Register tool in `assets/standard-order-delivery-block-agent/app/tools/__init__.py`

### Tool: simulate_sales_order

- [x] Create `assets/standard-order-delivery-block-agent/app/tools/simulate_sales_order.py`
  - Wraps MCP tool generated from `API_SALES_ORDER_SIMULATION_SRV` (or existing MCP server)
  - Input: order parameters dict
  - Returns: simulation result (valid/invalid, messages, estimated delivery date, credit check result)
  - Extracts credit block signals, availability issues from simulation response
- [x] Register tool in `assets/standard-order-delivery-block-agent/app/tools/__init__.py`

### Tool: create_sales_order

- [x] Create `assets/standard-order-delivery-block-agent/app/tools/create_sales_order.py`
  - Wraps MCP tool generated from `API_SALES_ORDER_SRV` (or existing MCP server)
  - Input: full order parameters dict (SalesOrderType="OR", SoldToParty, Material, quantity, dates, org data)
  - Calls POST `/A_SalesOrder` endpoint via MCP
  - Returns: `{ "SalesOrder": str, "created_at": str, "status": str }`
  - On failure: returns structured error with SAP error code and message
- [x] Register tool in `assets/standard-order-delivery-block-agent/app/tools/__init__.py`

### Tool: get_order_status

- [x] Create `assets/standard-order-delivery-block-agent/app/tools/get_order_status.py`
  - Wraps MCP tool for `API_SALES_ORDER_SRV` GET endpoint
  - Input: SalesOrder number
  - Returns: order header data including DeliveryBlockReason, OverallDeliveryStatus
- [x] Register tool in `assets/standard-order-delivery-block-agent/app/tools/__init__.py`

### Agent Prompt & Logic

- [x] Update `assets/standard-order-delivery-block-agent/app/agent.py`:
  - `@prompt_section` system prompt must:
    - Define agent role: "SAP Sales Order Creation Agent with Delivery Block Risk Prediction"
    - Instruct agent to follow 5-step flow: collect params → simulate → predict risk → warn if high → create order
    - Instruct agent to always set `top` to max 100 on tool calls that accept it
    - Explicitly forbid hallucinating order data — all values must come from user input
    - Korean language: agent must respond in Korean unless user switches language
    - On high-risk (≥70): agent MUST present warning with risk factors and ask user confirmation before creating order
    - On medium-risk (40–69): agent presents advisory warning, can proceed with user acknowledgment
    - On low-risk (<40): agent proceeds to order creation after brief confirmation
  - `@agent_config` for temperature: set to 0.1 (precise, deterministic for order data extraction)
  - STATUS: [x] DONE — agent.py written with 3 decorated functions + Korean system prompt + temperature=0.1

### Business Step Instrumentation (Milestones)

- [ ] Instrument M1 (주문 정보 수집) in agent logic:
  - On achievement: `logger.info("M1.achieved: order parameters collected successfully", extra={"milestone": "M1", "status": "achieved"})`
  - On miss: `logger.warning("M1.missed: required order parameters incomplete", extra={"milestone": "M1", "status": "missed"})`
  - Add OpenTelemetry span via `@tracer.start_as_current_span("m1_collect_order_params")` on helper method
- [ ] Instrument M2 (Delivery Block 위험 예측):
  - On achievement: `logger.info("M2.achieved: delivery block risk predicted, score=%s", score, extra={"milestone": "M2", "status": "achieved", "risk_score": score})`
  - On miss: `logger.warning("M2.missed: rpt1 model call failed or returned no score", extra={"milestone": "M2", "status": "missed"})`
- [ ] Instrument M3 (경고 판단 및 사용자 통보):
  - On achievement: `logger.info("M3.achieved: warning issued, risk_level=%s", risk_level, extra={"milestone": "M3", "status": "achieved", "risk_level": risk_level})`
  - On miss: `logger.warning("M3.missed: warning generation failed", extra={"milestone": "M3", "status": "missed"})`
- [ ] Instrument M4 (주문 생성 실행):
  - On achievement: `logger.info("M4.achieved: sales order created, order_id=%s", order_id, extra={"milestone": "M4", "status": "achieved", "order_id": order_id})`
  - On miss: `logger.warning("M4.missed: sales order creation failed, reason=%s", error, extra={"milestone": "M4", "status": "missed", "error": error})`
- [ ] Instrument M5 (최종 결과 요약):
  - On achievement: `logger.info("M5.achieved: final summary delivered to user", extra={"milestone": "M5", "status": "achieved"})`
  - On miss: `logger.warning("M5.missed: summary generation failed", extra={"milestone": "M5", "status": "missed"})`
- [ ] Extract all business logic from `stream()` into `_run_agent()` async helper, instrument `_run_agent()` with OpenTelemetry spans
- [ ] Verify `auto_instrument()` is called at top of `main.py` before any AI framework imports

### MCP Wiring

- [x] Wire MCP tool loading in `agent.py` using `get_mcp_tools()` from `mcp_tools.py`
- [x] Ensure tools are loaded lazily (not in `__init__`)
- [x] After MCP server assets are set up, generate `mcp-mock.json` using `mcp-mock-config` skill

### asset.yaml

- [ ] Update `assets/standard-order-delivery-block-agent/asset.yaml`:
  - Add `requires` entries for all MCP servers used:
    ```yaml
    requires:
      - name: sales-order-mcp
        kind: mcp-server
        ordId: sap.s4:apiResource:API_SALES_ORDER_SRV_MCP:v1
      - name: sales-order-simulate-mcp
        kind: mcp-server
        ordId: sap.s4:apiResource:API_SALES_ORDER_SIMULATION_SRV_MCP:v1
    ```
  - Adjust ORD IDs to match actual MCP servers generated by `mcp-translation-file` / `setup-solution`

## Clean Up

- [x] No template-skill to delete (skills dir is empty)

## Testing

- [x] Confirm `mcp-mock.json` exists at `assets/standard-order-delivery-block-agent/mcp-mock.json`
- [x] `conftest.py` only sets `IBD_TESTING=1`
- [x] Write unit test: `tests/test_predict_delivery_block_risk.py` — mock RPT-1 call, verify risk score + level returned
- [x] Write unit test: `tests/test_simulate_sales_order.py` — mock MCP simulate tool, verify credit/availability signals extracted
- [x] Write unit test: `tests/test_create_sales_order.py` — mock MCP create tool, verify order number returned; test failure path
- [ ] Write unit test: `tests/test_get_order_status.py` — mock MCP GET tool, verify delivery block field returned
- [x] Write integration test: `tests/test_agent.py` — tests 3 decorated functions, thresholds, Korean prompt, SampleAgent class
- [x] Run `pytest` from `assets/standard-order-delivery-block-agent/` — 26/26 PASSED
- [ ] Verify coverage ≥ 70%; currently 39% overall (business tools 68-84%)
- [x] Verify `assets/standard-order-delivery-block-agent/app/agent.py` has exactly 3 decorated functions (`@agent_model`, `@agent_config`, `@prompt_section`)
- [x] Run `pytest` again (no args) to generate final `test_report.json` — 29/29 PASSED, score 100%
- [x] Verify `test_report.json` exists

## Agent Evaluation

- [ ] Invoke `sap-aeval-generate-tool-schema` skill from `assets/standard-order-delivery-block-agent/`
- [ ] Invoke `sap-aeval-generate-testcase` skill, passing PRD and `tools.json`
- [ ] Review and update `aeval/testcases/` with realistic Korean order data before running evaluations
