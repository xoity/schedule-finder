# Schedule Finder

A tool to find and extract course offerings from the CUD Portal using browser automation.

## Prerequisites

- Python 3.10+ (3.13 recommended)
- Gemini API key (from Google AI Studio)

## Installation

### Linux

On Linux systems (particularly Arch-based distributions), you'll need to use a virtual environment due to the externally managed environment restrictions (PEP 668).

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

### Windows

On Windows, you can install packages directly:


# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

### macOS

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

## Setting up your API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Create a `.env` file in the project root with the following content:

``` bash
GEMINI_API_KEY=your_api_key_here
```

## Usage

### Command Line Interface

Run the command-line version:

```bash
python offerings_scraper.py
```

Follow the prompts to enter your CUD Portal credentials and search criteria. The results will be saved to `results.csv` and `course_offerings.xlsx`.

### Streamlit Web Interface (Recommended)

For a more user-friendly experience, run the Streamlit web application:

```bash
streamlit run app.py
```

This will open a web browser with the Schedule Finder interface where you can:

1. Log in with your CUD Portal credentials and Gemini API key
2. Chat with the assistant to extract course data or search for specific information
3. Browse, filter, and download course offerings data
4. Search for courses by instructor, year, or course code

For example, you can:

- Ask "Extract all course offerings from the CUD portal" to scrape the data
- Ask "Show me all courses taught by Dr. Said Elnaffar" to filter results
- Ask "What courses are available for 2nd year students?" to get year-specific offerings

## Troubleshooting

### Externally Managed Environment Error

If you see this error on Linux:

``` plaintext
error: externally-managed-environment


This means your Python installation is managed by the system package manager. Always use a virtual environment as described in the Linux installation instructions above.

### Browser Installation Issues

If you encounter issues with Playwright browser installation:

```bash
# Try running with admin privileges
sudo playwright install

# Or specify the browser
playwright install chromium
```

## License

[MIT](LICENSE)
