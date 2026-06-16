from agents.planner import AdvisorPlanner
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
        self.planner = AdvisorPlanner(self.registry)

    def recommend(self, query):
        plan = self.planner.plan(query)
        if plan["action"] == "ask_clarification":
            return {
                "action": "ask_clarification",
                "raw_query": plan["raw_query"],
                "planner": plan["planner"],
                "planner_notes": plan["planner_notes"],
                "clarification_question": plan["clarification_question"],
            }

        if plan["action"] == "out_of_scope":
            if "illegal business" in plan["planner_notes"].lower():
                message = (
                    "I cannot help with illegal business activities. I can only assist with lawful "
                    "business launch advisory questions such as market research, finance feasibility, "
                    "compliance, suppliers, and launch strategy."
                )
            else:
                message = (
                    "I cannot answer that because I am built for business launch advisory questions, "
                    "such as market research, finance feasibility, compliance, suppliers, and launch strategy."
                )

            return {
                "action": "out_of_scope",
                "raw_query": plan["raw_query"],
                "planner": plan["planner"],
                "planner_notes": plan["planner_notes"],
                "message": message,
            }

        if plan["action"] == "planner_error":
            return {
                "action": "planner_error",
                "raw_query": plan["raw_query"],
                "planner": plan["planner"],
                "planner_notes": plan["planner_notes"],
                "identified_tools": plan["identified_tools"],
                "identified_agent_capabilities": plan["identified_agent_capabilities"],
                "message": (
                    "I could not create an LLM-based execution plan. Please check the OpenAI API key, "
                    "quota, and network connection, then try again."
                ),
            }

        country = plan["country"]
        budget_usd = plan["budget_usd"]
        focus = plan["focus"]
        execution_plan = plan["execution_plan"]

        supported_countries = self.market_tool.available_countries()
        if country not in supported_countries:
            return {
                "action": "unsupported_country",
                "raw_query": plan["raw_query"],
                "country": country,
                "planner": plan["planner"],
                "planner_notes": plan["planner_notes"],
                "supported_countries": supported_countries,
                "message": (
                    f"I do not have country-specific demo knowledge for {country or 'that country'} yet. "
                    "Please choose one of the supported countries for this demo: "
                    f"{', '.join(supported_countries)}."
                ),
            }

        trace = [
            "Business Advisor Agent received the user request.",
            f"Planner mode: {plan['planner']}.",
            f"Planner decision: {plan['planner_notes']}",
            f"Business Advisor Agent selected focus: {focus}.",
            f"Business Advisor Agent created execution plan: {', '.join(execution_plan)}.",
        ]
        a2a_events = []

        market_data = None
        country_data = None
        shipping_data = None
        supplier_result = {}
        finance_result = {}
        compliance_result = {}

        if "market_tool" in execution_plan:
            trace.append("Business Advisor Agent called MarketTool for product demand data.")
            market_data = self.market_tool.get_market_options(country)

        if "country_tool" in execution_plan:
            trace.append("Business Advisor Agent called CountryTool for country setup data.")
            country_data = self.country_tool.get_country_profile(country)

        if "shipping_tool" in execution_plan:
            trace.append("Business Advisor Agent called ShippingTool for logistics data.")
            shipping_data = self.shipping_tool.get_shipping_profile(country)

        if "supplier.analysis" in execution_plan:
            supplier_result = self._call_external_agent(
                capability="supplier.analysis",
                payload={"market_data": market_data, "shipping_data": shipping_data},
                trace=trace,
                a2a_events=a2a_events,
            )

        if "finance.feasibility" in execution_plan:
            finance_result = self._call_external_agent(
                capability="finance.feasibility",
                payload={"market_data": market_data, "budget_usd": budget_usd},
                trace=trace,
                a2a_events=a2a_events,
            )

        if "compliance.review" in execution_plan:
            compliance_result = self._call_external_agent(
                capability="compliance.review",
                payload={"market_data": market_data, "country_data": country_data},
                trace=trace,
                a2a_events=a2a_events,
            )

        recommendations = []
        for product in market_data["products"]:
            name = product["name"]
            estimated_cost = finance_result.get(name, {}).get("estimated_startup_cost", product["base_startup_cost"])
            score = self._score_option(
                product=product,
                estimated_cost=estimated_cost,
                budget_usd=budget_usd,
                supplier_score=supplier_result.get(name, {}).get("score"),
                compliance_score=compliance_result.get(name, {}).get("score"),
            )

            recommendations.append(
                {
                    "name": name,
                    "summary": product["summary"],
                    "score": score,
                    "estimated_startup_cost": estimated_cost,
                    "budget_feasible": estimated_cost <= budget_usd,
                    "budget_gap": max(0, estimated_cost - budget_usd),
                    "profit_potential": product["profit_potential"],
                    "market_notes": self._market_notes(product),
                    "supplier_notes": supplier_result.get(name, {}).get("notes"),
                    "finance_notes": finance_result.get(name, {}).get("notes"),
                    "compliance_notes": compliance_result.get(name, {}).get("notes"),
                    "risks": sorted(
                        set(
                            product["risks"]
                            + supplier_result.get(name, {}).get("risks", [])
                            + compliance_result.get(name, {}).get("risks", [])
                        )
                    ),
                }
            )

        recommendations = self._filter_by_budget(recommendations, budget_usd, trace)

        trace.append("Business Advisor Agent ranked all options and generated the final plan.")

        return {
            "action": "execute",
            "country": country,
            "budget_usd": budget_usd,
            "raw_query": plan["raw_query"],
            "focus": focus,
            "planner": plan["planner"],
            "planner_notes": plan["planner_notes"],
            "identified_tools": plan["identified_tools"],
            "selected_tools": plan["selected_tools"],
            "identified_agent_capabilities": plan["identified_agent_capabilities"],
            "selected_agent_capabilities": plan["selected_agent_capabilities"],
            "execution_plan": execution_plan,
            "capability_registry": self.registry.list_capabilities(),
            "a2a_events": a2a_events,
            "trace": trace,
            "recommendations": recommendations,
            "budget_summary": self._budget_summary(recommendations, budget_usd),
            "next_step": self._next_step(focus, recommendations[0]["name"], recommendations[0]),
        }

    def _call_external_agent(self, capability, payload, trace, a2a_events):
        agent_card = self.registry.discover(capability)
        trace.append(
            f"Discovered {agent_card['name']} for capability '{capability}' "
            f"at {agent_card['endpoint']}."
        )
        trace.append(f"Sent A2A task envelope to {agent_card['name']}.")
        response = self.a2a_client.send_task(agent_card, capability, payload)
        a2a_events.append(
            {
                "capability": capability,
                "agent_id": agent_card["id"],
                "agent_name": agent_card["name"],
                "endpoint": agent_card["endpoint"],
                "version": agent_card["version"],
                "payload_keys": sorted(payload.keys()),
                "response_items": len(response),
            }
        )
        return response

    def _score_option(self, product, estimated_cost, budget_usd, supplier_score, compliance_score):
        budget_score = 100 if estimated_cost <= budget_usd else max(30, int((budget_usd / estimated_cost) * 100))
        demand_score = product["demand_score"]
        profit_score = product["profit_score"]
        supplier_score = supplier_score if supplier_score is not None else 70
        compliance_score = compliance_score if compliance_score is not None else 70

        total = (
            budget_score * 0.25
            + demand_score * 0.25
            + profit_score * 0.20
            + supplier_score * 0.15
            + compliance_score * 0.15
        )
        return round(total)

    def _filter_by_budget(self, recommendations, budget_usd, trace):
        feasible = [option for option in recommendations if option["budget_feasible"]]
        over_budget = [option for option in recommendations if not option["budget_feasible"]]

        feasible.sort(key=lambda option: option["score"], reverse=True)
        over_budget.sort(key=lambda option: (option["budget_gap"], -option["score"]))

        if feasible:
            trace.append(
                f"Business Advisor Agent filtered out {len(over_budget)} over-budget option(s) "
                "from primary recommendations."
            )
            return [self._with_budget_status(option) for option in feasible]

        closest = over_budget[:1]
        trace.append(
            "Business Advisor Agent found no fully budget-feasible options and returned only "
            "the closest option with a clear budget gap."
        )
        return [self._with_budget_status(option) for option in closest]

    def _with_budget_status(self, option):
        if option["budget_feasible"]:
            option["budget_status"] = "Feasible within budget"
        else:
            option["budget_status"] = f"Over budget by USD {option['budget_gap']:,}"
        return option

    def _budget_summary(self, recommendations, budget_usd):
        if recommendations[0]["budget_feasible"]:
            return f"Showing only options within the USD {budget_usd:,} budget."
        return (
            f"No option is fully feasible within USD {budget_usd:,}. "
            f"Showing the closest option only: gap USD {recommendations[0]['budget_gap']:,}."
        )

    def _market_notes(self, product):
        return (
            f"Demand score {product['demand_score']}/100 and profit score "
            f"{product['profit_score']}/100 for this demo dataset."
        )

    def _next_step(self, focus, top_option, option):
        if not option["budget_feasible"]:
            return (
                f"Either increase the budget by about USD {option['budget_gap']:,}, "
                f"or reduce the launch scope for '{top_option}' before proceeding."
            )
        if focus == "market_research":
            return f"Validate demand for '{top_option}' with 10 customer interviews and competitor price checks."
        if focus == "finance":
            return f"Build a simple cash-flow model for '{top_option}' with startup cost and 6-month runway assumptions."
        if focus == "compliance":
            return f"Create a country-specific compliance checklist for '{top_option}' before spending on launch."
        if focus == "supplier":
            return f"Collect 3 supplier quotes and delivery timelines for '{top_option}'."
        return (
            f"Validate '{top_option}' with 10 customer interviews, "
            "3 supplier quotes, and a country-specific compliance checklist."
        )
