"""
Budget Optimizer
Calculates the ideal daily budget for each campaign based on:
  - Current month's seasonal target
  - Each campaign's individual ACOS performance
  - A max change cap (default 25%) to avoid jarring swings
"""

from datetime import datetime
from typing import List, Dict


class BudgetOptimizer:

    def __init__(self, settings):
        self.settings = settings
        self.current_month = datetime.now().month
        self.target_daily  = settings.seasonal_budgets[self.current_month]
        self.target_acos   = settings.target_acos
        self.max_change    = settings.max_budget_change_pct

    def optimize(self, campaigns: List[Dict]) -> List[Dict]:
        """
        For each campaign, decide whether to raise, lower, or hold its budget.
        Returns a list of action dicts.
        """
        actions = []

        # Filter to only active campaigns
        active = [c for c in campaigns if c["status"] == "ENABLED"]
        if not active:
            return actions

        # Distribute the monthly target budget proportionally
        # across campaigns based on their trailing sales contribution
        total_sales = sum(c["sales_30d"] for c in active) or 1
        for campaign in active:
            share = campaign["sales_30d"] / total_sales
            ideal_budget = round(self.target_daily * share, 2)
            ideal_budget = max(ideal_budget, 1.00)  # Amazon minimum is $1/day

            action = self._build_action(campaign, ideal_budget)
            actions.append(action)

        return actions

    def _build_action(self, campaign: Dict, ideal_budget: float) -> Dict:
        """Determine whether and how much to change a campaign's budget."""
        current = campaign["current_budget"]
        acos    = campaign["acos_30d"]

        # Apply ACOS performance modifier
        # If ACOS is high → be more conservative with budget
        # If ACOS is very low → we can be more aggressive
        if acos is not None:
            if acos > self.target_acos * 1.5:       # ACOS >30% — pull back 10%
                ideal_budget *= 0.90
            elif acos > self.target_acos * 1.2:     # ACOS >24% — pull back 5%
                ideal_budget *= 0.95
            elif acos < self.target_acos * 0.5:     # ACOS <10% — push 10% more
                ideal_budget *= 1.10

        ideal_budget = round(ideal_budget, 2)

        # Cap the change at max_change % to avoid large swings
        if current > 0:
            max_up   = round(current * (1 + self.max_change), 2)
            max_down = round(current * (1 - self.max_change), 2)
            new_budget = max(max_down, min(max_up, ideal_budget))
        else:
            new_budget = ideal_budget

        new_budget = round(new_budget, 2)
        delta      = new_budget - current

        return {
            "campaign_id":   campaign["campaign_id"],
            "campaign_name": campaign["campaign_name"],
            "old_budget":    current,
            "ideal_budget":  ideal_budget,
            "new_budget":    new_budget,
            "delta":         round(delta, 2),
            "direction":     "increase" if delta > 0.50 else ("decrease" if delta < -0.50 else "hold"),
            "should_update": abs(delta) >= 0.50,   # only update if change is ≥ $0.50
            "reason":        self._reason(campaign, delta, acos),
            "month_target":  self.target_daily,
            "current_month": self.current_month,
        }

    def _reason(self, campaign: Dict, delta: float, acos) -> str:
        month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                       7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
        mo = month_names[self.current_month]
        acos_str = f"{acos*100:.1f}%" if acos else "N/A"

        if delta > 0:
            return f"{mo} is a peak month (target ${self.target_daily}/day). ACOS {acos_str} — increasing budget."
        elif delta < 0:
            return f"{mo} is a slow month (target ${self.target_daily}/day). ACOS {acos_str} — reducing budget."
        else:
            return f"Budget optimal for {mo}. ACOS {acos_str} — holding."
