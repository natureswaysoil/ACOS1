"""
Basic tests for the Amazon Ads Automation.
Run locally with: pytest tests/ -v
"""

import pytest
from unittest.mock import MagicMock, patch
from functions.budget_optimizer import BudgetOptimizer


# ── Mock settings ────────────────────────────────────────────────────────────
def mock_settings(month=7):
    s = MagicMock()
    s.target_acos = 0.20
    s.acos_upper_warn = 0.30
    s.acos_lower_warn = 0.10
    s.max_budget_change_pct = 0.25
    s.seasonal_budgets = {
        1:35, 2:18, 3:65, 4:68, 5:68, 6:87,
        7:110, 8:88, 9:70, 10:45, 11:20, 12:19
    }
    # Patch current month
    import functions.budget_optimizer as bm
    bm.datetime = MagicMock()
    bm.datetime.now.return_value.month = month
    return s


def sample_campaign(acos=0.20, budget=65.0, sales=1000.0):
    return {
        "campaign_id":   "C001",
        "campaign_name": "Test Campaign",
        "status":        "ENABLED",
        "current_budget": budget,
        "spend_30d":     sales * acos,
        "sales_30d":     sales,
        "units_30d":     25,
        "acos_30d":      acos,
    }


# ── Budget Optimizer Tests ───────────────────────────────────────────────────

class TestBudgetOptimizer:

    def test_july_increases_budget(self):
        """July is peak — budget should go up from $65 baseline."""
        with patch("functions.budget_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value.month = 7
            settings = MagicMock()
            settings.target_acos = 0.20
            settings.max_budget_change_pct = 0.25
            settings.seasonal_budgets = {7: 110}
            optimizer = BudgetOptimizer(settings)
            campaign = sample_campaign(acos=0.20, budget=65.0, sales=1000.0)
            actions = optimizer.optimize([campaign])
            assert len(actions) == 1
            assert actions[0]["new_budget"] > 65.0, "July budget should increase"

    def test_february_decreases_budget(self):
        """February is slow — budget should go down from $65 baseline."""
        with patch("functions.budget_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value.month = 2
            settings = MagicMock()
            settings.target_acos = 0.20
            settings.max_budget_change_pct = 0.25
            settings.seasonal_budgets = {2: 18}
            optimizer = BudgetOptimizer(settings)
            campaign = sample_campaign(acos=0.20, budget=65.0, sales=1000.0)
            actions = optimizer.optimize([campaign])
            assert actions[0]["new_budget"] < 65.0, "Feb budget should decrease"

    def test_high_acos_reduces_budget(self):
        """If ACOS is very high (40%), budget should be pulled back."""
        with patch("functions.budget_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value.month = 6
            settings = MagicMock()
            settings.target_acos = 0.20
            settings.max_budget_change_pct = 0.25
            settings.seasonal_budgets = {6: 87}
            optimizer = BudgetOptimizer(settings)
            # Compare high ACOS vs normal ACOS
            campaign_normal = sample_campaign(acos=0.20, budget=65.0)
            campaign_high   = sample_campaign(acos=0.40, budget=65.0)
            actions_normal = optimizer.optimize([campaign_normal])
            actions_high   = optimizer.optimize([campaign_high])
            assert actions_high[0]["new_budget"] <= actions_normal[0]["new_budget"], \
                "High ACOS should result in lower or equal budget"

    def test_max_change_cap_respected(self):
        """Budget should never change more than 25% in one day."""
        with patch("functions.budget_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value.month = 7
            settings = MagicMock()
            settings.target_acos = 0.20
            settings.max_budget_change_pct = 0.25
            settings.seasonal_budgets = {7: 110}
            optimizer = BudgetOptimizer(settings)
            campaign = sample_campaign(acos=0.20, budget=65.0)
            actions = optimizer.optimize([campaign])
            old = actions[0]["old_budget"]
            new = actions[0]["new_budget"]
            change_pct = abs(new - old) / old
            assert change_pct <= 0.26, f"Change {change_pct:.1%} exceeds 25% cap"

    def test_disabled_campaigns_skipped(self):
        """Paused/disabled campaigns should not get budget changes."""
        with patch("functions.budget_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value.month = 7
            settings = MagicMock()
            settings.target_acos = 0.20
            settings.max_budget_change_pct = 0.25
            settings.seasonal_budgets = {7: 110}
            optimizer = BudgetOptimizer(settings)
            campaign = sample_campaign()
            campaign["status"] = "PAUSED"
            actions = optimizer.optimize([campaign])
            assert actions == [], "Disabled campaigns should be skipped"

    def test_no_campaigns_returns_empty(self):
        """Empty campaign list should return empty actions."""
        with patch("functions.budget_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value.month = 7
            settings = MagicMock()
            settings.seasonal_budgets = {7: 110}
            settings.target_acos = 0.20
            settings.max_budget_change_pct = 0.25
            optimizer = BudgetOptimizer(settings)
            assert optimizer.optimize([]) == []
