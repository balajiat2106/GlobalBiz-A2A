import json
import os
import re
import ssl
import urllib.error
import urllib.request

from config import load_env


class AdvisorPlanner:
    """Plans tool and agent calls from natural language."""

    def __init__(self, registry):
        load_env()
        self.registry = registry

    def plan(self, query):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "replace_with_your_openai_api_key":
            try:
                return self._plan_with_llm(query)
            except (OSError, ValueError, KeyError, urllib.error.URLError) as error:
                fallback = self._fallback_plan(query)
                fallback["planner_notes"] = f"LLM planner failed; used fallback parser. Error: {error}"
                return fallback

        fallback = self._fallback_plan(query)
        fallback["planner_notes"] = "OPENAI_API_KEY missing or placeholder in .env; used local fallback parser."
        return fallback

    def _plan_with_llm(self, query):
        available_tools = [
            {
                "name": "market_tool",
                "description": "Returns product demand, profit potential, startup cost, and market risks.",
            },
            {
                "name": "country_tool",
                "description": "Returns country business setup, tax, and registration assumptions.",
            },
            {
                "name": "shipping_tool",
                "description": "Returns logistics, import, and shipping assumptions.",
            },
        ]
        available_capabilities = self.registry.list_capabilities()

        prompt = {
            "role": "user",
            "content": (
                "You are the planning brain for a Business Advisor Agent. "
                "Read the user query and decide whether you have enough information to execute. "
                "If the user does not provide a target country or budget, ask one concise clarification question "
                "and do not choose tools or external agents yet. "
                "If enough information is available, choose only the tools and external agent capabilities needed. "
                "Return strict JSON with keys: action, clarification_question, country, budget_usd, focus, "
                "execution_plan, reasoning. "
                "Valid action values are ask_clarification and execute. "
                "Valid execution_plan items are market_tool, country_tool, shipping_tool, "
                "supplier.analysis, finance.feasibility, compliance.review. "
                "Use market_tool whenever recommendations or product options are needed. "
                "Use country_tool only for compliance/legal/setup/tax questions. "
                "Use shipping_tool only for supplier/import/export/logistics questions. "
                "Use external capabilities only when their expertise is needed. "
                f"Available MCP tools: {json.dumps(available_tools)}. "
                f"Available external capabilities: {json.dumps(available_capabilities)}. "
                f"User query: {query}"
            ),
        }

        body = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            "input": [prompt],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "advisor_plan",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "action": {"type": "string", "enum": ["ask_clarification", "execute"]},
                            "clarification_question": {"type": "string"},
                            "country": {"type": "string"},
                            "budget_usd": {"type": "integer"},
                            "focus": {
                                "type": "string",
                                "enum": ["market_research", "finance", "compliance", "supplier", "full_strategy"],
                            },
                            "execution_plan": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": [
                                        "market_tool",
                                        "country_tool",
                                        "shipping_tool",
                                        "supplier.analysis",
                                        "finance.feasibility",
                                        "compliance.review",
                                    ],
                                },
                            },
                            "reasoning": {"type": "string"},
                        },
                        "required": [
                            "action",
                            "clarification_question",
                            "country",
                            "budget_usd",
                            "focus",
                            "execution_plan",
                            "reasoning",
                        ],
                    },
                }
            },
        }

        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=30, context=self._ssl_context()) as response:
            data = json.loads(response.read().decode("utf-8"))

        plan = json.loads(data["output"][0]["content"][0]["text"])
        plan["raw_query"] = query
        plan["planner"] = "llm"
        plan["planner_notes"] = plan.pop("reasoning")
        return self._normalize_plan(plan)

    def _ssl_context(self):
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()

    def _fallback_plan(self, query):
        normalized = query.lower()
        has_country = self._has_country(normalized)
        has_budget = self._has_budget(normalized)

        if not has_country or not has_budget:
            missing = []
            if not has_country:
                missing.append("target country")
            if not has_budget:
                missing.append("budget")

            return self._normalize_plan(
                {
                    "raw_query": query,
                    "action": "ask_clarification",
                    "clarification_question": f"Please provide the {' and '.join(missing)} for the analysis.",
                    "country": self._country_from(normalized) if has_country else "",
                    "budget_usd": self._budget_from(normalized) if has_budget else 0,
                    "focus": "full_strategy",
                    "execution_plan": [],
                    "planner": "fallback",
                }
            )

        focus = "full_strategy"
        execution_plan = [
            "market_tool",
            "country_tool",
            "shipping_tool",
            "supplier.analysis",
            "finance.feasibility",
            "compliance.review",
        ]

        if any(term in normalized for term in ["market research", "market only", "demand", "customers"]):
            focus = "market_research"
            execution_plan = ["market_tool"]
        elif any(
            term in normalized
            for term in ["financial feasibility", "financially feasible", "finance only", "cost analysis"]
        ):
            focus = "finance"
            execution_plan = ["market_tool", "finance.feasibility"]
        elif any(term in normalized for term in ["compliance", "regulation", "legal", "license", "tax"]):
            focus = "compliance"
            execution_plan = ["market_tool", "country_tool", "compliance.review"]
        elif any(term in normalized for term in ["supplier", "supply", "shipping", "logistics", "import"]):
            focus = "supplier"
            execution_plan = ["market_tool", "shipping_tool", "supplier.analysis"]

        return self._normalize_plan(
            {
                "raw_query": query,
                "action": "execute",
                "clarification_question": "",
                "country": self._country_from(normalized),
                "budget_usd": self._budget_from(normalized),
                "focus": focus,
                "execution_plan": execution_plan,
                "planner": "fallback",
            }
        )

    def _normalize_plan(self, plan):
        plan["action"] = plan.get("action") or "execute"
        plan["clarification_question"] = plan.get("clarification_question") or ""

        country = (plan.get("country") or "").strip().upper()
        plan["country"] = country
        if plan["country"] in {"US", "UNITED STATES", "AMERICA"}:
            plan["country"] = "USA"

        plan["budget_usd"] = int(plan.get("budget_usd") or 0)

        valid_steps = {
            "market_tool",
            "country_tool",
            "shipping_tool",
            "supplier.analysis",
            "finance.feasibility",
            "compliance.review",
        }
        plan["execution_plan"] = [step for step in plan.get("execution_plan", []) if step in valid_steps]

        if plan["action"] == "execute" and "market_tool" not in plan["execution_plan"]:
            plan["execution_plan"].insert(0, "market_tool")

        if plan["action"] == "execute" and (not plan["country"] or not plan["budget_usd"]):
            missing = []
            if not plan["country"]:
                missing.append("target country")
            if not plan["budget_usd"]:
                missing.append("budget")
            plan["action"] = "ask_clarification"
            plan["clarification_question"] = f"Please provide the {' and '.join(missing)} for the analysis."
            plan["execution_plan"] = []

        return plan

    def _has_country(self, query):
        return "usa" in query or "united states" in query or "america" in query

    def _country_from(self, query):
        if "usa" in query or "united states" in query or "america" in query:
            return "USA"
        return ""

    def _has_budget(self, query):
        return re.search(r"(?:usd|\$)?\s*([0-9][0-9,]*)", query) is not None

    def _budget_from(self, query):
        match = re.search(r"(?:usd|\$)?\s*([0-9][0-9,]*)", query)
        if not match:
            return 0
        return int(match.group(1).replace(",", ""))
