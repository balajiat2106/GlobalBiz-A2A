from textwrap import fill

from agents.advisor import BusinessAdvisorAgent


WIDTH = 96


def line(char="-"):
    print(char * WIDTH)


def banner(title):
    print()
    line("=")
    print(f"{title.center(WIDTH)}")
    line("=")


def section(number, title):
    print()
    line()
    print(f"STEP {number}: {title}")
    line()


def bullet(value, indent=2):
    print(f"{' ' * indent}- {value}")


def label(name, value):
    print(f"{name:<22}: {value}")


def wrap_text(text, indent=2, width=88):
    prefix = " " * indent
    print(fill(str(text), width=width, initial_indent=prefix, subsequent_indent=prefix))


def print_list(values, empty="- none"):
    if values:
        for value in values:
            bullet(value)
    else:
        bullet(empty)


def format_clarification(question, answer):
    normalized = question.lower()
    if "country" in normalized and "budget" in normalized:
        return f"Target country and budget: {answer}."
    if "budget" in normalized:
        return f"Budget is USD {answer}."
    if "country" in normalized:
        return f"Target country is {answer}."
    return answer


def print_non_execution(report):
    banner("GlobalBiz Business Advisor")
    section(1, "Advisor Response")
    wrap_text(report["message"])
    print()
    label("Planner", report["planner"])
    label("Planner notes", report["planner_notes"])

    if report["action"] == "planner_error":
        section(2, "Available Discovery Surface")
        print("Identified MCP Tools:")
        print_list(report["identified_tools"])
        print("\nIdentified A2A Agent Capabilities:")
        print_list(report["identified_agent_capabilities"])


def print_report(report):
    banner("GlobalBiz A2A Launch Advisor")

    section(1, "User Request And Planner Decision")
    label("Query", report["raw_query"].replace("\n", " | "))
    label("Country", report["country"])
    label("Budget", f"USD {report['budget_usd']:,}")
    label("Focus", report["focus"])
    label("Planner", report["planner"])
    print("\nPlanner reasoning:")
    wrap_text(report["planner_notes"])
    print("\nBudget fit:")
    wrap_text(report["budget_summary"])

    section(2, "Discovery: What Is Available")
    print("Identified MCP Tools:")
    print_list(report["identified_tools"])
    print("\nIdentified A2A Agent Capabilities:")
    print_list(report["identified_agent_capabilities"])

    section(3, "Selection: What The LLM Chose")
    print("Selected MCP Tools:")
    print_list(report["selected_tools"])
    print("\nSelected A2A Agent Capabilities:")
    print_list(report["selected_agent_capabilities"])
    print("\nCombined Execution Plan:")
    print_list(report["execution_plan"])

    section(4, "A2A Capability Registry")
    for capability, agent in report["capability_registry"].items():
        print(f"{capability:<24} -> {agent['agent_name']} ({agent['agent_id']})")
        wrap_text(agent["description"], indent=4)

    section(5, "A2A Message Exchange")
    if report["a2a_events"]:
        for index, event in enumerate(report["a2a_events"], start=1):
            print(f"A2A-{index}: {event['capability']}")
            print(f"  Agent Card      : {event['agent_name']} | {event['agent_id']} | v{event['version']}")
            print(f"  Endpoint        : {event['endpoint']}")
            print(f"  Task Envelope   : to={event['agent_id']} capability={event['capability']}")
            print(f"  Payload Keys    : {', '.join(event['payload_keys'])}")
            print(f"  Response        : {event['response_items']} product-level result(s)")
            print()
    else:
        print("No external A2A agents were called for this request.")

    section(6, "MCP Tool And Advisor Trace")
    for event in report["trace"]:
        bullet(event)

    section(7, "Final Recommendations")
    for index, option in enumerate(report["recommendations"], start=1):
        print(f"{index}. {option['name']} | Score {option['score']}/100")
        label("Startup cost", f"USD {option['estimated_startup_cost']:,}")
        label("Budget status", option["budget_status"])
        label("Profit potential", option["profit_potential"])
        print("Summary:")
        wrap_text(option["summary"], indent=4)
        print("Market:")
        wrap_text(option["market_notes"], indent=4)
        if option["supplier_notes"]:
            print("Supplier Agent:")
            wrap_text(option["supplier_notes"], indent=4)
        if option["finance_notes"]:
            print("Finance Agent:")
            wrap_text(option["finance_notes"], indent=4)
        if option["compliance_notes"]:
            print("Compliance Agent:")
            wrap_text(option["compliance_notes"], indent=4)
        print("Key risks:")
        print_list(option["risks"], empty="none")
        print()

    section(8, "Recommended Next Step")
    wrap_text(report["next_step"])
    line("=")


def main():
    query = input("Ask your business question: ").strip()

    advisor = BusinessAdvisorAgent()
    report = advisor.recommend(query)

    clarification_count = 0
    while report["action"] == "ask_clarification" and clarification_count < 3:
        print()
        line()
        print("CLARIFICATION NEEDED")
        line()
        print(f"Advisor: {report['clarification_question']}")
        answer = input("You: ").strip()
        clarification = format_clarification(report["clarification_question"], answer)
        query = f"{query}\nClarification: {clarification}"
        report = advisor.recommend(query)
        clarification_count += 1

    if report["action"] == "ask_clarification":
        banner("GlobalBiz Business Advisor")
        section(1, "More Information Needed")
        print(f"Question: {report['clarification_question']}")
        return

    if report["action"] in {"out_of_scope", "planner_error", "unsupported_country"}:
        print_non_execution(report)
        return

    print_report(report)


if __name__ == "__main__":
    main()
