from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Controller
from pydantic import BaseModel, Field
from typing import List
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

api_key = os.getenv("GEMINI_API_KEY")

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


# Define Pydantic models for structured output
class Course(BaseModel):
    course_code: str = Field(description="The course code identifier")
    course_name: str = Field(description="The name of the course")
    credits: str = Field(description="Number of credits for the course")
    instructor: str = Field(description="Name of the instructor")
    room: str = Field(description="Room where the course is held")
    days: str = Field(description="Days when the course meets (e.g., M, T, W)")
    start_time: str = Field(description="Start time of the course")
    end_time: str = Field(description="End time of the course")
    max_enrollment: str = Field(description="Maximum enrollment allowed")
    total_enrollment: str = Field(description="Current total enrollment")


class CourseOfferings(BaseModel):
    courses: List[Course] = Field(description="List of course offerings")


def process_result(result):
    """Process the structured result from the agent"""
    try:
        # Initialize an empty list to store all courses
        all_courses = []

        # For AgentHistoryList result type
        if hasattr(result, "final_result"):
            # Get the final structured result
            final_result = result.final_result()
            if final_result:
                # Parse the JSON result into our Pydantic model
                return CourseOfferings.model_validate_json(final_result)

        # Process all steps in the agent history to find extracted content
        if hasattr(result, "__iter__"):
            for step in result:
                # Check for controller_response which contains extracted data
                if hasattr(step, "controller_response") and step.controller_response:
                    response = str(step.controller_response)

                    # Look for JSON data in the response
                    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response)
                    if json_match:
                        json_str = json_match.group(1)
                        try:
                            courses_data = json.loads(json_str)
                            # Add these courses to our accumulated list
                            if isinstance(courses_data, list):
                                all_courses.extend(courses_data)
                        except Exception as e:
                            logger.error("Error parsing JSON from step: %s", e)
                            continue

        # Return the accumulated courses
        if all_courses:
            return CourseOfferings(courses=all_courses)

        # If we haven't found courses yet, try other methods
        logger.error("Could not extract course data from agent result")
        return None

    except Exception as e:
        logger.error("Error processing result: %s", e)
        logger.error(traceback.format_exc())
        return None


# Main function to run the script
async def main():
    try:
        # Use the API key directly without SecretStr wrapper
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", google_api_key=api_key
        )

        username = input("Enter your CUD Portal username: ")
        password = getpass.getpass("Enter your CUD Portal password: ")

        # btw this is done to save on credits, but def not memory or cpu

        course_code = input(
            "Enter the course code to search for (or press Enter for None): "
        )
        if course_code:
            course_code = f"[{course_code}]"

        course_name = input(
            "Enter the course name to search for (or press Enter for None): "
        )
        if course_name:
            course_name = f"[{course_name}]"

        creds = input(
            "Enter the number of credits to search for (or press Enter for None): "
        )
        if creds:
            creds = f"[{creds}]"

        instructor = input(
            "Enter the instructor name to search for (or press Enter for None): "
        )
        if instructor:
            instructor = f"[{instructor}]"

        room = input("Enter the room to search for (or press Enter for None): ")
        if room:
            room = f"[{room}]"

        days = input("Enter the days to search for, MTWR (or press Enter for None): ")
        if days:
            days = f"[{days}]"

        start_time = input(
            "Enter a minimum start time to search for (or press Enter for None): "
        )
        if start_time:
            start_time = f"[{start_time}]"

        end_time = input(
            "Enter a maximum end time to search for (or press Enter for None): "
        )
        if end_time:
            end_time = f"[{end_time}]"

        max_enrollment = input(
            "Enter the maximum enrollment to search for (or press Enter for None): "
        )
        if max_enrollment:
            max_enrollment = f"[{max_enrollment}]"

        total_enrollment = input(
            "Enter the total enrollment to search for (or press Enter for None): "
        )
        if total_enrollment:
            total_enrollment = f"[{total_enrollment}]"

        # Define the task for the Browser Use agent
        task = f"""
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
        12. Extract ALL course information from the table with these field names:
            - course_code {course_code}
            - course_name {course_name}
            - credits {creds}
            - instructor {instructor}
            - room {room}
            - days {days}
            - start_time {start_time}
            - end_time {end_time}
            - max_enrollment {max_enrollment}
            - total_enrollment {total_enrollment}

        13. Repeat step 12 for the page 2 and 3 if available THEN STOP FOR 1 SECOND AND PROCEED TO THE NEXT STEP
        14. Combine all extracted course data into a single JSON array



        IMPORTANT: After extracting data from each page, always return the full set of course data you've collected so far.
        Store the extracted course data after each page and maintain this data throughout the entire process.
        Do not return an empty array when you're done
        """

        # TODO: above is a possible use of system prompts.

        sensitive_data = {
            "user": username,
            "password": password,
        }

        # Set up controller with our output model
        controller = Controller(output_model=CourseOfferings)

        logger.info("Initializing browser automation agent...")
        agent = Agent(
            task=task,
            llm=llm,
            sensitive_data=sensitive_data,
            controller=controller,
        )

        logger.info("Starting course data extraction from CUD portal...")
        result = await agent.run(max_steps=100)

        # Process the result
        course_offerings = process_result(result)

        # Save to CSV if we have data
        if course_offerings and course_offerings.courses:
            # Convert Pydantic model to DataFrame
            df = pd.DataFrame(
                [course.model_dump() for course in course_offerings.courses]
            )

            # Save to results.csv as requested
            csv_path = os.path.join(os.path.dirname(__file__), "results.csv")
            df.to_csv(csv_path, index=False)
            logger.info("Course data saved to %s", csv_path)

            # Also save to Excel for convenience
            excel_path = os.path.join(
                os.path.dirname(__file__), "course_offerings.xlsx"
            )
            df.to_excel(excel_path, index=False)
            logger.info("Course data also saved to %s", excel_path)

            logger.info("Retrieved %d courses", len(course_offerings.courses))
        else:
            logger.error("No course data was extracted or there was an error.")

    except Exception as e:
        logger.error("Error: %s", e)
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nScript terminated by user.")
        sys.exit(0)
