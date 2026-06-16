import importlib
import json
from pathlib import Path


class AgentRegistry:
    """Capability registry used by the advisor for A2A-style discovery."""

    def __init__(self):
        self.registry_path = Path(__file__).resolve().parents[1] / "data" / "agent_registry.json"
        self.agent_cards = self._load_agent_cards()

    def discover(self, capability):
        matches = []
        for card in self.agent_cards:
            capability_names = [item["name"] for item in card["capabilities"]]
            if capability in capability_names:
                matches.append(card)

        if not matches:
            raise LookupError(f"No external agent found for capability: {capability}")

        return matches[0]

    def list_capabilities(self):
        capabilities = {}
        for card in self.agent_cards:
            for item in card["capabilities"]:
                capabilities[item["name"]] = {
                    "agent_id": card["id"],
                    "agent_name": card["name"],
                    "description": item["description"],
                }
        return capabilities

    def _load_agent_cards(self):
        with self.registry_path.open(encoding="utf-8") as file:
            return json.load(file)["agents"]


class A2AClient:
    """Small local transport that sends task envelopes to discovered agents."""

    def send_task(self, agent_card, capability, payload):
        agent = self._load_local_agent(agent_card["endpoint"])
        task = {
            "to": agent_card["id"],
            "capability": capability,
            "payload": payload,
        }
        return agent.handle_task(task)

    def _load_local_agent(self, endpoint):
        if not endpoint.startswith("local://"):
            raise ValueError(f"Unsupported demo endpoint: {endpoint}")

        import_path = endpoint.replace("local://", "")
        module_name, class_name = import_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        agent_class = getattr(module, class_name)
        return agent_class()
