from pydantic import BaseModel, Field
from typing import List


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