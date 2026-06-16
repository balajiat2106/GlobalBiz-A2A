from agents.compliance import ComplianceAgent
from agents.finance import FinanceAgent
from agents.supplier import SupplierAgent
from tools.country_tool import CountryTool
from tools.market_tool import MarketTool
from tools.shipping_tool import ShippingTool


class BusinessAdvisorAgent:
    """Main agent that coordinates MCP-style tools and external agents."""

    def __init__(self):
        self.market_tool = MarketTool()
        self.country_tool = CountryTool()
        self.shipping_tool = ShippingTool()
        self.supplier_agent = SupplierAgent()
        self.finance_agent = FinanceAgent()
        self.compliance_agent = ComplianceAgent()

    def recommend(self, request):
        country = request["country"]
        budget_usd = request["budget_usd"]

        trace = [
            "Business Advisor Agent received the user request.",
            "Business Advisor Agent called MarketTool for product demand data.",
            "Business Advisor Agent called CountryTool for country setup data.",
            "Business Advisor Agent called ShippingTool for logistics data.",
        ]

        market_data = self.market_tool.get_market_options(country)
        country_data = self.country_tool.get_country_profile(country)
        shipping_data = self.shipping_tool.get_shipping_profile(country)

        trace.extend(
            [
                "Business Advisor Agent contacted SupplierAgent for sourcing feasibility.",
                "Business Advisor Agent contacted FinanceAgent for budget feasibility.",
                "Business Advisor Agent contacted ComplianceAgent for regulatory feasibility.",
            ]
        )

        supplier_result = self.supplier_agent.analyze(market_data, shipping_data)
        finance_result = self.finance_agent.analyze(market_data, budget_usd)
        compliance_result = self.compliance_agent.analyze(market_data, country_data)

        recommendations = []
        for product in market_data["products"]:
            name = product["name"]
            estimated_cost = finance_result[name]["estimated_startup_cost"]
            score = self._score_option(
                product=product,
                estimated_cost=estimated_cost,
                budget_usd=budget_usd,
                supplier_score=supplier_result[name]["score"],
                compliance_score=compliance_result[name]["score"],
            )

            recommendations.append(
                {
                    "name": name,
                    "summary": product["summary"],
                    "score": score,
                    "estimated_startup_cost": estimated_cost,
                    "profit_potential": product["profit_potential"],
                    "supplier_notes": supplier_result[name]["notes"],
                    "finance_notes": finance_result[name]["notes"],
                    "compliance_notes": compliance_result[name]["notes"],
                    "risks": sorted(
                        set(
                            product["risks"]
                            + supplier_result[name]["risks"]
                            + compliance_result[name]["risks"]
                        )
                    ),
                }
            )

        recommendations.sort(key=lambda option: option["score"], reverse=True)

        trace.append("Business Advisor Agent ranked all options and generated the final plan.")

        return {
            "country": country,
            "budget_usd": budget_usd,
            "trace": trace,
            "recommendations": recommendations,
            "next_step": (
                f"Validate '{recommendations[0]['name']}' with 10 customer interviews, "
                "3 supplier quotes, and a state-specific compliance checklist."
            ),
        }

    def _score_option(self, product, estimated_cost, budget_usd, supplier_score, compliance_score):
        budget_score = 100 if estimated_cost <= budget_usd else max(30, int((budget_usd / estimated_cost) * 100))
        demand_score = product["demand_score"]
        profit_score = product["profit_score"]

        total = (
            budget_score * 0.25
            + demand_score * 0.25
            + profit_score * 0.20
            + supplier_score * 0.15
            + compliance_score * 0.15
        )
        return round(total)
