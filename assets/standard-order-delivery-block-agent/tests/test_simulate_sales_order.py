"""Unit tests for simulate_sales_order tool."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

import pytest


class TestSimulateSalesOrder:
    """Tests for the simulate_sales_order tool."""

    @pytest.mark.asyncio
    async def test_fallback_when_no_mcp_tools(self):
        """Returns fallback result when MCP tools are not available."""
        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = []
            from tools.simulate_sales_order import _simulate_sales_order
            result = await _simulate_sales_order(
                SoldToParty="0000001000",
                Material="TG11",
                RequestedQuantity=10.0,
                RequestedDeliveryDate="2026-08-01",
                SalesOrganization="1710",
                DistributionChannel="10",
                Division="00",
            )
            assert "is_valid" in result
            assert "messages" in result
            assert "credit_check_passed" in result
            assert "availability_ok" in result

    @pytest.mark.asyncio
    async def test_fallback_returns_valid_result(self):
        """Fallback result is valid."""
        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = []
            from tools.simulate_sales_order import _simulate_sales_order
            result = await _simulate_sales_order(
                SoldToParty="0000002000",
                Material="TG22",
                RequestedQuantity=500.0,
                RequestedDeliveryDate="2026-09-01",
                SalesOrganization="1710",
                DistributionChannel="10",
                Division="00",
            )
            assert result["is_valid"] is True
            assert isinstance(result["messages"], list)

    @pytest.mark.asyncio
    async def test_simulate_extracts_credit_check(self):
        """Result includes credit check result."""
        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = []
            from tools.simulate_sales_order import _simulate_sales_order
            result = await _simulate_sales_order(
                SoldToParty="0000001000",
                Material="TG11",
                RequestedQuantity=10.0,
                RequestedDeliveryDate="2026-08-01",
                SalesOrganization="1710",
                DistributionChannel="10",
                Division="00",
            )
            assert "credit_check_passed" in result
            assert isinstance(result["credit_check_passed"], bool)
            assert "availability_ok" in result
