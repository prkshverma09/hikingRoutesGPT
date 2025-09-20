import os
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv
from dedalus_labs.utils.streaming import stream_async
import asyncio

load_dotenv()

async def main():
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    result = await runner.run(
        input="Show all tool calls and their outputs. Find the year GPT-5 released, and handoff to Claude to write a haiku about Elon Musk. Output this haiku. Use your tools.",
        model=["openai/gpt-4.1", "claude-3-5-sonnet-20241022"],
        mcp_servers=["tsion/brave-search-mcp"],
        stream=False
    )

    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
