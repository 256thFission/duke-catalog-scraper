# Duke Course Catalog Scraper

A Python utility to scrape course data from DukeHub using the class search API.

## Features

- **Authentication**: Uses the `duke-sso-auth` library to maintain DukeHub sessions via Shibboleth SSO
- **Flexible Search**: Search courses by term, subject, instructor, enrollment status, and more
- **Pagination**: Automatically handles pagination to fetch all results
- **Multiple Export Formats**: Save data as JSON or CSV
- **Course Analytics**: Built-in summary statistics and filtering capabilities

## Installation

1. Clone this repository:
```bash
git clone https://github.com/256thFission/duke-catalog-scraper.git
cd duke-catalog-scraper
```

2. Install dependencies (including duke-sso-auth from GitHub):
```bash
pip install -r requirements.txt
# OR install in development mode
pip install -e .
```

The scraper uses the [duke-sso-auth](https://github.com/256thFission/duke-sso-auth) library for authentication, which will be installed automatically from GitHub.

3. (Optional) Configure with .env file:
```bash
cp .env.example .env
# Edit .env with your settings (MFA cookie, default term, etc.)
```

## Configuration

The scraper supports configuration via a `.env` file. This is optional but recommended for convenience.

### Setting up .env

Copy the example file:
```bash
cp .env.example .env
```

Edit `.env` with your preferred settings:

```bash
# Authentication - add your MFA cookie to skip manual entry
DUKE_MFA_COOKIE=your_mfa_cookie_value_here

# Course search defaults
DEFAULT_TERM=1950              # Spring 2025
REQUEST_DELAY=0.5              # Delay between requests (seconds)
MAX_PAGES=                     # Leave empty for unlimited

# File locations
SESSION_FILE=duke_session.pkl
OUTPUT_DIR=data
```

### Available Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DUKE_MFA_COOKIE` | MFA cookie for authentication | (none) |
| `DUKE_NETID` | NetID for credential-based login | (none) |
| `DUKE_PASSWORD` | Password for credential-based login | (none) |
| `DEFAULT_TERM` | Default term code for searches | `1950` |
| `MAX_PAGES` | Maximum pages to fetch (empty = unlimited) | `3` |
| `REQUEST_DELAY` | Delay between requests in seconds | `0.5` |
| `SESSION_FILE` | Session file location | `duke_session.pkl` |
| `OUTPUT_DIR` | Output directory for scraped data | `data` |

**Note**: Never commit your `.env` file to version control. It's already in `.gitignore`.

## Quick Start

### 1. Set Up Authentication

First, you need to capture your MFA cookie from DukeHub:

1. Log in to [DukeHub](https://dukehub.duke.edu) in your browser
2. Check **"Remember me"** when prompted by Duo
3. Open browser Developer Tools (F12)
4. Go to: Application/Storage → Cookies → `shib.oit.duke.edu`
5. Find the `mfa` cookie and copy its value

Then run the setup script:

```bash
python examples/setup_auth.py
```

This will save your session to `duke_session.pkl` for future use.

### 2. Run Basic Examples

```bash
python examples/basic_usage.py
```

This will:
- Search for open courses in Spring 2026
- Save results to JSON and CSV
- Display summary statistics

## Usage

### Basic Course Search

```python
from duke_sso import DukeSSOAuth
from course_scraper import DukeCourseScraper

# Authenticate
auth = DukeSSOAuth()
auth.login()

# Initialize scraper
scraper = DukeCourseScraper(auth)

# Search for courses
courses = scraper.search_courses(
    term="1950",       # Spring 2026
    enrl_stat="O",     # Open courses only
    delay=0.5          # Wait 0.5s between requests
)

# Save results
scraper.save_json("courses.json")
scraper.save_csv("courses.csv", include_meetings=True)
```

### Search Parameters

The `search_courses()` method supports many parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `term` | Term code (required) | `"1950"` (Spring 2026) |
| `institution` | Institution code | `"DUKEU"` (default) |
| `subject` | Subject/department code | `"COMPSCI"` |
| `catalog_nbr` | Course number | `"101"` |
| `enrl_stat` | Enrollment status | `"O"` (Open), `"C"` (Closed) |
| `keyword` | Search keyword | `"machine learning"` |
| `instructor_name` | Instructor last name | `"Smith"` |
| `campus` | Campus code | `"DUKE"` |
| `acad_career` | Academic career | `"UGRD"`, `"GRAD"` |
| `max_pages` | Limit number of pages | `5` (None for all) |
| `delay` | Delay between requests (seconds) | `0.5` |

### Term Codes

Duke uses 4-digit term codes:
- Format: `YCSS` where:
  - `Y` = Last digit of year
  - `C` = Century (9 for 2000s)
  - `SS` = Semester (50=Spring, 60=Summer, 70=Fall)

Examples:
- `1950` = Spring 2025 (2025 → 19, 50 = Spring)
- `1960` = Summer 2025
- `1970` = Fall 2025

## Examples

### Search by Subject

```python
# Get all Computer Science courses
courses = scraper.search_courses(
    term="1950",
    subject="COMPSCI"
)
```

### Search by Instructor

```python
# Find courses taught by Prof. Smith
courses = scraper.search_courses(
    term="1950",
    instructor_name="Smith"
)
```

### Filter Results

```python
# Search all courses, then filter for small classes
courses = scraper.search_courses(term="1950")

small_classes = [
    c for c in courses
    if c.get("class_capacity", 0) <= 20
]
```

### Get Summary Statistics

```python
summary = scraper.get_course_summary()
print(f"Total courses: {summary['total_courses']}")
print(f"Unique subjects: {summary['unique_subjects']}")
print(f"Enrollment rate: {summary['enrollment_rate']}")
```

## Output Format

### JSON Output

Courses are saved as an array of course objects:

```json
[
  {
    "class_nbr": 7370,
    "subject": "AAAS",
    "catalog_nbr": "102",
    "class_section": "01",
    "descr": "Introduction to African American Studies",
    "units": "1",
    "class_capacity": 20,
    "enrollment_total": 5,
    "enrollment_available": 15,
    "enrl_stat": "O",
    "enrl_stat_descr": "Open",
    "instructors": [
      {
        "name": "Tsitsi Jaji",
        "email": "tsitsi.jaji@duke.edu"
      }
    ],
    "meetings": [
      {
        "days": "TuTh",
        "start_time": "10.05.00.000000",
        "end_time": "11.20.00.000000",
        "bldg_cd": "7224",
        "room": "240",
        "facility_descr": "Friedl Bldg 240"
      }
    ]
  }
]
```

### CSV Output

CSV files include flattened course information. With `include_meetings=True`, each meeting time gets its own row.

## Advanced Examples

See `examples/advanced_search.py` for examples of:
- Filtering courses by meeting time
- Grouping courses by subject
- Finding small seminar-style classes
- Searching multiple subjects at once

## Project Structure

```
duke-catalog-scraper/
├── course_scraper.py      # Main scraper class
├── examples/              # Example scripts
│   ├── setup_auth.py
│   ├── basic_usage.py
│   └── advanced_search.py
├── data/                  # Output directory (created automatically)
├── requirements.txt
├── setup.py
└── README.md
```

## Security Notes

- `duke_session.pkl` contains sensitive session data - treat it like a password
- `.env` file contains sensitive credentials - never commit it to version control
- The `.gitignore` file excludes `duke_session.pkl`, `.env`, and other sensitive files by default
- MFA cookies and session files are stored locally and never transmitted except to Duke servers
- Use environment variables or `.env` for credentials instead of hardcoding them

## Best Practices

1. **Rate Limiting**: Use the `delay` parameter (default 0.5s) to avoid overwhelming the server
2. **Session Management**: Re-authenticate periodically as sessions expire
3. **Error Handling**: Wrap scraper calls in try/except blocks for production use
4. **Data Storage**: Back up scraped data as course information changes over time

## Troubleshooting

### Authentication fails
- Ensure you copied the complete MFA cookie value
- Check that you selected "Remember me" during Duo authentication
- Try logging out of DukeHub and logging back in with a fresh cookie

### No courses returned
- Verify the term code is correct
- Check that courses exist for your search criteria
- Try broadening your search (remove filters)

### Rate limiting / timeouts
- Increase the `delay` parameter
- Reduce `max_pages` to fetch fewer results at once
- Check your network connection

## License

MIT License - see LICENSE file for details

## Disclaimer

This project is for educational use only. Use it in accordance with Duke University's acceptable use policies and all applicable laws. Always respect server resources and rate limits.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Related Projects

- [duke-sso-auth](https://github.com/256thFission/duke-sso-auth) - The authentication library used by this scraper
