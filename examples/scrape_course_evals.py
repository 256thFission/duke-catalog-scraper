"""
Example script for scraping Duke course evaluations.

This script demonstrates how to:
1. Set up authentication with cookies
2. Search for evaluations by department
3. Download evaluation report HTML files
4. Export metadata to JSON and CSV

Before running:
1. Update the COOKIES dictionary with your current session cookies
2. (Optional) Set the REPORT_URL_TEMPLATE after determining the correct URL pattern
3. Configure which departments to scrape in the DEPARTMENTS_TO_SCRAPE list
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import course_eval_scraper
sys.path.insert(0, str(Path(__file__).parent.parent))

from course_eval_scraper import DukeCourseEvalScraper, DEPARTMENTS


# ============================================================================
# CONFIGURATION
# ============================================================================

# Authentication cookies
# Replace these with your current cookies from eval-duke.evaluationkit.com
COOKIES = {
    '.ASPXAUTH': 'YOUR_ASPXAUTH_COOKIE_HERE',
    'ASP.NET_SessionId': 'YOUR_SESSION_ID_HERE',
    'AWSALBCORS': 'YOUR_AWSALBCORS_COOKIE_HERE',
    'CESJWT': 'YOUR_CESJWT_COOKIE_HERE',
    'YARP.Affinity': 'YOUR_YARP_AFFINITY_COOKIE_HERE',
    'LoggedinFrom': 'Shibboleth',
}

# Output directory for HTML reports and metadata
OUTPUT_DIR = Path("data/course_evaluations")

# Delay between requests (seconds) to avoid overwhelming the server
REQUEST_DELAY = 0.5

# Departments to scrape (use department codes from DEPARTMENTS dict)
# Set to None to scrape all departments
DEPARTMENTS_TO_SCRAPE = [
    "COMPSCI",  # Computer Science
    "MATH",     # Mathematics
    "HISTORY",  # History
    # Add more as needed...
]

# Search parameters
# Leave empty for all terms/years
SEARCH_TERM_ID = ""  # e.g., "9169" for Fall 2023
SEARCH_YEAR = ""     # e.g., "2023"

# Generic search term to use for each department
# This should return all courses in that department
COURSE_SEARCH_TERM = "a"  # Common letter that appears in most course codes


# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    print("=" * 60)
    print("Duke Course Evaluation Scraper")
    print("=" * 60)

    # Initialize scraper with cookies
    scraper = DukeCourseEvalScraper(cookies=COOKIES)

    # Check session validity
    print("\nChecking session validity...")
    if not scraper.check_session():
        print("ERROR: Session is invalid or expired.")
        print("Please update your cookies and try again.")
        return

    print("Session is valid!\n")

    # Determine which departments to scrape
    if DEPARTMENTS_TO_SCRAPE is None:
        departments = list(DEPARTMENTS.keys())
        print(f"Scraping ALL {len(departments)} departments")
    else:
        departments = DEPARTMENTS_TO_SCRAPE
        print(f"Scraping {len(departments)} departments: {', '.join(departments)}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Scrape each department
    total_evaluations = 0

    for i, dept_code in enumerate(departments, 1):
        if dept_code not in DEPARTMENTS:
            print(f"\n[{i}/{len(departments)}] WARNING: Unknown department code: {dept_code}")
            continue

        area_id = DEPARTMENTS[dept_code]

        print(f"\n[{i}/{len(departments)}] Scraping {dept_code} (AreaId: {area_id})")
        print("-" * 60)

        try:
            # Search for evaluations in this department
            results = scraper.search_evaluations(
                area_id=area_id,
                course=COURSE_SEARCH_TERM,
                term_id=SEARCH_TERM_ID,
                year=SEARCH_YEAR,
                delay=REQUEST_DELAY
            )

            total_evaluations += len(results)
            print(f"Found {len(results)} evaluations for {dept_code}")

            # Save department-specific metadata
            if results:
                dept_output_dir = OUTPUT_DIR / dept_code
                dept_output_dir.mkdir(parents=True, exist_ok=True)

                # Save metadata for this department
                scraper.save_metadata_json(
                    str(dept_output_dir / f"{dept_code}_metadata.json")
                )
                scraper.save_metadata_csv(
                    str(dept_output_dir / f"{dept_code}_metadata.csv")
                )

                # Download report HTML files
                print(f"\nDownloading {len(results)} reports for {dept_code}...")
                html_output_dir = dept_output_dir / "reports"
                saved_files = scraper.download_all_reports(
                    str(html_output_dir),
                    delay=REQUEST_DELAY
                )
                print(f"Saved {len(saved_files)} reports to {html_output_dir}")

                # Clear evaluations list for next department
                scraper.evaluations = []

        except Exception as e:
            print(f"ERROR scraping {dept_code}: {e}")
            continue

    # Final summary
    print("\n" + "=" * 60)
    print("Scraping Complete!")
    print("=" * 60)
    print(f"Total evaluations found: {total_evaluations}")
    print(f"Scraped {len(departments)} departments")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
