# Duke Course Catalog Scraper

A Python utility to scrape course data from DukeHub. Supports two modes:

1. **Class Search** (`DukeCourseScraper`) - Scrape class sections for a specific term with enrollment info
2. **Course Catalog** (`DukeCatalogScraper`) - Scrape ALL course definitions from the catalog with descriptions and attributes

## Quick Start

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

3. (Optional) Create a .env file for configuration:
```bash
cp .env.example .env
# Edit .env with your settings (default term, output dir, etc.)
```

### 1. Set Up Authentication

By default, `DukeSSOAuth` will guide you through Duke SSO login (NetID + Duo).

If you prefer non-interactive runsyou can also config mfa cookie in .env file.

### 2. Run Basic Examples

```bash
python examples/basic_usage.py
```
## Usage


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

## Output Format

Courses are represented as dictionaries containing fields like subject,
catalog number, enrollment, instructors, and meeting information.
You can export results via:
- `save_json(path)` – writes all courses to a JSON file.
- `save_csv(path, include_meetings=True)` – writes a CSV file, optionally
  flattening meetings so each meeting gets its own row.

---

## Course Catalog Scraper

The `DukeCatalogScraper` fetches **all course definitions** from the Duke Course Catalog, not just term-specific sections. This gives you access to:

- Complete course descriptions
- Course attributes (areas of knowledge, requirements satisfied)
- All subjects/departments
- Course components (lecture, lab, discussion, etc.)

### Quick Start - Catalog

```bash
python examples/scrape_catalog.py
```

### Catalog Usage

```python
from duke_sso import DukeSSOAuth
from duke_catalog_scraper import DukeCatalogScraper

auth = DukeSSOAuth()
auth.authenticate()

scraper = DukeCatalogScraper(auth)

# Scrape all undergraduate courses
courses = scraper.scrape_all_courses(
    acad_career="UGRD",      # "UGRD", "GRAD", "LAW", "MED"
    include_details=True,     # Fetch full descriptions
    delay=0.3                 # Request delay
)

# Save results
scraper.save_json("data/catalog.json")
scraper.save_csv("data/catalog.csv")
```

### Filter by Subject

```python
# Only scrape specific subjects
courses = scraper.scrape_all_courses(
    acad_career="UGRD",
    subjects_filter=["COMPSCI", "MATH", "PHYSICS"]
)
```

### Catalog API Methods

| Method | Description |
|--------|-------------|
| `get_subjects(institution, acad_career)` | Get all subjects for an academic career |
| `get_subject_courses(subject, institution, acad_career)` | Get courses for a subject |
| `get_course_details(course, institution)` | Get detailed info for a course |
| `scrape_all_courses(...)` | Scrape complete catalog |

### Catalog Course Fields

Each course includes:

| Field | Description |
|-------|-------------|
| `subject` | Subject code (e.g., "COMPSCI") |
| `catalog_nbr` | Course number (e.g., "201") |
| `crse_id` | Unique course ID |
| `descr` | Course title |
| `acad_career` | Academic career (UGRD, GRAD, etc.) |
| `typ_offr` | Typical offering (FALL, SPRING, FALL-SPRNG) |
| `details.descrlong` | Full course description |
| `details.attributes` | Course attributes (areas of knowledge) |
| `details.components` | Course components (lecture, lab, etc.) |
| `details.units_minimum/maximum` | Credit hours |

## Disclaimer

This project is for educational use only. Use it in accordance with Duke University's acceptable use policies and all applicable laws. Always respect server resources and rate limits.

## Configuration

The scraper supports configuration via a `.env` file. 

###  Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DUKE_NETID` | NetID for optional credential-based login (non-interactive) | (none) |
| `DUKE_PASSWORD` | Password for optional credential-based login | (none) |
| `DUKE_MFA_COOKIE` | Optional pre-set MFA cookie for advanced/non-interactive use | (none) |
| `DEFAULT_TERM` | Default term code for searches | `1950` |
| `MAX_PAGES` | Maximum pages to fetch (empty = unlimited) | `3` |
| `REQUEST_DELAY` | Delay between requests in seconds | `0.5` |
| `SESSION_FILE` | Session file location | `duke_session.pkl` |
| `OUTPUT_DIR` | Output directory for scraped data | `data` |

## Related Projects

- [duke-sso-auth](https://github.com/256thFission/duke-sso-auth) - The authentication library used by this scraper
