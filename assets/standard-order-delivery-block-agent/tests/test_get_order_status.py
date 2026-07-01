"""Unit tests for get_order_status tool."""
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

import pytest


class TestGetOrderStatus:
    """Tests for the get_order_status tool."""

    @pytest.mark.asyncio
    async def test_returns_delivery_block_reason(self):
        """Returns DeliveryBlockReason from MCP tool response."""
        mock_tool = MagicMock()
        mock_tool.name = "get_a_sales_order"
        mock_tool.ainvoke = AsyncMock(return_value=json.dumps({
            "d": {
                "SalesOrder": "0000005001",
                "DeliveryBlockReason": "01",
                "OverallDeliveryStatus": "A",
                "OverallSDProcessStatus": "C",
            }
        }))

        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = [mock_tool]
            from tools.get_order_status import _get_order_status
            result = await _get_order_status(SalesOrder="0000005001")
            assert "DeliveryBlockReason" in result
            assert result["SalesOrder"] == "0000005001"
            assert "OverallDeliveryStatus" in result

    @pytest.mark.asyncio
    async def test_fallback_when_no_mcp_tools(self):
        """Returns error dict when no MCP tools available."""
        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = []
            from tools.get_order_status import _get_order_status
            result = await _get_order_status(SalesOrder="0000005001")
            assert "SalesOrder" in result
            assert result["SalesOrder"] == "0000005001"
            # Should return some status even if tool not found
            assert "DeliveryBlockReason" in result

    @pytest.mark.asyncio
    async def test_result_contains_required_fields(self):
        """Result always contains SalesOrder and status fields."""
        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = []
            from tools.get_order_status import _get_order_status
            result = await _get_order_status(SalesOrder="0000001234")
            assert "SalesOrder" in result
            assert result["SalesOrder"] == "0000001234"
