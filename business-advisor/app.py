from agents.advisor import BusinessAdvisorAgent


def main():
    request = {
        "country": "USA",
        "budget_usd": 50000,
        "risk_appetite": "medium",
        "interests": ["import-export", "retail", "services"],
    }

    advisor = BusinessAdvisorAgent()
    report = advisor.recommend(request)

    print("\n=== Global Business Launch Advisor ===")
    print(f"Country: {report['country']}")
    print(f"Budget: USD {report['budget_usd']:,}")

    print("\nDiscovered Capability Registry:")
    for capability, agent in report["capability_registry"].items():
        print(f"- {capability} -> {agent['agent_name']}")

    print("\nAgent Collaboration Trace:")
    for event in report["trace"]:
        print(f"- {event}")

    print("\nTop Business Options:")
    for index, option in enumerate(report["recommendations"], start=1):
        print(f"\n{index}. {option['name']} ({option['score']}/100)")
        print(f"   Summary: {option['summary']}")
        print(f"   Estimated startup cost: USD {option['estimated_startup_cost']:,}")
        print(f"   Profit potential: {option['profit_potential']}")
        print(f"   Compliance notes: {option['compliance_notes']}")
        print(f"   Supplier notes: {option['supplier_notes']}")
        print(f"   Finance notes: {option['finance_notes']}")
        print(f"   Key risks: {', '.join(option['risks'])}")

    print("\nRecommended Next Step:")
    print(report["next_step"])


if __name__ == "__main__":
    main()
