from browser_use import Agent, Controller
from src.models import CourseOfferings
import re
import json
import logging
import traceback

logger = logging.getLogger(__name__)


class AgentRunner:
    def __init__(self, llm, username: str, password: str, filters: dict):
        self.llm = llm
        self.username = username
        self.password = password
        self.filters = filters
        # Use Controller with output_model for structured output
        self.controller = Controller(output_model=CourseOfferings)

    def _build_task(self) -> str:
        # Insert filters into the formatted task string
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
            - course_code {self.filters.get("course_code")}
            - course_name {self.filters.get("course_name")}
            - credits {self.filters.get("credits")}
            - instructor {self.filters.get("instructor")}
            - room {self.filters.get("room")}
            - days {self.filters.get("days")}
            - start_time {self.filters.get("start_time")}
            - end_time {self.filters.get("end_time")}
            - max_enrollment {self.filters.get("max_enrollment")}
            - total_enrollment {self.filters.get("total_enrollment")}
        13. Repeat step 12 for the page 2 and 3 if available, THEN STOP FOR 1 SECOND AND PROCEED TO THE NEXT STEP
        14. Combine all extracted course data into a single JSON array formatted to match the CourseOfferings schema

        IMPORTANT: After extracting data from each page, always return the full set of course data you've collected so far.
        Store the extracted course data after each page and maintain this data throughout the entire process.
        Do not return an empty array when you're done.
        """
        return task

    async def run(self) -> CourseOfferings:
        task = self._build_task()
        agent = Agent(
            task=task,
            llm=self.llm,
            sensitive_data={"user": self.username, "password": self.password},
            controller=self.controller,
            max_actions_per_step=4,
        )

        result = await agent.run(max_steps=100)
        return self._process_result(result)

    def _process_result(self, result):
        """Process the structured result from the agent"""
        try:
            # Initialize an empty list to store all courses
            all_courses = []

            # Case 1: Check if we have a final_result method with structured output
            if hasattr(result, "final_result") and callable(
                getattr(result, "final_result")
            ):
                final_result = result.final_result()
                if final_result:
                    try:
                        # Try to directly parse the final result
                        return CourseOfferings.model_validate_json(final_result)
                    except Exception as e:
                        logger.warning(f"Failed to parse final result: {e}")
                        # Continue with other extraction methods

            # Case 2: Process all steps in the agent history to find extracted content
            if hasattr(result, "__iter__"):
                for step in result:
                    # Check for done action with successful result
                    if (
                        hasattr(step, "action")
                        and isinstance(step.action, dict)
                        and "done" in step.action
                    ):
                        done_data = step.action.get("done", {})
                        if (
                            isinstance(done_data, dict)
                            and done_data.get("success")
                            and "text" in done_data
                        ):
                            # Try to extract JSON from the text
                            text = done_data["text"]
                            try:
                                # Look for JSON pattern in the text
                                json_match = re.search(
                                    r'(\{.*"courses"\s*:\s*\[.*\].*\})', text, re.DOTALL
                                )
                                if json_match:
                                    json_str = json_match.group(1)
                                    courses_data = json.loads(json_str)
                                    return CourseOfferings.model_validate(courses_data)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to extract JSON from done action: {e}"
                                )

                    # Check for controller_response which contains extracted data
                    if (
                        hasattr(step, "controller_response")
                        and step.controller_response
                    ):
                        response = str(step.controller_response)

                        # Look for JSON format in code blocks
                        json_match = re.search(
                            r"```json\s*([\s\S]*?)\s*```", response, re.DOTALL
                        )
                        if json_match:
                            try:
                                json_str = json_match.group(1)
                                data = json.loads(json_str)

                                # Case: Full CourseOfferings format
                                if isinstance(data, dict) and "courses" in data:
                                    return CourseOfferings.model_validate(data)

                                # Case: Just an array of courses
                                if isinstance(data, list):
                                    all_courses.extend(data)

                            except json.JSONDecodeError as e:
                                logger.warning(f"Could not decode JSON: {e}")

                        # Try alternative pattern matching for JSON arrays
                        json_array_match = re.search(
                            r"\[\s*\{.*?\}\s*(?:,\s*\{.*?\}\s*)*\]", response, re.DOTALL
                        )
                        if json_array_match:
                            try:
                                courses_data = json.loads(json_array_match.group(0))
                                if isinstance(courses_data, list):
                                    all_courses.extend(courses_data)
                            except json.JSONDecodeError:
                                pass

            # Return the accumulated courses
            if all_courses:
                return CourseOfferings(courses=all_courses)

            logger.error("Could not extract course data from agent result")
            return None

        except Exception as e:
            logger.error(f"Error processing result: {str(e)}")
            logger.error(traceback.format_exc())
            return None
