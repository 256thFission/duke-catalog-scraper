"""
Download all undergraduate (UGRD) courses for a given term.

Uses the same authentication flow as the other examples and saves
all undergraduate courses to JSON and CSV files.

Configuration is read from the .env file (see .env.example).
"""

import os
import time
from pathlib import Path
import json

from dotenv import load_dotenv
from duke_sso import DukeSSOAuth
from duke_catalog_scraper.course_scraper import DukeCourseScraper


# Load environment variables from .env file
load_dotenv()


def main():
    print("=" * 60)
    print("Duke Course Scraper - All Undergraduate Courses")
    print("=" * 60)

    # Load configuration from environment
    session_file = os.getenv("SESSION_FILE", "duke_session.pkl")
    term = os.getenv("DEFAULT_TERM", "1950")
    delay = float(os.getenv("REQUEST_DELAY", "0.5"))
    output_dir = Path(os.getenv("OUTPUT_DIR", "data"))

    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize authentication
    auth = DukeSSOAuth(cookie_file=session_file)

    # First try to use a cached session from session_file
    if auth.login():
        print("\nUsing cached DukeHub session.")
    else:
        print("\nNo cached session found or session expired.")
        # Fall back to credential-based login with Duo push (credentials from env)
        username = os.getenv("DUKE_NETID")
        password = os.getenv("DUKE_PASSWORD")

        if not username or not password:
            print("Please set DUKE_NETID and DUKE_PASSWORD environment variables before running this script.")
            return

        duo_device_id = os.getenv("DUO_DEVICE_ID") or None

        if not auth.login_with_credentials(username, password, duo_device_id):
            print("\nCredential-based login failed. Check your NetID/password and Duo approval.")
            return

        # Cache the authenticated session for future runs
        auth.save_session()
        print("\nAuthentication successful and session cached.")

    # Initialize the scraper
    scraper = DukeCourseScraper(auth)

    print("\n" + "=" * 60)
    print(f"Downloading all undergraduate (UGRD) courses for term {term}")
    print("=" * 60)

    # Step 1: Fetch all course catalog entries in one request
    courses = scraper.browse_courses(term=term, acad_career="UGRD")

    if not courses:
        print("No courses found.")
        return

    # Step 2: Fetch sections for each course
    all_sections = []
    for idx, course in enumerate(courses, 1):
        subj = course.get("subject", "")
        cat = course.get("catalog_nbr", "")
        print(f"[{idx}/{len(courses)}] Fetching sections for {subj} {cat}")

        sections = scraper.get_sections(term=term, course=course, acad_career="UGRD")
        all_sections.extend(sections)

        if delay > 0:
            time.sleep(delay)

    print(f"\nTotal sections fetched: {len(all_sections)}")
    scraper.courses = all_sections

    if not all_sections:
        print("No sections found.")
        return

    # Save results
    json_path = output_dir / f"undergrad_term{term}.json"
    csv_path = output_dir / f"undergrad_term{term}.csv"

    scraper.save_json(str(json_path))
    scraper.save_csv(str(csv_path), include_meetings=True)

    # Print summary
    summary = scraper.get_course_summary()
    print("\n" + "=" * 60)
    print("Undergraduate Course Summary")
    print("=" * 60)
    print(json.dumps(summary, indent=2))

    print("\nSaved:")
    print(f"  JSON: {json_path}")
    print(f"  CSV : {csv_path}")


if __name__ == "__main__":
    main()
