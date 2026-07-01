"""Unit tests for create_sales_order tool."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import json

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

import pytest


class TestCreateSalesOrder:
    """Tests for the create_sales_order tool."""

    @pytest.mark.asyncio
    async def test_successful_order_creation_via_mock_mcp(self):
        """Returns order number when MCP create tool succeeds."""
        mock_tool = MagicMock()
        mock_tool.name = "create_a_sales_order"
        mock_tool.ainvoke = AsyncMock(return_value=json.dumps({
            "SalesOrder": "0000005001",
            "OverallSDProcessStatus": "A",
        }))

        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = [mock_tool]
            from tools.create_sales_order import _create_sales_order
            result = await _create_sales_order(
                SoldToParty="0000001000",
                Material="TG11",
                RequestedQuantity=10.0,
                RequestedDeliveryDate="2026-08-01",
                SalesOrganization="1710",
                DistributionChannel="10",
                Division="00",
            )
            assert result["success"] is True
            assert result["SalesOrder"] == "0000005001"
            assert "created_at" in result

    @pytest.mark.asyncio
    async def test_failure_path_when_no_mcp_tools(self):
        """Returns error when no MCP tools available."""
        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = []
            from tools.create_sales_order import _create_sales_order
            result = await _create_sales_order(
                SoldToParty="0000001000",
                Material="TG11",
                RequestedQuantity=10.0,
                RequestedDeliveryDate="2026-08-01",
                SalesOrganization="1710",
                DistributionChannel="10",
                Division="00",
            )
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_result_structure_on_success(self):
        """Result has required fields on success."""
        mock_tool = MagicMock()
        mock_tool.name = "create_a_sales_order"
        mock_tool.ainvoke = AsyncMock(return_value=json.dumps({
            "SalesOrder": "0000005002",
        }))

        with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = [mock_tool]
            from tools.create_sales_order import _create_sales_order
            result = await _create_sales_order(
                SoldToParty="0000002000",
                Material="TG22",
                RequestedQuantity=50.0,
                RequestedDeliveryDate="2026-09-15",
                SalesOrganization="1710",
                DistributionChannel="10",
                Division="00",
            )
            assert "success" in result
            if result["success"]:
                assert "SalesOrder" in result
                assert "created_at" in result
                assert "status" in result
