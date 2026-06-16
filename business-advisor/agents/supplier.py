class SupplierAgent:
    """Demo external agent for supplier and sourcing feasibility."""

    def analyze(self, market_data, shipping_data):
        result = {}
        for product in market_data["products"]:
            complexity = product["supply_complexity"]
            if complexity == "low":
                score = 90
                notes = "Domestic suppliers and service partners are easy to start with."
                risks = []
            elif complexity == "medium":
                score = 75
                notes = "Supplier options exist, but pricing and fulfillment terms need validation."
                risks = ["supplier reliability"]
            else:
                score = 58
                notes = (
                    "Supply chain requires import planning, customs support, "
                    f"and typical lead time of {shipping_data['typical_lead_time_days']} days."
                )
                risks = ["inventory delay", "customs clearance"]

            result[product["name"]] = {"score": score, "notes": notes, "risks": risks}
        return result
