import asyncio
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv
from dedalus_labs.utils.streaming import stream_async

load_dotenv()

async def main():
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    result = runner.run(
        input="What do you think of Mulligan?",
        model="openai/gpt-4o-mini",
        stream=True
    )

    # use stream parameter and stream_async function to stream output
    await stream_async(result)

if __name__ == "__main__":
    asyncio.run(main())
