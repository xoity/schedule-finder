import streamlit as st
import pandas as pd
import os
import asyncio
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from src.agent_runner import AgentRunner
from src.models import CourseOfferings
from browser_use import Agent, BrowserConfig, Controller
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContextConfig
from pydantic import SecretStr
from src.utils import save_results
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure page settings
st.set_page_config(
    page_title="CUD Schedule Finder",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom CSS
st.markdown(
    """
<style>
    .main {
        padding: 2rem;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e6f7ff;
    }
    .bot-message {
        background-color: #f0f2f6;
    }
    .stButton button {
        width: 100%;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")
if "username" not in st.session_state:
    st.session_state.username = ""
if "password" not in st.session_state:
    st.session_state.password = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "courses_df" not in st.session_state:
    st.session_state.courses_df = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# Function to load saved data if exists
def load_saved_data():
    try:
        if os.path.exists("results.csv"):
            df = pd.read_csv("results.csv")
            st.session_state.courses_df = df
            return True
        return False
    except Exception as e:
        st.error(f"Error loading saved data: {e}")
        return False


# Function to run direct browser-use instructions
async def run_browser_instruction(
    instruction, username, password, api_key, use_structured_output=False
):
    try:
        # Initialize the browser with default configuration
        browser = Browser(
            config=BrowserConfig(
                new_context_config=BrowserContextConfig(
                    viewport_expansion=0,
                )
            )
        )

        # Initialize LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", api_key=SecretStr(api_key)
        )

        if use_structured_output and "extract" in instruction.lower():
            # Use structured output for extraction tasks
            controller = Controller(output_model=CourseOfferings)

            # Create agent with user instruction and controller
            agent = Agent(
                task=instruction,
                llm=llm,
                max_actions_per_step=4,
                browser=browser,
                sensitive_data={"user": username, "password": password},
                controller=controller,
            )
        else:
            # Regular agent without structured output
            agent = Agent(
                task=instruction,
                llm=llm,
                max_actions_per_step=4,
                browser=browser,
                sensitive_data={"user": username, "password": password},
            )

        # Run the agent
        result = await agent.run(max_steps=100)
        return result
    except Exception as e:
        logger.error(f"Error running browser instruction: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error running browser instruction: {str(e)}"


# Function to extract and save data from browser-use results
def extract_and_save_data_from_result(result):
    try:
        # Process result using the same approach as AgentRunner
        # Initialize an empty list to store all courses
        all_courses = []
        courses_obj = None

        # Case 1: Check if we have a final_result method with structured output
        if hasattr(result, "final_result") and callable(
            getattr(result, "final_result")
        ):
            final_result = result.final_result()
            if final_result:
                try:
                    # Try to directly parse the final result
                    courses_obj = CourseOfferings.model_validate_json(final_result)
                    if courses_obj and courses_obj.courses:
                        df = pd.DataFrame(
                            [course.model_dump() for course in courses_obj.courses]
                        )

                        # Save to CSV and Excel
                        csv_path = os.path.join(os.getcwd(), "results.csv")
                        excel_path = os.path.join(os.getcwd(), "course_offerings.xlsx")

                        df.to_csv(csv_path, index=False)
                        df.to_excel(excel_path, index=False)

                        return (
                            df,
                            f"✅ Successfully saved {len(df)} records to CSV and Excel files!",
                        )
                except Exception as e:
                    logger.warning(f"Failed to parse final result: {e}")
                    # Continue with other extraction methods

        # Case 2: Process all steps in the agent history
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
                                courses_obj = CourseOfferings.model_validate(
                                    courses_data
                                )
                                break
                            else:
                                # Try to find a JSON array directly
                                json_array_match = re.search(
                                    r"\[(.*)\]", text, re.DOTALL
                                )
                                if json_array_match:
                                    try:
                                        array_data = json.loads(
                                            f"[{json_array_match.group(1)}]"
                                        )
                                        if isinstance(array_data, list):
                                            all_courses.extend(array_data)
                                    except json.JSONDecodeError:
                                        pass
                        except Exception as e:
                            logger.warning(
                                f"Failed to extract JSON from done action: {e}"
                            )

                # Check for controller_response which contains extracted data
                if hasattr(step, "controller_response") and step.controller_response:
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
                                courses_obj = CourseOfferings.model_validate(data)
                                break

                            # Case: Just an array of courses
                            if isinstance(data, list):
                                all_courses.extend(data)

                        except json.JSONDecodeError as e:
                            logger.warning(f"Could not decode JSON: {e}")

                    # Try alternative pattern matching for JSON arrays
                    if not courses_obj and not all_courses:
                        json_array_match = re.search(
                            r"\[\s*\{.*?\}\s*(?:,\s*\{.*?\}\s*)*\]", response, re.DOTALL
                        )
                        if json_array_match:
                            try:
                                array_text = json_array_match.group(0)
                                courses_data = json.loads(array_text)
                                if isinstance(courses_data, list):
                                    all_courses.extend(courses_data)
                            except json.JSONDecodeError:
                                pass

        # Process the collected data
        if courses_obj and courses_obj.courses:
            df = pd.DataFrame([course.model_dump() for course in courses_obj.courses])
        elif all_courses:
            # Try to standardize field names for consistency
            standardized_courses = []
            for course in all_courses:
                # Map common field variations
                standardized = {}
                for key, value in course.items():
                    lower_key = key.lower()
                    if "code" in lower_key:
                        standardized["course_code"] = value
                    elif "name" in lower_key:
                        standardized["course_name"] = value
                    elif "credit" in lower_key:
                        standardized["credits"] = value
                    elif "instructor" in lower_key or "professor" in lower_key:
                        standardized["instructor"] = value
                    elif "room" in lower_key:
                        standardized["room"] = value
                    elif "day" in lower_key:
                        standardized["days"] = value
                    elif "start" in lower_key and "time" in lower_key:
                        standardized["start_time"] = value
                    elif "end" in lower_key and "time" in lower_key:
                        standardized["end_time"] = value
                    elif "max" in lower_key and "enr" in lower_key:
                        standardized["max_enrollment"] = value
                    elif "total" in lower_key and "enr" in lower_key:
                        standardized["total_enrollment"] = value
                    else:
                        standardized[key] = value
                standardized_courses.append(standardized)

            df = pd.DataFrame(standardized_courses)
        else:
            return None, "Could not extract structured data from the automation results"

        # Save the data
        csv_path = os.path.join(os.getcwd(), "results.csv")
        excel_path = os.path.join(os.getcwd(), "course_offerings.xlsx")

        df.to_csv(csv_path, index=False)
        df.to_excel(excel_path, index=False)

        return df, f"✅ Successfully saved {len(df)} records to CSV and Excel files!"

    except Exception as e:
        logger.error(f"Error processing results: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error processing results: {str(e)}"


# Sidebar
with st.sidebar:
    st.title("CUD Schedule Finder")

    # Authentication section
    st.subheader("Authentication")

    if not st.session_state.authenticated:
        with st.form("auth_form"):
            st.text_input(
                "API Key",
                value=st.session_state.api_key,
                key="input_api_key",
                type="password",
                help="Enter your Gemini API key",
            )
            st.text_input(
                "CUD Portal Username",
                value=st.session_state.username,
                key="input_username",
            )
            st.text_input("CUD Portal Password", key="input_password", type="password")

            submit_button = st.form_submit_button("Login")

            if submit_button:
                if (
                    st.session_state.input_api_key
                    and st.session_state.input_username
                    and st.session_state.input_password
                ):
                    st.session_state.api_key = st.session_state.input_api_key
                    st.session_state.username = st.session_state.input_username
                    st.session_state.password = st.session_state.input_password
                    st.session_state.authenticated = True
                    st.success("Authentication successful!")
                    st.rerun()
                else:
                    st.error("Please fill all the authentication fields")
    else:
        st.success(f"Logged in as: {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.session_state.password = ""
            st.rerun()

    # Load saved data option
    if st.session_state.authenticated:
        if st.button("Load Saved Course Data"):
            if load_saved_data():
                st.success("Course data loaded successfully!")
            else:
                st.warning("No saved course data found.")

# Main content
if not st.session_state.authenticated:
    st.title("CUD Schedule Finder")
    st.info("Please log in using the sidebar to access the application.")
else:
    # Create tabs for different functionalities
    tab1, tab2 = st.tabs(["Browser Instructions", "Course Search"])

    # Tab 1: Browser Instructions
    with tab1:
        st.header("Run Custom Browser Instructions")
        st.markdown("""
        This tool lets you directly run browser automation instructions using natural language.
        Just type your instruction below and the AI will automate the browser actions.
        
        **Examples:**
        - "Go to CUD portal, login, and check my current GPA"
        - "Navigate to the CUD library website and search for books on machine learning"
        - "Go to the CUD portal, login, navigate to Course Offerings, and extract all courses with code BCS101"
        """)

        instruction = st.text_area(
            "Enter browser automation instruction",
            placeholder="E.g., Go to CUD portal, login, and extract all courses with code BCS101",
            height=100,
        )

        col1, col2 = st.columns([1, 2])
        with col1:
            save_option = st.checkbox("Save extracted data to CSV/Excel", value=True)
        with col2:
            structured_output = st.checkbox(
                "Use structured output format (recommended for data extraction)",
                value=True,
            )

        col1, col2 = st.columns([1, 3])
        with col1:
            run_button = st.button(
                "Run Browser Automation", type="primary", use_container_width=True
            )

        if run_button and instruction:
            status_container = st.empty()
            status_container.info("Starting browser automation...")

            try:
                # Create a new event loop and run the browser instruction
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                status_container.info(
                    "Browser automation running... This may take a minute."
                )
                result = loop.run_until_complete(
                    run_browser_instruction(
                        instruction=instruction,
                        username=st.session_state.username,
                        password=st.session_state.password,
                        api_key=st.session_state.api_key,
                        use_structured_output=structured_output,
                    )
                )
                loop.close()

                # Display result
                status_container.success("Browser automation completed!")

                # Process and save results if requested
                if save_option:
                    df, message = extract_and_save_data_from_result(result)
                    if df is not None:
                        st.session_state.courses_df = df
                        st.success(message)

                        # Show a preview of the extracted data
                        st.subheader("Extracted Data Preview")
                        st.dataframe(df.head(10), use_container_width=True)
                    else:
                        st.warning(message)

                # Format and display results
                st.subheader("Execution Steps")
                if hasattr(result, "__iter__"):
                    for step_num, step in enumerate(result):
                        with st.expander(f"Step {step_num + 1}"):
                            if hasattr(step, "action"):
                                st.write(f"**Action:** {step.action}")
                            if hasattr(step, "observation"):
                                st.write(f"**Observation:** {step.observation}")
                            if hasattr(step, "thought"):
                                st.write(f"**Thought:** {step.thought}")
                            if hasattr(step, "controller_response"):
                                st.write(f"**Response:** {step.controller_response}")
                else:
                    st.write(str(result))

            except Exception as e:
                status_container.error(f"Error running browser automation: {str(e)}")
                st.error(traceback.format_exc())

    # Tab 2: Course Search
    with tab2:
        st.header("Course Search & Filter")

        if st.session_state.courses_df is not None:
            df = st.session_state.courses_df

            # Create filter columns
            col1, col2, col3 = st.columns(3)

            with col1:
                # Filter by course code
                course_codes = ["All"] + sorted(df["course_code"].unique().tolist())
                selected_code = st.selectbox("Filter by Course Code", course_codes)

            with col2:
                # Filter by instructor
                instructors = ["All"] + sorted(df["instructor"].unique().tolist())
                selected_instructor = st.selectbox("Filter by Instructor", instructors)

            with col3:
                # Filter by days
                days_options = ["All"] + sorted(df["days"].unique().tolist())
                selected_days = st.selectbox("Filter by Days", days_options)

            # Apply filters
            filtered_df = df.copy()

            if selected_code != "All":
                filtered_df = filtered_df[filtered_df["course_code"] == selected_code]

            if selected_instructor != "All":
                filtered_df = filtered_df[
                    filtered_df["instructor"] == selected_instructor
                ]

            if selected_days != "All":
                filtered_df = filtered_df[filtered_df["days"] == selected_days]

            # Display filtered data
            st.subheader(f"Results ({len(filtered_df)} courses)")
            st.dataframe(filtered_df, use_container_width=True)

            # Download options
            col1, col2 = st.columns(2)
            with col1:
                csv_data = filtered_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download as CSV",
                    data=csv_data,
                    file_name="filtered_courses.csv",
                    mime="text/csv",
                )
            with col2:
                excel_data = filtered_df.copy()
                excel_path = "filtered_courses.xlsx"
                excel_data.to_excel(excel_path, index=False)
                with open(excel_path, "rb") as f:
                    st.download_button(
                        label="Download as Excel",
                        data=f,
                        file_name=excel_path,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                # Clean up the temporary file
                if os.path.exists(excel_path):
                    os.remove(excel_path)
        else:
            st.info(
                "No course data available. Please extract course data first by using the Browser Instructions tab "
                "and running a data extraction instruction."
            )

            if st.button("Load Saved Data (if available)"):
                if load_saved_data():
                    st.success("Course data loaded successfully!")
                    st.rerun()
                else:
                    st.warning("No saved course data found.")

# Footer
st.markdown("---")
