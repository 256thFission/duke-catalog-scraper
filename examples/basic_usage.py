"""
Basic Duke course scraper.

This script demonstrates how to:
1. Set up authentication with an MFA cookie
2. Search for courses
3. Save results to JSON and CSV
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from duke_sso import DukeSSOAuth
from duke_catalog_scraper.course_scraper import DukeCourseScraper
import json

# Load environment variables from .env file
load_dotenv()


def main():
    # Initialize authentication
    print("=" * 60)
    print("Duke Course Scraper - Basic Example")
    print("=" * 60)

    # Load configuration from environment
    session_file = os.getenv("SESSION_FILE", "duke_session.pkl")
    default_term = os.getenv("DEFAULT_TERM", "1950")
    max_pages = os.getenv("MAX_PAGES", "3")
    max_pages = int(max_pages) if max_pages else None
    delay = float(os.getenv("REQUEST_DELAY", "0.5"))
    output_dir = Path(os.getenv("OUTPUT_DIR", "data"))

    output_dir.mkdir(parents=True, exist_ok=True)

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
            print("Please set DUKE_NETID and DUKE_PASSWORD environment variables before running this example.")
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

    # Example 1: Search for all open courses in the default term
    print("\n" + "=" * 60)
    print(f"Example 1: Searching open courses in term {default_term}")
    print("=" * 60)

    courses = scraper.search_courses(
        term=default_term,     # From .env or default 1950 (Spring 2026)
        enrl_stat="O",         # Open courses only
        max_pages=max_pages,   # From .env or default 3
        delay=delay            # From .env or default 0.5
    )

    # Save results
    if courses:
        scraper.save_json(str(output_dir / f"courses_term{default_term}_sample.json"))
        scraper.save_csv(str(output_dir / f"courses_term{default_term}_sample.csv"), include_meetings=True)

        # Print summary
        summary = scraper.get_course_summary()
        print("\n" + "=" * 60)
        print("Course Summary")
        print("=" * 60)
        print(json.dumps(summary, indent=2))

    # Example 2: Search for specific subject
    print("\n" + "=" * 60)
    print("Example 2: Searching Computer Science courses")
    print("=" * 60)

    courses = scraper.search_courses(
        term=default_term,
        subject="COMPSCI",     # Computer Science
        max_pages=None,        # Get all pages
        delay=delay
    )

    if courses:
        scraper.save_json(str(output_dir / f"compsci_term{default_term}.json"))
        print(f"\nFound {len(courses)} Computer Science courses")

    # Example 3: Search by instructor
    print("\n" + "=" * 60)
    print("Example 3: Search by instructor name")
    print("=" * 60)

    courses = scraper.search_courses(
        term=default_term,
        instructor_name="Smith",  # Search for instructors with last name Smith
        delay=delay
    )

    if courses:
        print(f"\nFound {len(courses)} courses taught by instructors named Smith")
        # Print first few courses
        for i, course in enumerate(courses[:5], 1):
            print(f"{i}. {course['subject']} {course['catalog_nbr']}: {course['descr']}")
            for instructor in course.get('instructors', []):
                print(f"   Instructor: {instructor['name']}")

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
