from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Controller
from pydantic import BaseModel, SecretStr, Field
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
        # For AgentHistoryList result type
        if hasattr(result, "final_result"):
            # Get the final structured result
            final_result = result.final_result()
            if final_result:
                # Parse the JSON result into our Pydantic model
                return CourseOfferings.model_validate_json(final_result)
            else:
                logger.error("No final result available in agent history")
        
        # For non-structured results, fallback to extracting from response
        if hasattr(result, "get_all_output_messages"):
            messages = result.get_all_output_messages()
            for message in messages:
                if hasattr(message, "content"):
                    content = message.content
                    # Try to extract JSON from content
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
                    if json_match:
                        json_str = json_match.group(1)
                        # Try to parse as CourseOfferings
                        try:
                            courses_data = json.loads(json_str)
                            # If it's an array of courses, wrap it in the expected structure
                            if isinstance(courses_data, list):
                                return CourseOfferings(courses=courses_data)
                            return CourseOfferings.model_validate(courses_data)
                        except Exception as e:
                            logger.error(f"Error parsing JSON: {e}")
        
        # Extract from controller response if available
        for step in result:
            if hasattr(step, 'controller_response') and step.controller_response:
                response = step.controller_response
                if 'Extracted from page' in str(response):
                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', str(response))
                    if json_match:
                        json_str = json_match.group(1)
                        courses_data = json.loads(json_str)
                        # Convert keys to snake_case if they're in different format
                        formatted_courses = []
                        for course in courses_data:
                            formatted_course = {
                                "course_code": course.get("Course Code", ""),
                                "course_name": course.get("Course Name", ""),
                                "credits": course.get("Credits", ""),
                                "instructor": course.get("Instructor", ""),
                                "room": course.get("Room", ""),
                                "days": course.get("Days", ""),
                                "start_time": course.get("Start Time", ""),
                                "end_time": course.get("End Time", ""),
                                "max_enrollment": course.get("Max Enrollment", ""),
                                "total_enrollment": course.get("Total Enrollment", "")
                            }
                            formatted_courses.append(formatted_course)
                        return CourseOfferings(courses=formatted_courses)
        
        logger.error("Could not extract course data from agent result")
        return None
        
    except Exception as e:
        logger.error(f"Error processing result: {e}")
        logger.error(traceback.format_exc())
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
        
        # TODO: there is no need to have in the "task" the square brackets, find a way to inclose them in [] here
        course_code = input("Enter the course code to search for (or press Enter for None): ")
        course_name = input("Enter the course name to search for (or press Enter for None): ")
        credits = input("Enter the number of credits to search for (or press Enter for None): ")
        instructor = input("Enter the instructor name to search for (or press Enter for None): ")
        room = input("Enter the room to search for (or press Enter for None): ")
        days = input("Enter the days to search for, MTWR (or press Enter for None): ")
        start_time = input("Enter a minimum start time to search for (or press Enter for None): ")
        end_time = input("Enter a maximum end time to search for (or press Enter for None): ")
        max_enrollment = input("Enter the maximum enrollment to search for (or press Enter for None): ")
        total_enrollment = input("Enter the total enrollment to search for (or press Enter for None): ")

        
        
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
            - credits {credits}
            - instructor {instructor}
            - room {room}
            - days {days}
            - start_time {start_time}
            - end_time {end_time}
            - max_enrollment {max_enrollment}
            - total_enrollment {total_enrollment}
        
        if there are multiple pages under SEAST, navigate to each page other page and extract the course information as per the previous field names
        
        Return the data as a JSON array of course objects with these exact field names.
        """

        sensitive_data = {
            'user': username,
            "password": password,
        }

        # Set up controller with our output model
        controller = Controller(output_model=CourseOfferings)

        logger.info("Initializing browser automation agent...")
        agent = Agent(
            task=task,
            llm=llm,
            sensitive_data=sensitive_data,
            controller=controller
        )
        
        logger.info("Starting course data extraction from CUD portal...")
        result = await agent.run()
        
        # Process the result
        course_offerings = process_result(result)
        
        # Save to CSV if we have data
        if course_offerings and course_offerings.courses:
            # Convert Pydantic model to DataFrame
            df = pd.DataFrame([course.model_dump() for course in course_offerings.courses])
            
            # Save to results.csv as requested
            csv_path = os.path.join(os.path.dirname(__file__), 'results.csv')
            df.to_csv(csv_path, index=False)
            logger.info(f"Course data saved to {csv_path}")
            
            # Also save to Excel for convenience
            excel_path = os.path.join(os.path.dirname(__file__), 'course_offerings.xlsx')
            df.to_excel(excel_path, index=False)
            logger.info(f"Course data also saved to {excel_path}")
            
            logger.info(f"Retrieved {len(course_offerings.courses)} courses")
        else:
            logger.error("No course data was extracted or there was an error.")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nScript terminated by user.")
        sys.exit(0)