import json
from pathlib import Path


class MarketTool:
    """MCP-style tool that returns local market/product data."""

    def __init__(self):
        self.data_path = Path(__file__).resolve().parents[1] / "data" / "products.json"

    def get_market_options(self, country):
        with self.data_path.open(encoding="utf-8") as file:
            data = json.load(file)
        return {"country": country, "products": data[country]}

    def available_countries(self):
        with self.data_path.open(encoding="utf-8") as file:
            data = json.load(file)
        return sorted(data.keys())
