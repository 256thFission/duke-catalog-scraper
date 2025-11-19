"""
Download all undergraduate (UGRD) courses for a given term.

Uses the same authentication flow as the other examples and saves
all undergraduate courses to JSON and CSV files.

Configuration is read from the .env file (see .env.example).
"""

import os
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

        duo_device_id = None  # Use default Duo device

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

    # Optional limit via MAX_PAGES; default is None for all pages
    max_pages_env = os.getenv("MAX_PAGES")
    max_pages = int(max_pages_env) if max_pages_env else None

    courses = scraper.search_courses(
        term=term,
        acad_career="UGRD",   # Undergraduate courses only
        max_pages=max_pages,    # None means fetch all pages
        delay=delay,
    )

    if not courses:
        print("No courses found.")
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
