from agents.advisor import BusinessAdvisorAgent


def main():
    query = input(
        "Ask your business question: "
    ).strip()

    advisor = BusinessAdvisorAgent()
    report = advisor.recommend(query)

    clarification_count = 0
    while report["action"] == "ask_clarification" and clarification_count < 3:
        print(f"\nAdvisor: {report['clarification_question']}")
        answer = input("You: ").strip()
        query = f"{query}\nClarification: {answer}"
        report = advisor.recommend(query)
        clarification_count += 1

    if report["action"] == "ask_clarification":
        print("\nI still need more information before I can run the analysis.")
        print(f"Question: {report['clarification_question']}")
        return

    print("\n=== Global Business Launch Advisor ===")
    print(f"Query: {report['raw_query']}")
    print(f"Country: {report['country']}")
    print(f"Budget: USD {report['budget_usd']:,}")
    print(f"Focus: {report['focus']}")
    print(f"Planner: {report['planner']}")
    print(f"Planner notes: {report['planner_notes']}")

    print("\nExecution Plan:")
    for step in report["execution_plan"]:
        print(f"- {step}")

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
        print(f"   Market notes: {option['market_notes']}")
        if option["compliance_notes"]:
            print(f"   Compliance notes: {option['compliance_notes']}")
        if option["supplier_notes"]:
            print(f"   Supplier notes: {option['supplier_notes']}")
        if option["finance_notes"]:
            print(f"   Finance notes: {option['finance_notes']}")
        print(f"   Key risks: {', '.join(option['risks'])}")

    print("\nRecommended Next Step:")
    print(report["next_step"])


if __name__ == "__main__":
    main()
