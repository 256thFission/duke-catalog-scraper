# Duke Course Evaluation Scraper

A Python utility to scrape course evaluation reports from Duke's evaluation system (eval-duke.evaluationkit.com).

## Features

- **Cookie-based Authentication**: Uses Shibboleth SSO cookies for authenticated access
- **Department-wide Scraping**: Search and download evaluations for entire departments
- **Session Management**: Automatic session keep-alive to prevent timeouts
- **HTML Report Download**: Download evaluation report HTML pages
- **Metadata Export**: Export evaluation metadata to JSON and CSV formats
- **Comprehensive Department Mapping**: Support for 160+ departments across all Duke schools

## Installation

Dependencies are listed in `requirements.txt` and will be installed automatically:

```bash
pip install -r requirements.txt
```

## Authentication Setup

The evaluation system uses Shibboleth SSO (same as DukeHub). You'll need to extract cookies from an authenticated browser session.

### Getting Your Cookies

1. Log in to https://eval-duke.evaluationkit.com/ in your browser
2. Check "Remember me" when prompted by Duo (if applicable)
3. Open Browser Developer Tools (F12)
4. Go to: Application/Storage → Cookies → `eval-duke.evaluationkit.com`
5. Copy the values for these cookies:
   - `.ASPXAUTH`
   - `ASP.NET_SessionId`
   - `AWSALBCORS` (or `AWSALB`)
   - `CESJWT`
   - `YARP.Affinity`

### Cookie Format

```python
COOKIES = {
    '.ASPXAUTH': 'YOUR_LONG_AUTH_TOKEN_HERE',
    'ASP.NET_SessionId': 'wdkezcq4vu4y5jldckcut4lt',
    'AWSALBCORS': 'YOUR_AWS_LOAD_BALANCER_COOKIE',
    'CESJWT': 'YOUR_JWT_TOKEN',
    'YARP.Affinity': 'YOUR_AFFINITY_TOKEN',
    'LoggedinFrom': 'Shibboleth',
}
```

## Features Overview

The scraper can:
- ✅ Search for evaluations by department, course, instructor, term, and year
- ✅ Extract comprehensive metadata from search results
- ✅ Download evaluation report HTML files
- ✅ Export metadata to JSON and CSV formats
- ✅ Manage sessions with automatic keep-alive
- ✅ Support all 160+ Duke departments

## Usage

### Basic Example

```python
from course_eval_scraper import DukeCourseEvalScraper, DEPARTMENTS

# Set up authentication
cookies = {
    '.ASPXAUTH': 'your_auth_cookie',
    'ASP.NET_SessionId': 'your_session_id',
    # ... other cookies
}

# Initialize scraper
scraper = DukeCourseEvalScraper(cookies=cookies)

# Search for Computer Science evaluations
results = scraper.search_evaluations(
    area_id=DEPARTMENTS["COMPSCI"],
    course="",  # Empty to get all courses
    delay=0.5
)

# Save metadata
scraper.save_metadata_json("compsci_evals.json")
scraper.save_metadata_csv("compsci_evals.csv")

# Download report HTML files
scraper.download_all_reports("output/reports", delay=0.5)
```

### Scraping Multiple Departments

```python
departments_to_scrape = ["COMPSCI", "MATH", "HISTORY", "ENGLISH"]

for dept_code in departments_to_scrape:
    area_id = DEPARTMENTS[dept_code]

    print(f"Scraping {dept_code}...")
    results = scraper.search_evaluations(
        area_id=area_id,
        course="",  # Get all courses
        delay=0.5
    )

    # Save department-specific data
    scraper.save_metadata_json(f"{dept_code}_metadata.json")

    # Clear for next department
    scraper.evaluations = []
```

### Using the Example Script

See `examples/scrape_course_evals.py` for a complete example:

1. **Configure cookies** in the script
2. **Set departments** to scrape
3. **Run the script**:

```bash
python examples/scrape_course_evals.py
```

The script will:
- Search all specified departments
- Extract evaluation metadata
- Save metadata to JSON/CSV by department
- (Optional) Download report HTML files

## Search Parameters

The `search_evaluations()` method supports these parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `area_id` | Department/Area ID (required) | `"98827"` (COMPSCI) |
| `course` | Course code or search term | `"compsci"`, `"history"` |
| `instructor` | Instructor name | `"Smith"` |
| `term_id` | Term ID | `"9169"` (Fall 2023) |
| `year` | Year | `"2023"` |
| `question_key` | Question filter | `""` (all questions) |
| `delay` | Delay between requests (seconds) | `0.5` |

## Department Codes

The scraper includes mappings for 160+ departments. Common ones include:

| Code | Area ID | Department |
|------|---------|------------|
| `COMPSCI` | 98827 | Computer Science |
| `MATH` | 98862 | Mathematics |
| `HISTORY` | 98849 | History |
| `ENGLISH` | 98840 | English |
| `BIOLOGY` | 98819 | Biology |
| `CHEMISTRY` | 98823 | Chemistry |
| `ECONOMICS` | 98837 | Economics |
| `POLISCI` | 98879 | Political Science |

See `departments.json` for the complete list, or use the utility:

```bash
python utils/extract_departments.py
```

## Terms and Years

Common term codes:

| Term | Term ID |
|------|---------|
| Fall 2023 | 9169 |
| Spring 2024 | 9470 |
| Fall 2024 | 9973 |
| Spring 2025 | 10319 |

