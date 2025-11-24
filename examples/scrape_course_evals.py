"""
Example script for scraping Duke course evaluations.

This script demonstrates how to:
1. Authenticate using Duke SSO (same as DukeHub)
2. Search for evaluations by department
3. Download evaluation report HTML files
4. Export metadata to JSON and CSV

Configuration is read from .env file (see .env.example)
Set DUKE_NETID and DUKE_PASSWORD in your .env file.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import course_eval_scraper
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from duke_sso import DukeSSOAuth
from course_eval_scraper import DukeCourseEvalScraper, DEPARTMENTS, complete_saml_flow

# Load environment variables
load_dotenv()


# ============================================================================
# CONFIGURATION
# ============================================================================

# Output directory for HTML reports and metadata
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "data")) / "course_evaluations"

# Delay between requests (seconds) to avoid overwhelming the server
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.5"))

# Departments to scrape (use department codes from DEPARTMENTS dict)
# Set to None to scrape all departments
DEPARTMENTS_TO_SCRAPE = [
    "COMPSCI",  # Computer Science
    # "MATH",     # Mathematics
    # "HISTORY",  # History
    # Add more as needed...
]

# Search parameters
# Leave empty for all terms/years
SEARCH_TERM_ID = ""  # e.g., "9169" for Fall 2023
SEARCH_YEAR = ""     # e.g., "2023"


# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    print("=" * 60)
    print("Duke Course Evaluation Scraper")
    print("=" * 60)

    # Load configuration
    session_file = os.getenv("SESSION_FILE", "duke_session.pkl")

    # Initialize Duke SSO authentication
    auth = DukeSSOAuth(cookie_file=session_file)

    # First try to use a cached session from session_file
    if auth.login():
        print("\nUsing cached Duke SSO session.")
    else:
        print("\nNo cached session found or session expired.")
        # Fall back to credential-based login with Duo push
        username = os.getenv("DUKE_NETID")
        password = os.getenv("DUKE_PASSWORD")

        if not username or not password:
            print("\nPlease set DUKE_NETID and DUKE_PASSWORD in your .env file.")
            print("Example:")
            print("  DUKE_NETID=abc123")
            print("  DUKE_PASSWORD=your_password")
            return

        duo_device_id = None  # Use default Duo device

        print(f"\nLogging in as {username}...")
        print("Check your phone for Duo push notification...")

        if not auth.login_with_credentials(username, password, duo_device_id):
            print("\nCredential-based login failed.")
            print("Check your NetID/password and approve the Duo push.")
            return

        # Cache the authenticated session for future runs
        auth.save_session()
        print("\nAuthentication successful and session cached.")

    # Now access the evaluation site to establish session
    print("\nAccessing course evaluation site...")
    eval_url = "https://eval-duke.evaluationkit.com/"
    response = auth.get(eval_url)

    if response.status_code != 200:
        print(f"ERROR: Failed to access evaluation site: {response.status_code}")
        return

    # Complete the SAML flow if needed
    print("Completing SAML authentication flow...")
    response = complete_saml_flow(auth.session, response)

    # Check final response
    if "SAML" in response.text:
        print("ERROR: SAML flow did not complete successfully.")
        print(f"Final response length: {len(response.text)} characters")
        print(f"Final response URL: {response.url}")

        # Save for debugging
        with open("debug_final_response.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved response to: debug_final_response.html")
        return
    else:
        print(f"✅ Successfully authenticated with evaluation site")
        print(f"Final URL: {response.url}")

    # Initialize scraper with the authenticated session
    scraper = DukeCourseEvalScraper(session=auth.session)

    # Check session validity
    print("\nVerifying evaluation site session...")
    if not scraper.check_session():
        print("ERROR: Session is invalid.")
        print("This shouldn't happen. Please report this issue.")
        return

    print("✅ Session is valid!\n")

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
            # Search for ALL evaluations in this department
            # Searching by area_id only ensures we get all courses, including cross-listed ones
            results = scraper.search_evaluations(
                area_id=area_id,
                course="",  # Empty = get all courses in this department
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

                # Save metadata for this department search
                scraper.save_metadata_json(
                    str(dept_output_dir / f"{dept_code}_metadata.json")
                )
                scraper.save_metadata_csv(
                    str(dept_output_dir / f"{dept_code}_metadata.csv")
                )

                # Download report HTML files
                # Reports will be automatically saved to all relevant department folders
                # based on cross-listed course codes parsed from titles
                print(f"\nDownloading {len(results)} reports (will save to cross-listed departments)...")
                saved_files = scraper.download_all_reports(
                    str(OUTPUT_DIR),  # Base directory - subdirs created automatically
                    delay=REQUEST_DELAY
                )
                print(f"Saved to {len(saved_files)} total locations")

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
