from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from pydantic import SecretStr
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# Initialize the model
llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(os.getenv('GEMINI_API_KEY')))

# Create agent with the model
agent = Agent(
    task="Go to google.com and search for 'weather today'. Find the current temperature and return it.",
    llm=llm,

)

# Execute the agent
try:
    print("Starting browser navigation task...")
    result = agent.run()
    print("Task completed!")
    print(f"Result: {result}")
except Exception as e:
    print(f"An error occurred during execution: {str(e)}")
    import traceback
    traceback.print_exc()