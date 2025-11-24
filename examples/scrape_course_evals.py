"""
Example script for scraping Duke course evaluations.

This script:
1. Authenticates using Duke SSO (same as DukeHub)
2. Reads all department codes from utils/area_codes.csv
3. Searches for evaluations by course code pattern (e.g., "COMPSCI-")
4. Downloads and saves to appropriate department folders

Configuration is read from .env file (see .env.example)
Set DUKE_NETID and DUKE_PASSWORD in your .env file.
"""

import os
import sys
import csv
from pathlib import Path

# Add parent directory to path to import course_eval_scraper
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from duke_sso import DukeSSOAuth
from course_eval_scraper import DukeCourseEvalScraper, complete_saml_flow

# Load environment variables
load_dotenv()


# ============================================================================
# CONFIGURATION
# ============================================================================

# Output directory for HTML reports and metadata
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "data")) / "course_evaluations"

# Delay between requests (seconds) to avoid overwhelming the server
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.5"))

# Path to area codes CSV file
AREA_CODES_CSV = Path(__file__).parent.parent / "utils" / "area_codes.csv"

# Search parameters
# Leave empty for all terms/years
SEARCH_TERM_ID = ""  # e.g., "9169" for Fall 2023
SEARCH_YEAR = ""     # e.g., "2023"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_departments_from_csv(csv_path: Path) -> list:
    """
    Load department codes from CSV file.

    Returns:
        List of department code strings (e.g., ['COMPSCI', 'MATH', 'HISTORY'])
    """
    departments = []

    if not csv_path.exists():
        print(f"ERROR: Area codes CSV not found: {csv_path}")
        return departments

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dept_code = row.get('Name', '').strip()
            # Skip empty lines and "All Areas"
            if dept_code and dept_code != "All Areas":
                departments.append(dept_code)

    return departments


# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    print("=" * 80)
    print("Duke Course Evaluation Scraper - Simplified Version")
    print("=" * 80)

    # Load all departments from CSV
    print(f"\nLoading departments from: {AREA_CODES_CSV}")
    departments = load_departments_from_csv(AREA_CODES_CSV)

    if not departments:
        print("ERROR: No departments loaded!")
        return

    print(f"Loaded {len(departments)} departments")

    # Authenticate
    session_file = os.getenv("SESSION_FILE", "duke_session.pkl")
    auth = DukeSSOAuth(cookie_file=session_file)

    if auth.login():
        print("Using cached Duke SSO session.")
    else:
        print("\nNo cached session found or session expired.")
        username = os.getenv("DUKE_NETID")
        password = os.getenv("DUKE_PASSWORD")

        if not username or not password:
            print("\nPlease set DUKE_NETID and DUKE_PASSWORD in your .env file.")
            return

        print(f"\nLogging in as {username}...")
        print("Check your phone for Duo push notification...")

        if not auth.login_with_credentials(username, password, None):
            print("\nCredential-based login failed.")
            return

        auth.save_session()
        print("Authentication successful and session cached.")

    # Access evaluation site
    print("\nAccessing course evaluation site...")
    eval_url = "https://eval-duke.evaluationkit.com/"
    response = auth.get(eval_url)

    if response.status_code != 200:
        print(f"ERROR: Failed to access evaluation site: {response.status_code}")
        return

    response = complete_saml_flow(auth.session, response)

    if "SAML" in response.text:
        print("ERROR: SAML flow did not complete successfully.")
        return

    print("✅ Successfully authenticated with evaluation site")

    # Initialize scraper
    scraper = DukeCourseEvalScraper(session=auth.session)

    if not scraper.check_session():
        print("ERROR: Session is invalid.")
        return

    print("✅ Session is valid!\n")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Scrape each department by searching for course code pattern
    total_evaluations = 0
    successful_depts = 0

    print(f"Starting to scrape {len(departments)} departments...\n")

    for i, dept_code in enumerate(departments, 1):
        print(f"[{i}/{len(departments)}] {dept_code}")

        try:
            # Search by course code pattern (e.g., "COMPSCI-")
            # This is more reliable than area_id which can be inconsistent
            search_pattern = f"{dept_code}-"

            results = scraper.search_evaluations(
                area_id="",  # Don't use area_id, search by course pattern
                course=search_pattern,
                term_id=SEARCH_TERM_ID,
                year=SEARCH_YEAR,
                delay=REQUEST_DELAY
            )

            if results:
                total_evaluations += len(results)
                successful_depts += 1
                print(f"  ✓ Found {len(results)} evaluations")

                # Save metadata
                dept_output_dir = OUTPUT_DIR / dept_code
                dept_output_dir.mkdir(parents=True, exist_ok=True)

                scraper.save_metadata_json(str(dept_output_dir / f"{dept_code}_metadata.json"))
                scraper.save_metadata_csv(str(dept_output_dir / f"{dept_code}_metadata.csv"))

                # Download reports (will save to all cross-listed departments automatically)
                saved_files = scraper.download_all_reports(str(OUTPUT_DIR), delay=REQUEST_DELAY)
                print(f"  ✓ Saved to {len(saved_files)} locations")
            else:
                print(f"  - No evaluations found")

            # Always clear for next department
            scraper.evaluations = []

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            scraper.evaluations = []
            continue

    # Final summary
    print("\n" + "=" * 80)
    print("Scraping Complete!")
    print("=" * 80)
    print(f"Total evaluations found: {total_evaluations}")
    print(f"Successful departments: {successful_depts}/{len(departments)}")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
