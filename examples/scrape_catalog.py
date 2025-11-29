#!/usr/bin/env python3
"""
Example: Scrape the Duke Course Catalog

This script demonstrates how to scrape ALL courses from the Duke Course Catalog,
which is different from the class search (term-specific sections).

The catalog contains course definitions, descriptions, and attributes for all
courses that exist in the system, regardless of whether they're offered in a
specific term.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from duke_sso import DukeSSOAuth
from duke_catalog_scraper import DukeCatalogScraper

# Load environment variables
load_dotenv()


def main():
    # Configuration
    output_dir = Path(os.getenv("OUTPUT_DIR", "data"))
    output_dir.mkdir(parents=True, exist_ok=True)
    session_file = os.getenv("SESSION_FILE", "duke_session.pkl")

    # Academic careers to scrape
    # Options: "UGRD" (Undergraduate), "GRAD" (Graduate), "LAW", "MED", etc.
    acad_career = "UGRD"

    # Optional: Filter to specific subjects (None for all)
    # Example: subjects_filter = ["COMPSCI", "MATH", "PHYSICS"]
    subjects_filter = None

    # Whether to fetch detailed course info (descriptions, attributes, etc.)
    # Set to False for faster scraping with basic info only
    include_details = True

    # Delay between requests (seconds) - be respectful of the server
    delay = 0.3

    print("=" * 60)
    print("Duke Course Catalog Scraper")
    print("=" * 60)

    # Initialize authentication
    print("\nInitializing authentication...")
    auth = DukeSSOAuth(cookie_file=session_file)

    # Try cached session first
    if auth.login():
        print("Using cached DukeHub session.")
    else:
        print("No cached session found or session expired.")
        username = os.getenv("DUKE_NETID")
        password = os.getenv("DUKE_PASSWORD")

        if not username or not password:
            print("\nPlease set DUKE_NETID and DUKE_PASSWORD in your .env file.")
            print("Or run setup_auth.py first to cache a session.")
            sys.exit(1)

        print(f"\nLogging in as {username}...")
        print("Check your phone for Duo push notification...")

        if not auth.login_with_credentials(username, password):
            print("Authentication failed!")
            sys.exit(1)

        auth.save_session()
        print("Authentication successful and session cached.")

    # Initialize catalog scraper
    scraper = DukeCatalogScraper(auth)

    # Scrape all courses
    print(f"\nScraping {acad_career} catalog...")
    print(f"Include details: {include_details}")
    print(f"Request delay: {delay}s")

    if subjects_filter:
        print(f"Subjects filter: {subjects_filter}")

    print("-" * 60)

    courses = scraper.scrape_all_courses(
        institution="DUKEU",
        acad_career=acad_career,
        include_details=include_details,
        subjects_filter=subjects_filter,
        delay=delay
    )

    print("-" * 60)

    # Get summary
    summary = scraper.get_catalog_summary()
    print(f"\n📊 Summary:")
    print(f"  Total courses: {summary['total_courses']}")
    print(f"  Unique subjects: {summary['unique_subjects']}")
    print(f"  Avg courses/subject: {summary['courses_per_subject_avg']:.1f}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"catalog_{acad_career}_{timestamp}.json"
    csv_path = output_dir / f"catalog_{acad_career}_{timestamp}.csv"

    scraper.save_json(str(json_path))
    scraper.save_csv(str(csv_path))

    print(f"\n✅ Done! Output files:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")


if __name__ == "__main__":
    main()
