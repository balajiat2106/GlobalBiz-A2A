# Business Advisor A2A Demo

Code-level demo for a Business Advisor Agent that plans which MCP-style tools and external agents to call.

## Architecture

```text
User query
  -> Business Advisor Agent
    -> AdvisorPlanner
      -> LLM planner
      -> identified tools
      -> selected tools
      -> identified agent capabilities
      -> selected agent capabilities
    -> MCP-style tools
      -> market_tool
      -> country_tool
      -> shipping_tool
    -> A2A Agent Registry
      -> supplier.analysis
      -> finance.feasibility
      -> compliance.review
```

## Run

```bash
cd business-advisor
python3 app.py
```

## Test

Run the optional LLM smoke test. This uses a small number of OpenAI API calls:

```bash
python3 test_scenarios.py
```

Example queries:

```text
I want to start a business.
I have USD 50000 and want to start a business in USA
I only want market research for USA with USD 50000
I need financial feasibility for USD 50000 in USA
I only care about legal and tax issues for starting in USA with USD 50000
What is the capital of France?
I want to start a money laundering business.
```

Supported demo countries:

```text
USA, UAE, UK, Canada, Australia, Singapore, India
```

If the user asks for a country outside the demo dataset, the Advisor returns a country-specific knowledge message and does not call tools or agents.

## Intelligent Planner

Create a local `.env` file to let the Advisor use an LLM to plan the execution path and ask clarification questions when required information is missing:

```text
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4.1-mini
```

`.env` is ignored by git. Use `.env.example` as the shareable template.

Without a real API key or network access, the Advisor returns a planner error instead of using hardcoded fallback planning.

If the user leaves out required details such as country or budget, the Advisor asks a question before calling any tools or agents.

If the user asks something unrelated to business launch advisory, the Advisor returns an out-of-scope response and does not call tools or agents.

If the user asks for help with illegal business activity, the Advisor refuses and does not call tools or agents.

The Advisor also filters recommendations by budget. If no option fits the user's budget, it returns only the closest option and clearly shows the budget gap instead of listing every over-budget idea as a normal recommendation.

The Advisor honors explicit exclusions. For example, if the user says they do not need supplier, finance, or compliance analysis, the planner removes the matching tools and external agent capabilities before dispatch.

The CLI displays availability versus selection separately:

```text
Identified Tools
Selected Tools
Identified Agent Capabilities
Selected Agent Capabilities
Execution Plan
```

The terminal output is organized as a demo walkthrough:

```text
Step 1: User request and planner decision
Step 2: Discovery surface
Step 3: LLM selection
Step 4: A2A capability registry
Step 5: A2A message exchange
Step 6: MCP tool and advisor trace
Step 7: Final recommendations
Step 8: Recommended next step
```
