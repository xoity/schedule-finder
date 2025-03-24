import os
import pandas as pd
from src.models import CourseOfferings


def get_filters_from_user() -> dict:
    def safe_input(prompt):
        val = input(prompt).strip()
        return f"[{val}]" if val else None

    return {
        "course_code": safe_input("Enter the course code to search for: "),
        "course_name": safe_input("Enter the course name to search for: "),
        "credits": safe_input("Enter the number of credits to search for: "),
        "instructor": safe_input("Enter the instructor name to search for: "),
        "room": safe_input("Enter the room to search for: "),
        "days": safe_input("Enter the days to search for, MTWR: "),
        "start_time": safe_input("Enter a minimum start time to search for: "),
        "end_time": safe_input("Enter a maximum end time to search for: "),
        "max_enrollment": safe_input("Enter the maximum enrollment to search for: "),
        "total_enrollment": safe_input("Enter the total enrollment to search for: "),
    }


def save_results(offerings: CourseOfferings):
    df = pd.DataFrame([course.model_dump() for course in offerings.courses])
    output_dir = os.getcwd()

    csv_path = os.path.join(output_dir, "results.csv")
    df.to_csv(csv_path, index=False)

    excel_path = os.path.join(output_dir, "course_offerings.xlsx")
    df.to_excel(excel_path, index=False)
