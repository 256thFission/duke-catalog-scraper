# Duke Course Evaluation Scraper

A Python utility to scrape course evaluation reports from Duke's evaluation system (eval-duke.evaluationkit.com).

## Authentication Setup

The evaluation system uses Shibboleth SSO (same as DukeHub). You'll need to extract cookies from an authenticated browser session.

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

The scraper includes mappings for 160+ departments. Common ones include:

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