import asyncio
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv
from dedalus_labs.utils.streaming import stream_async

load_dotenv()

async def main():
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    result = await runner.run(
        input="""I want to do a cycle tour near harrow, london. come up with a tour near that.
        Give me the tour as a list of locations and their coordinates in a json file. Don't output anything else.""",
        model="openai/gpt-4.1",
        mcp_servers=[
            "joerup/exa-mcp",        # For semantic travel research
            "tsion/brave-search-mcp", # For travel information search
        ]
    )

    print(f"Travel Planning Results:\n{result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())
