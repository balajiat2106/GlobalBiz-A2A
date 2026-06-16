class FinanceAgent:
    """Demo external agent for financial feasibility."""

    def handle_task(self, task):
        if task["capability"] != "finance.feasibility":
            raise ValueError(f"FinanceAgent cannot handle capability: {task['capability']}")

        payload = task["payload"]
        return self.analyze(payload["market_data"], payload["budget_usd"])

    def analyze(self, market_data, budget_usd):
        result = {}
        for product in market_data["products"]:
            estimated_cost = product["base_startup_cost"]
            remaining_budget = budget_usd - estimated_cost

            if remaining_budget >= 10000:
                notes = f"Feasible with about USD {remaining_budget:,} left for marketing and buffer."
            elif remaining_budget >= 0:
                notes = f"Feasible, but only USD {remaining_budget:,} remains after initial setup."
            else:
                notes = f"Not ideal; exceeds budget by about USD {abs(remaining_budget):,}."

            result[product["name"]] = {
                "estimated_startup_cost": estimated_cost,
                "notes": notes,
            }
        return result
