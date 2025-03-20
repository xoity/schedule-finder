# Schedule Finder

A tool for automatically scraping and organizing course offerings from the Canadian University Dubai (CUD) portal.

## Overview

Schedule Finder uses browser automation and AI to log into the CUD student portal, navigate to the course offerings page, and extract detailed information about available courses. The data is then saved in both CSV and Excel formats for easy analysis and planning.

## Features

- Automated login to CUD student portal
- Navigation to course offerings page
- Filtering by division (currently configured for SEAST)
- Data extraction of course details including:
  - Course code and name
  - Credits
  - Instructor information
  - Room assignments
  - Schedule (days and times)
  - Enrollment statistics
- Output to both CSV and Excel formats

## Requirements

- Python 3.11 or higher (Browser Use requirement)
- Gemini API key (Google AI)
- Playwright browser automation dependencies

## Environment Setup

### Using uv (Recommended)

1. Create a virtual environment with Python 3.11 or higher:
```bash
uv venv --python 3.11
```

2. Activate the virtual environment:
```bash
# For Mac/Linux:
source .venv/bin/activate

# For Windows:
.venv\Scripts\activate
```

3. Install dependencies using uv:
```bash
uv pip install browser-use
```

4. Install Playwright browser automation:
```bash
playwright install
```

5. Install additional requirements:
```bash
uv pip install -r requirements.txt
```

### Alternative setup with pip

If you don't have uv available:

1. Create a virtual environment with Python 3.11 or higher:
```bash
python -m venv .venv
```

2. Activate the virtual environment (same activation commands as above)

3. Install dependencies:
```bash
$ pip install -r requirements.txt
$ pip install browser-use
$ playwright install
```

## API Key Setup

1. Create a `.env` file in the project root directory with your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

2. **Important**: The `.env` file contains sensitive information. It is already added to `.gitignore` to prevent accidental commits. Never share or commit your API key.

3. If you need to obtain a Gemini API key:
   - Go to the [Google AI Studio](https://ai.google.dev/)
   - Create an account or sign in
   - Navigate to the API keys section
   - Generate a new API key
   - Copy the key to your `.env` file

## Usage

Run the main script:
```bash
python offerings_scraper.py
```

You will be prompted to enter your CUD Portal username and password. The script will:
1. Log into the portal
2. Navigate to the course offerings page
3. Apply the SEAST division filter
4. Extract course data
5. Save the data to `course_offerings.csv` and `course_offerings.xlsx`

## Testing

You can test basic browser automation functionality using:
```bash
python test_navigation.py
```

This will verify that your setup can perform simple browser automation tasks.

## Troubleshooting

If you encounter errors related to browser automation:

1. Ensure you're using Python 3.11 or higher:
```bash
python --version
```

2. Verify Playwright is installed correctly:
```bash
playwright install --help
```

3. Check your Gemini API key is properly set in the `.env` file

4. Make sure all dependencies are installed:
```bash
pip list | grep browser-use
pip list | grep pandas
```

5. If experiencing issues with missing browsers:
```bash
playwright install
```

## License

[MIT License](LICENSE)
