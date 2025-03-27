from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from src.agent_runner import AgentRunner
from src.utils import get_filters_from_user, save_results
from src.models import CourseOfferings
import os
import asyncio
import logging
import getpass

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

async def main():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY not found in .env file.")

        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", api_key=api_key)

        username = input("Enter your CUD Portal username: ")
        password = getpass.getpass("Enter your CUD Portal password: ")
        filters = get_filters_from_user()

        runner = AgentRunner(llm=llm, username=username, password=password, filters=filters)
        logger.info("Running schedule extraction...")

        offerings: CourseOfferings = await runner.run()

        if offerings and offerings.courses:
            save_results(offerings)
            logger.info("Successfully saved %d courses.", len(offerings.courses))
        else:
            logger.warning("No course data extracted.")

    except Exception as e:
        logger.error("Login failed: Invalid username or password.", e)
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user.")
    except Exception as e:
        logger.error("Unhandled Exception: %s", e)

if __name__ == "__main__":
    asyncio.run(main())
