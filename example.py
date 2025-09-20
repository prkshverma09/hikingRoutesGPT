import asyncio
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv
from dedalus_labs.utils.streaming import stream_async

load_dotenv()

def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert temperature from Celsius to Fahrenheit."""
    return (celsius * 9/5) + 32

def get_clothing_recommendation(temp_f: float) -> str:
    """Recommend clothing based on temperature in Fahrenheit."""
    if temp_f < 32:
        return "Heavy winter coat, gloves, hat, and warm boots"
    elif temp_f < 50:
        return "Warm jacket or coat, long pants, closed shoes"
    elif temp_f < 65:
        return "Light jacket or sweater, long pants"
    elif temp_f < 80:
        return "T-shirt or light shirt, comfortable pants or shorts"
    else:
        return "Lightweight clothing, shorts, sandals, and sun protection"

def plan_activity(temp_f: float, clothing: str) -> str:
    """Suggest outdoor activities based on temperature and clothing."""
    if temp_f < 32:
        return f"Great weather for skiing, ice skating, or cozy indoor activities. Dress in: {clothing}"
    elif temp_f < 50:
        return f"Perfect for hiking, jogging, or outdoor photography. Dress in: {clothing}"
    elif temp_f < 80:
        return f"Ideal for picnics, outdoor sports, or walking in the park. Dress in: {clothing}"
    else:
        return f"Excellent for swimming, beach activities, or water sports. Dress in: {clothing}"

async def main():
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    result = await runner.run(
        input="Show all tool calls and their outputs. Show all handoffs. It's 22 degrees Celsius today in Paris. Convert this to Fahrenheit, recommend what I should wear, suggest outdoor activities, and search for current weather conditions in Paris to confirm.",
        model=["openai/gpt-4.1"],
        tools=[celsius_to_fahrenheit, get_clothing_recommendation, plan_activity],
        mcp_servers=["joerup/open-meteo-mcp", "tsion/brave-search-mcp"],
        stream=False
    )

    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
