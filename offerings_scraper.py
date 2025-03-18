from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
from pydantic import SecretStr
import os
import asyncio
from dotenv import load_dotenv
import json
import sys
import pandas as pd
import re
import traceback
import logging
import getpass

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

# Function to extract course data from the agent's results
def process_extracted_data(result):
    """Process the data returned from the agent run"""
    try:
        # Try to find and parse JSON in the result
        json_match = re.search(r'\[[\s\S]*\]', result)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            try:
                # If no clear JSON pattern, try parsing the whole response
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Could not parse result as JSON")
                return None
    except Exception as e:
        logger.error("Error processing extraction: %s", e)
        logger.debug("Raw result: %s...", result[:200])
        return None

# Main function to run the script
async def main():
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", 
            api_key=SecretStr(os.getenv('GEMINI_API_KEY'))
        )

        username = input("Enter your CUD Portal username: ")
        password = getpass.getpass("Enter your CUD Portal password: ")
        
        # Define the task for the Browser Use agent
        task = """
        Follow these steps precisely:
        
        1. Navigate to https://cudportal.cud.ac.ae/student/login.asp
        2. Login with username and password provided
        3. Wait for the dashboard to load completely
        4. Find and click on the menu item related to "Course Registration"
        5. Find and click on "Course Offerings" link or button
        6. Wait for the page to load completely
        7. Find and click on "Show Filter" button
        8. Wait for filter options to appear
        9. Select "SEAST" from the Divisions dropdown/selection field
        10. Click the "Apply Filter" button
        11. Wait for the filtered results to load completely
        12. Extract ALL course information from the table in this format:
            - Course code
            - Course name
            - Credits
            - Instructor
            - Room
            - Days
            - Start Time
            - End Time
            - Max Enrollment
            - Total Enrollment
        
        Return the data as a JSON array of objects with these exact field names.
        """

        sensitive_data = {
            'user': username,
            "password": password,
        }

        logger.info("Initializing browser automation agent...")
        agent = Agent(
            task=task,
            llm=llm,
            sensitive_data=sensitive_data
        )
        
        logger.info("Starting course data extraction from CUD portal...")
        result = await agent.run()
        
        # Process the extracted data
        courses = process_extracted_data(result)
        
        # Save to CSV if we have data
        if courses:
            df = pd.DataFrame(courses)
            csv_path = os.path.join(os.path.dirname(__file__), 'course_offerings.csv')
            df.to_csv(csv_path, index=False)
            logger.info("Course data saved to %s", csv_path)
            
            # Also save to Excel for convenience
            excel_path = os.path.join(os.path.dirname(__file__), 'course_offerings.xlsx')
            df.to_excel(excel_path, index=False)
            logger.info("Course data also saved to %s", excel_path)
        else:
            logger.error("No course data was extracted or there was an error.")
            logger.debug("Raw agent result:")
            logger.debug("%s", result)
        return
        
    except Exception as e:
        logger.error("Error: %s", e)
        logger.error("%s", traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nScript terminated by user.")
        sys.exit(0)