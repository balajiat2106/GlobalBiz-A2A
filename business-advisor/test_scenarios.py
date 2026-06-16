import os

from agents.advisor import BusinessAdvisorAgent


def assert_case(name, query, expected):
    report = BusinessAdvisorAgent().recommend(query)
    assert report["action"] == expected["action"], f"{name}: action={report['action']}"

    if report["action"] == "execute":
        assert report["country"] == expected["country"], f"{name}: country={report['country']}"
        assert report["budget_usd"] == expected["budget_usd"], f"{name}: budget={report['budget_usd']}"
        assert report["selected_tools"] == expected["selected_tools"], (
            f"{name}: selected_tools={report['selected_tools']}"
        )
        assert report["selected_agent_capabilities"] == expected["selected_agent_capabilities"], (
            f"{name}: selected_agent_capabilities={report['selected_agent_capabilities']}"
        )

    print(f"PASS: {name}")


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "replace_with_your_openai_api_key":
        raise SystemExit("Set OPENAI_API_KEY to run LLM planner smoke tests.")

    cases = [
        (
            "market only",
            "I have USD 50000 and only want market research for starting a business in USA",
            {
                "action": "execute",
                "country": "USA",
                "budget_usd": 50000,
                "selected_tools": ["market_tool"],
                "selected_agent_capabilities": [],
            },
        ),
        (
            "exclude compliance and logistics",
            "I want to do a business in UAE and skip compliance and logistics. I have USD 10000",
            {
                "action": "execute",
                "country": "UAE",
                "budget_usd": 10000,
                "selected_tools": ["market_tool"],
                "selected_agent_capabilities": ["finance.feasibility"],
            },
        ),
    ]

    for name, query, expected in cases:
        assert_case(name, query, expected)

    print(f"\n{len(cases)} LLM smoke scenarios passed.")


if __name__ == "__main__":
    main()
