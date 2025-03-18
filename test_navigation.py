#!/usr/bin/env python3
import asyncio
from browser_use import Agent
from langchain_ollama import ChatOllama

async def main():
    print("Initializing Qwen2.5 model through Ollama...")
    llm = ChatOllama(model="qwen2.5", num_ctx=32000)
    
    # Create a very simple task with explicit URL navigation
    task = "Visit https://cudportal.cud.ac.ae/student/login.asp and tell me the page title"
    
    # Configure the agent with proper parameters
    print("Creating Browser Use agent...")
    agent = Agent(
        task=task,
        llm=llm,
    )
    
    print("Running agent to test navigation...")
    try:
        result = await agent.run()
        print("Agent returned result:")
        print(result)
    except Exception as e:
        print(f"Error running agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())