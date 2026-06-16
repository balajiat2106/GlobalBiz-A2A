from agents.registry import A2AClient, AgentRegistry
from tools.country_tool import CountryTool
from tools.market_tool import MarketTool
from tools.shipping_tool import ShippingTool


class BusinessAdvisorAgent:
    """Main agent that coordinates MCP-style tools and external agents."""

    def __init__(self):
        self.market_tool = MarketTool()
        self.country_tool = CountryTool()
        self.shipping_tool = ShippingTool()
        self.registry = AgentRegistry()
        self.a2a_client = A2AClient()

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

        supplier_result = self._call_external_agent(
            capability="supplier.analysis",
            payload={"market_data": market_data, "shipping_data": shipping_data},
            trace=trace,
        )
        finance_result = self._call_external_agent(
            capability="finance.feasibility",
            payload={"market_data": market_data, "budget_usd": budget_usd},
            trace=trace,
        )
        compliance_result = self._call_external_agent(
            capability="compliance.review",
            payload={"market_data": market_data, "country_data": country_data},
            trace=trace,
        )

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
            "capability_registry": self.registry.list_capabilities(),
            "trace": trace,
            "recommendations": recommendations,
            "next_step": (
                f"Validate '{recommendations[0]['name']}' with 10 customer interviews, "
                "3 supplier quotes, and a state-specific compliance checklist."
            ),
        }

    def _call_external_agent(self, capability, payload, trace):
        agent_card = self.registry.discover(capability)
        trace.append(
            f"Discovered {agent_card['name']} for capability '{capability}' "
            f"at {agent_card['endpoint']}."
        )
        trace.append(f"Sent A2A task envelope to {agent_card['name']}.")
        return self.a2a_client.send_task(agent_card, capability, payload)

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
