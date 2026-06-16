import json
from pathlib import Path


class ShippingTool:
    """MCP-style tool that returns logistics assumptions."""

    def __init__(self):
        self.data_path = Path(__file__).resolve().parents[1] / "data" / "countries.json"

    def get_shipping_profile(self, country):
        with self.data_path.open(encoding="utf-8") as file:
            data = json.load(file)
        return data[country]["shipping"]
