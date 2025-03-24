from browser_use import Agent, Controller
from src.models import CourseOfferings
import re
import json
import logging

logger = logging.getLogger(__name__)

class AgentRunner:
    def __init__(self, llm, username: str, password: str, filters: dict):
        self.llm = llm
        self.username = username
        self.password = password
        self.filters = filters
        self.controller = Controller(output_model=CourseOfferings)

    def _build_task(self) -> str:
        # Insert filters into the formatted task string
        task = f"""
        Follow these steps precisely:
        1. Navigate to https://cudportal.cud.ac.ae/student/login.asp
        2. Login with username and password provided
        3. Wait for the dashboard to load completely
        4. Go to "Course Registration" > "Course Offerings"
        5. Show filter, choose SEAST division, apply filter
        6. Extract ALL course info from table:
            - course_code {self.filters.get('course_code')}
            - course_name {self.filters.get('course_name')}
            - credits {self.filters.get('credits')}
            - instructor {self.filters.get('instructor')}
            - room {self.filters.get('room')}
            - days {self.filters.get('days')}
            - start_time {self.filters.get('start_time')}
            - end_time {self.filters.get('end_time')}
            - max_enrollment {self.filters.get('max_enrollment')}
            - total_enrollment {self.filters.get('total_enrollment')}
        7. Repeat for all available pages and return JSON array of all courses.
        """
        return task

    async def run(self) -> CourseOfferings:
        task = self._build_task()
        agent = Agent(
            task=task,
            llm=self.llm,
            sensitive_data={"user": self.username, "password": self.password},
            controller=self.controller,
        )

        result = await agent.run(max_steps=100)
        return self._process_result(result)

    def _process_result(self, result):
        try:
            all_courses = []

            if hasattr(result, "final_result") and result.final_result():
                return CourseOfferings.model_validate_json(result.final_result())

            if hasattr(result, "__iter__"):
                for step in result:
                    if hasattr(step, "controller_response") and step.controller_response:
                        response = str(step.controller_response)
                        json_match = re.search(r"```json\\s*(\[.*?\])\\s*```", response, re.DOTALL)
                        if json_match:
                            try:
                                data = json.loads(json_match.group(1))
                                if isinstance(data, list):
                                    all_courses.extend(data)
                            except json.JSONDecodeError as e:
                                logger.warning("Could not decode JSON: %s", e)

            return CourseOfferings(courses=all_courses) if all_courses else None

        except Exception as e:
            logger.error("Error processing result: %s", e)
            return None