Years are specified as strings: `"2023"`, `"2024"`, `"2025"`

## Output Format

### Metadata JSON

```json
[
  {
    "uid": "154503_9169_12241518_27991780",
    "course_code": "COMPSCI-590-01",
    "title": "ADVANCED TOPICS IN CPS.COMPSCI-590-01.",
    "instructor": "Dhingra, Bhuwan",
    "term": "Fall 2023",
    "area": "COMPSCI",
    "response_rate": "9 of 24 responded (37.50%)",
    "data_ids": {
      "data-id0": "98827",
      "data-id1": "t%2fFkKASUrBF6qRsNV5Za2w%3d%3d",
      "data-id2": "%2bMkiujkig74zszAFqrOePw%3d%3d",
      "data-id3": "%2bA9xQDMSsfMFlnbB2EeqCg%3d%3d"
    },
    "scraped_at": "2025-11-18T14:30:00.123456"
  }
]
```

### Metadata CSV

| uid | course_code | instructor | term | area | response_rate | data-id0 | ... |
|-----|-------------|------------|------|------|---------------|----------|-----|
| 154503_9169... | COMPSCI-590-01 | Dhingra, Bhuwan | Fall 2023 | COMPSCI | 9 of 24... | 98827 | ... |

### Downloaded Reports

Report HTML files are saved with the naming pattern:

```
{course_code}_{instructor}_{term}.html
```

Example: `COMPSCI-590-01_Dhingra_Bhuwan_Fall_2023.html`

Each HTML file contains:
- Student evaluation responses
- Statistical summaries (mean, median, std dev)
- Response rates
- Written comments
- JSON data in a hidden input field (`hdnReportData`)

## Extracting Data from Reports

The downloaded HTML files contain evaluation data in two formats:

### 1. Rendered HTML

Parse using BeautifulSoup:

```python
from bs4 import BeautifulSoup

with open('report.html') as f:
    soup = BeautifulSoup(f, 'html.parser')

# Extract course info
course = soup.find('h3', string=re.compile('Course:')).find_next('span').text
instructor = soup.find('h3', string=re.compile('Instructor:')).find_next('span').text

# Extract questions and responses
questions = soup.find_all('div', class_='panel panel-default')
for q in questions:
    question_text = q.find('h4', class_='question-text').text
    # ... extract tables, stats, etc.
```

### 2. JSON Data

Extract from hidden input:

```python
import json
import re
from html import unescape

with open('report.html') as f:
    html = f.read()

# Find the hidden input with JSON data
match = re.search(r'id="hdnReportData" value="([^"]+)"', html)
if match:
    json_data = unescape(match.group(1))
    data = json.loads(json_data)

    # data is a list of questions with responses
    for question in data:
        print(f"Q{question['Sequence']}: {question['QuestionText']}")
        print(f"  Mean: {question['Mean']}")
        print(f"  Response Rate: {question['ResponseRate']}")
```

## Session Management

The scraper automatically manages session keep-alive:

- Checks session status before operations
- Sends keep-alive requests every 30+ seconds
- Warns if session is about to expire

To manually check session:

```python
is_valid = scraper.check_session()
if not is_valid:
    print("Session expired! Update your cookies.")
```

## Best Practices

1. **Rate Limiting**: Use `delay=0.5` or higher to avoid overwhelming the server
2. **Session Expiry**: Evaluation sessions expire after ~1 hour. Get fresh cookies if needed.
3. **Department Batching**: Process departments in batches, saving metadata after each
4. **Error Handling**: Wrap scraping in try/except blocks for production use
5. **Cookie Security**: Never commit cookies to version control

## Troubleshooting

### Authentication Fails

- Ensure all cookies are current and copied correctly
- Try logging out and logging back in to get fresh cookies
- Verify you're logged in at https://eval-duke.evaluationkit.com/

### No Results Returned

- Verify the `area_id` is correct for your department
- Check if evaluations exist for the specified term/year
- Try broadening search (remove term/year filters)

### Session Expires

- Get fresh cookies from your browser
- Sessions typically last ~1 hour
- The scraper will warn you before expiry

### Report Download Fails

- Verify the data-id values are being extracted from search results
- Check that cookies are still valid
- Ensure you have access to the evaluation reports in your browser
- Try downloading a single report manually first to verify access

## Security Notes

- Cookies contain authentication tokens - treat like passwords
- Never commit cookies to version control
- `.gitignore` is configured to exclude cookie files and session data
- Use environment variables or config files (not in git) for sensitive data

## Project Structure

```
duke-catalog-scraper/
├── course_eval_scraper.py        # Main evaluation scraper class
├── departments.json              # Department code → Area ID mapping
├── examples/
│   └── scrape_course_evals.py   # Example usage script
├── utils/
│   └── extract_departments.py   # Utility to extract department IDs
├── watermark_html.har           # Sample HAR file (for reference)
└── watermark_xhr.har            # Sample HAR file (for reference)
```

## Related Files

- **Course Catalog Scraper**: `course_scraper.py` - For scraping DukeHub course listings
- **Authentication Library**: Uses same authentication pattern as `duke-sso-auth`

## Contributing

To add missing department codes:

1. Run `python utils/extract_departments.py`
2. The script will extract all departments from a HAR file
3. Update `course_eval_scraper.py` with new codes

## License

MIT License - see LICENSE file for details

## Disclaimer

This tool is for educational and research purposes. Use in accordance with Duke University's acceptable use policies and all applicable laws. Always respect server resources and rate limits.
