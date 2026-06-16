class ComplianceAgent:
    """Demo external agent for regulation and compliance feasibility."""

    def handle_task(self, task):
        if task["capability"] != "compliance.review":
            raise ValueError(f"ComplianceAgent cannot handle capability: {task['capability']}")

        payload = task["payload"]
        return self.analyze(payload["market_data"], payload["country_data"])

    def analyze(self, market_data, country_data):
        result = {}
        for product in market_data["products"]:
            level = product["compliance_level"]
            if level == "low":
                score = 88
                notes = f"Basic {country_data['entity_type']} setup, local registration, and tax tracking."
                risks = ["state registration differences"]
            elif level == "medium":
                score = 72
                notes = "Requires sales tax review, contracts, insurance, and category-specific checks."
                risks = ["sales tax complexity", "insurance requirements"]
            else:
                score = 52
                notes = "Requires FDA/import review, labeling checks, customs documentation, and tax setup."
                risks = ["import compliance", "labeling requirements", "customs documentation"]

            result[product["name"]] = {"score": score, "notes": notes, "risks": risks}
        return result
