from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from pydantic import SecretStr
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

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
    result = await agent.run()
    print(f"Task completed: {result}")

# Run the async function
if __name__ == "__main__":
    asyncio.run(run_agent())