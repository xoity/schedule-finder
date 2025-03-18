from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from pydantic import SecretStr
import os
import asyncio
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")

# Initialize the model
llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(os.getenv('GEMINI_API_KEY')))

# Create agent with the model
agent = Agent(
    task="open chrome and search for the best restaurants in Dubai",
    llm=llm
)

# Define async function to run the agent
async def run_agent():
    logger.info("Starting browser automation test...")
    result = await agent.run()
    logger.info("Task completed: %s", result)

# Run the async function
if __name__ == "__main__":
    asyncio.run(run_agent())