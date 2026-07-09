import unittest

from agents.advisor import BusinessAdvisorAgent
from agents.planner import AdvisorPlanner
from agents.registry import AgentRegistry


class StaticPlanner:
    def __init__(self, plan):
        self.static_plan = plan

    def plan(self, query):
        return {**self.static_plan, "raw_query": query}


def normalized_plan(**overrides):
    registry = AgentRegistry()
    planner = AdvisorPlanner(registry)
    plan = {
        "raw_query": "test query",
        "action": "execute",
        "clarification_question": "",
        "country": "USA",
        "budget_usd": 50000,
        "focus": "market_research",
        "identified_tools": [],
        "selected_tools": ["market_tool"],
        "identified_agent_capabilities": [],
        "selected_agent_capabilities": [],
        "planner": "test",
        "planner_notes": "test plan",
    }
    plan.update(overrides)
    return planner._normalize_plan(plan)


def advisor_with_plan(plan):
    advisor = BusinessAdvisorAgent()
    advisor.planner = StaticPlanner(plan)
    return advisor


class PlannerNormalizationTests(unittest.TestCase):
    def test_missing_budget_becomes_clarification(self):
        plan = normalized_plan(country="UK", budget_usd=0, selected_tools=["market_tool"])

        self.assertEqual(plan["action"], "ask_clarification")
        self.assertIn("budget", plan["clarification_question"])
        self.assertEqual(plan["selected_tools"], [])
        self.assertEqual(plan["selected_agent_capabilities"], [])
        self.assertEqual(plan["execution_plan"], [])

    def test_missing_country_becomes_clarification(self):
        plan = normalized_plan(country="", budget_usd=10000, selected_tools=["market_tool"])

        self.assertEqual(plan["action"], "ask_clarification")
        self.assertIn("target country", plan["clarification_question"])
        self.assertEqual(plan["execution_plan"], [])

    def test_compliance_capability_adds_required_tools(self):
        plan = normalized_plan(
            country="United Kingdom",
            selected_tools=[],
            selected_agent_capabilities=["compliance.review"],
            focus="compliance",
        )

        self.assertEqual(plan["country"], "UK")
        self.assertIn("market_tool", plan["selected_tools"])
        self.assertIn("country_tool", plan["selected_tools"])
        self.assertNotIn("shipping_tool", plan["selected_tools"])
        self.assertIn("compliance.review", plan["execution_plan"])

    def test_supplier_capability_adds_shipping_tool(self):
        plan = normalized_plan(
            selected_tools=["not_a_real_tool"],
            selected_agent_capabilities=["supplier.analysis", "not.a.real.capability"],
            focus="supplier",
        )

        self.assertEqual(plan["selected_agent_capabilities"], ["supplier.analysis"])
        self.assertIn("market_tool", plan["selected_tools"])
        self.assertIn("shipping_tool", plan["selected_tools"])
        self.assertNotIn("not_a_real_tool", plan["selected_tools"])


class AdvisorRecommendationTests(unittest.TestCase):
    def test_unsupported_country_returns_friendly_message_without_execution(self):
        plan = normalized_plan(country="Germany", budget_usd=50000)
        report = advisor_with_plan(plan).recommend("I want to do a business in Germany with USD 50000")

        self.assertEqual(report["action"], "unsupported_country")
        self.assertEqual(report["country"], "GERMANY")
        self.assertIn("supported countries", report["message"])
        self.assertIn("USA", report["supported_countries"])
        self.assertNotIn("recommendations", report)

    def test_market_only_query_does_not_call_external_agents(self):
        plan = normalized_plan(
            country="Singapore",
            budget_usd=25000,
            focus="market_research",
            selected_tools=["market_tool"],
            selected_agent_capabilities=[],
        )
        report = advisor_with_plan(plan).recommend("I want market research only for Singapore with USD 25000")

        self.assertEqual(report["action"], "execute")
        self.assertEqual(report["a2a_events"], [])
        self.assertEqual(report["selected_agent_capabilities"], [])
        self.assertTrue(report["recommendations"])
        self.assertTrue(all(option["estimated_startup_cost"] <= 25000 for option in report["recommendations"]))

    def test_budget_filter_returns_only_feasible_options_when_available(self):
        plan = normalized_plan(country="UK", budget_usd=10000, selected_tools=["market_tool"])
        report = advisor_with_plan(plan).recommend("I want to do a business in UK with budget 10000")

        self.assertEqual(report["action"], "execute")
        self.assertTrue(report["recommendations"])
        self.assertTrue(all(option["budget_feasible"] for option in report["recommendations"]))
        self.assertTrue(all(option["estimated_startup_cost"] <= 10000 for option in report["recommendations"]))
        self.assertIn("within the USD 10,000 budget", report["budget_summary"])

    def test_budget_filter_returns_closest_option_when_none_fit(self):
        plan = normalized_plan(country="UAE", budget_usd=10000, selected_tools=["market_tool"])
        report = advisor_with_plan(plan).recommend("I want to do a business in UAE with budget 10000")

        self.assertEqual(report["action"], "execute")
        self.assertEqual(len(report["recommendations"]), 1)
        self.assertFalse(report["recommendations"][0]["budget_feasible"])
        self.assertEqual(report["recommendations"][0]["budget_gap"], 4000)
        self.assertIn("closest option", report["budget_summary"])

    def test_finance_capability_produces_a2a_trace(self):
        plan = normalized_plan(
            country="UK",
            budget_usd=10000,
            focus="finance",
            selected_tools=["market_tool"],
            selected_agent_capabilities=["finance.feasibility"],
        )
        report = advisor_with_plan(plan).recommend(
            "I have USD 10000. Check only whether business ideas are financially feasible in UK."
        )

        self.assertEqual(report["action"], "execute")
        self.assertEqual(report["selected_agent_capabilities"], ["finance.feasibility"])
        self.assertEqual(len(report["a2a_events"]), 1)
        self.assertEqual(report["a2a_events"][0]["capability"], "finance.feasibility")
        self.assertIn("budget_usd", report["a2a_events"][0]["payload_keys"])
        self.assertTrue(report["recommendations"][0]["finance_notes"])


if __name__ == "__main__":
    unittest.main()
