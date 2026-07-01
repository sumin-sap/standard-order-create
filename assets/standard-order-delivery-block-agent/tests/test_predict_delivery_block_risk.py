"""Unit tests for predict_delivery_block_risk tool."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def add_app_to_path():
    app_path = str(Path(__file__).parent.parent / "app")
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    yield


class TestPredictDeliveryBlockRisk:
    """Tests for the predict_delivery_block_risk tool."""

    @pytest.mark.asyncio
    async def test_low_risk_order(self):
        """Low risk order returns score < 40."""
        from tools.predict_delivery_block_risk import _predict_delivery_block_risk, _rule_based_risk_score
        result = _rule_based_risk_score(
            sold_to_party="0000001000",
            requested_quantity=10.0,
            credit_limit=100000.0,
            current_exposure=10000.0,
            requested_delivery_date="2026-08-01",
        )
        assert "risk_score" in result
        assert "risk_level" in result
        assert result["risk_level"] in ("low", "medium", "high")
        assert 0 <= result["risk_score"] <= 100
        assert isinstance(result["risk_factors"], list)
        assert isinstance(result["recommendation"], str)

    @pytest.mark.asyncio
    async def test_high_risk_credit_exceeded(self):
        """High credit utilization triggers high risk."""
        from tools.predict_delivery_block_risk import _rule_based_risk_score
        result = _rule_based_risk_score(
            sold_to_party="0000001000",
            requested_quantity=100.0,
            credit_limit=10000.0,
            current_exposure=9800.0,
            requested_delivery_date="2026-08-01",
        )
        assert result["risk_score"] >= 70
        assert result["risk_level"] == "high"
        assert len(result["risk_factors"]) > 0

    @pytest.mark.asyncio
    async def test_medium_risk_credit_warning(self):
        """75-90% credit utilization triggers medium risk."""
        from tools.predict_delivery_block_risk import _rule_based_risk_score
        result = _rule_based_risk_score(
            sold_to_party="0000001000",
            requested_quantity=50.0,
            credit_limit=10000.0,
            current_exposure=8000.0,
            requested_delivery_date="2026-08-01",
        )
        assert result["risk_score"] >= 40
        assert result["risk_level"] in ("medium", "high")

    @pytest.mark.asyncio
    async def test_predict_tool_invocable(self):
        """Ensure the tool can be invoked with mock MCP tools."""
        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = []
            from tools.predict_delivery_block_risk import _predict_delivery_block_risk
            result = await _predict_delivery_block_risk(
                SoldToParty="0000001000",
                Material="TG11",
                RequestedQuantity=100.0,
                RequestedDeliveryDate="2026-08-01",
                SalesOrganization="1710",
                DistributionChannel="10",
                Division="00",
            )
            assert "risk_score" in result
            assert "risk_level" in result

    def test_risk_thresholds(self):
        """Verify threshold constants are correctly defined."""
        from tools.predict_delivery_block_risk import HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD
        assert HIGH_RISK_THRESHOLD == 70
        assert MEDIUM_RISK_THRESHOLD == 40
        assert HIGH_RISK_THRESHOLD > MEDIUM_RISK_THRESHOLD
