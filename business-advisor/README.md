# Business Advisor A2A Demo

Code-level demo for a Business Advisor Agent that plans which MCP-style tools and external agents to call.

## Architecture

```text
User query
  -> Business Advisor Agent
    -> AdvisorPlanner
      -> LLM planner when OPENAI_API_KEY is set
      -> local fallback planner when no API key is set
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

Example queries:

```text
I want to start a business.
I have USD 50000 and want to start a business in USA
I only want market research for USA with USD 50000
I need financial feasibility for USD 50000 in USA
I only care about legal and tax issues for starting in USA with USD 50000
```

## Intelligent Planner

Create a local `.env` file to let the Advisor use an LLM to plan the execution path and ask clarification questions when required information is missing:

```text
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4.1-mini
```

`.env` is ignored by git. Use `.env.example` as the shareable template.

Without a real API key, the project still runs using a local fallback planner so the demo never breaks.

If the user leaves out required details such as country or budget, the Advisor asks a question before calling any tools or agents.
