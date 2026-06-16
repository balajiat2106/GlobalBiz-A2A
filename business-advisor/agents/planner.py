import json
import os
import ssl
import urllib.error
import urllib.request

from config import load_env


class AdvisorPlanner:
    """LLM-only planner for tool and agent capability selection."""

    def __init__(self, registry):
        load_env()
        self.registry = registry

    def plan(self, query):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "replace_with_your_openai_api_key":
            return self._planner_error(query, "OPENAI_API_KEY is missing or still set to the placeholder.")

        try:
            return self._plan_with_llm(query)
        except (OSError, ValueError, KeyError, urllib.error.URLError, urllib.error.HTTPError) as error:
            return self._planner_error(query, f"LLM planner failed: {error}")

    def _plan_with_llm(self, query):
        available_tools = self._available_tools()
        available_capabilities = self.registry.list_capabilities()

        prompt = {
            "role": "user",
            "content": (
                "You are the only planning brain for a Business Advisor Agent. "
                "Read the user query and decide the action and exact tool/agent capability selection. "
                "Treat lines beginning with 'Clarification:' as user-provided answers to earlier questions. "
                "If the query is not about starting, evaluating, launching, or researching a business, "
                "return action out_of_scope and select no tools or capabilities. "
                "If the query asks for help with illegal business activity, including fraud, scams, "
                "money laundering, tax evasion, smuggling, counterfeit goods, or other unlawful activity, "
                "return action out_of_scope and select no tools or capabilities. "
                "If the user does not provide a target country or budget, return action ask_clarification, "
                "ask one concise clarification question, and select no tools or capabilities. "
                "A budget is required for every executable business analysis. Do not infer the budget from "
                "return expectations, desired profit, or words like high returns. "
                "For execute actions, country must be non-empty and budget_usd must be greater than 0. "
                "If the user already provides both target country and budget, do not ask a clarification question. "
                "First identify all available tools and capabilities. Then select only the tools and external "
                "agent capabilities needed for the user's exact scope. "
                "Honor explicit exclusions from the user. If the user says they do not need supplier, finance, "
                "compliance, legal, tax, licensing, shipping, or logistics analysis, do not select those tools "
                "or capabilities. "
                "Return strict JSON with keys: action, clarification_question, country, budget_usd, focus, "
                "identified_tools, selected_tools, identified_agent_capabilities, "
                "selected_agent_capabilities, reasoning. "
                "Valid action values are ask_clarification, execute, and out_of_scope. "
                "Valid selected_tools items are market_tool, country_tool, shipping_tool. "
                "Valid selected_agent_capabilities items are supplier.analysis, finance.feasibility, compliance.review. "
                "Use market_tool whenever recommendations or product options are needed. "
                "Use country_tool only when compliance/legal/setup/tax/country setup details are needed. "
                "Use shipping_tool only when supplier/import/export/shipping/logistics details are needed. "
                "Use external capabilities only when their expertise is needed. "
                "Dependency rules: every execute action requires market_tool because final recommendations "
                "are product-based; supplier.analysis requires market_tool and shipping_tool; "
                "finance.feasibility requires market_tool; compliance.review requires market_tool and country_tool. "
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
                            "action": {"type": "string", "enum": ["ask_clarification", "execute", "out_of_scope"]},
                            "clarification_question": {"type": "string"},
                            "country": {"type": "string"},
                            "budget_usd": {"type": "integer"},
                            "focus": {
                                "type": "string",
                                "enum": ["market_research", "finance", "compliance", "supplier", "full_strategy"],
                            },
                            "identified_tools": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["market_tool", "country_tool", "shipping_tool"],
                                },
                            },
                            "selected_tools": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["market_tool", "country_tool", "shipping_tool"],
                                },
                            },
                            "identified_agent_capabilities": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["supplier.analysis", "finance.feasibility", "compliance.review"],
                                },
                            },
                            "selected_agent_capabilities": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["supplier.analysis", "finance.feasibility", "compliance.review"],
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
                            "identified_tools",
                            "selected_tools",
                            "identified_agent_capabilities",
                            "selected_agent_capabilities",
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

    def _planner_error(self, query, message):
        return self._normalize_plan(
            {
                "raw_query": query,
                "action": "planner_error",
                "clarification_question": "",
                "country": "",
                "budget_usd": 0,
                "focus": "full_strategy",
                "identified_tools": [tool["name"] for tool in self._available_tools()],
                "selected_tools": [],
                "identified_agent_capabilities": list(self.registry.list_capabilities().keys()),
                "selected_agent_capabilities": [],
                "planner": "llm",
                "planner_notes": message,
            }
        )

    def _normalize_plan(self, plan):
        plan["action"] = plan.get("action") or "planner_error"
        plan["clarification_question"] = plan.get("clarification_question") or ""
        plan["planner_notes"] = plan.get("planner_notes", "")
        plan["identified_tools"] = [tool["name"] for tool in self._available_tools()]
        plan["identified_agent_capabilities"] = list(self.registry.list_capabilities().keys())

        country = (plan.get("country") or "").strip().upper()
        aliases = {
            "US": "USA",
            "UNITED STATES": "USA",
            "AMERICA": "USA",
            "UNITED KINGDOM": "UK",
            "GREAT BRITAIN": "UK",
            "BRITAIN": "UK",
            "ENGLAND": "UK",
            "UNITED ARAB EMIRATES": "UAE",
        }
        plan["country"] = aliases.get(country, country)
        plan["budget_usd"] = int(plan.get("budget_usd") or 0)

        valid_tools = set(plan["identified_tools"])
        valid_capabilities = set(plan["identified_agent_capabilities"])
        plan["selected_tools"] = [tool for tool in plan.get("selected_tools", []) if tool in valid_tools]
        plan["selected_agent_capabilities"] = [
            capability for capability in plan.get("selected_agent_capabilities", []) if capability in valid_capabilities
        ]
        self._apply_required_dependencies(plan)
        plan["execution_plan"] = plan["selected_tools"] + plan["selected_agent_capabilities"]

        if plan["action"] in {"ask_clarification", "out_of_scope", "planner_error"}:
            plan["selected_tools"] = []
            plan["selected_agent_capabilities"] = []
            plan["execution_plan"] = []

        if plan["action"] == "execute" and (not plan["country"] or plan["budget_usd"] <= 0):
            missing = []
            if not plan["country"]:
                missing.append("target country")
            if plan["budget_usd"] <= 0:
                missing.append("budget")
            plan["action"] = "ask_clarification"
            plan["clarification_question"] = f"Please provide the {' and '.join(missing)} for the analysis."
            plan["selected_tools"] = []
            plan["selected_agent_capabilities"] = []
            plan["execution_plan"] = []

        return plan

    def _apply_required_dependencies(self, plan):
        if plan["action"] != "execute":
            return

        if "market_tool" not in plan["selected_tools"]:
            plan["selected_tools"].append("market_tool")

        dependencies = {
            "supplier.analysis": ["market_tool", "shipping_tool"],
            "finance.feasibility": ["market_tool"],
            "compliance.review": ["market_tool", "country_tool"],
        }

        for capability in plan["selected_agent_capabilities"]:
            for tool in dependencies.get(capability, []):
                if tool not in plan["selected_tools"]:
                    plan["selected_tools"].append(tool)

    def _available_tools(self):
        return [
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

    def _ssl_context(self):
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()
