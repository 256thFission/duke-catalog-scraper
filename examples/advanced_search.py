"""
Advanced search examples for the Duke course scraper.

Demonstrates more complex search queries and data filtering.
Configuration can be set via .env file (see .env.example)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from duke_sso import DukeSSOAuth
from course_scraper import DukeCourseScraper
import json
from collections import defaultdict

# Load environment variables from .env file
load_dotenv()


def example_filter_by_time(scraper, term, delay=0.5):
    """Find courses that meet at specific times."""
    print("\n" + "=" * 60)
    print("Finding afternoon courses (after 2 PM)")
    print("=" * 60)

    courses = scraper.search_courses(term=term, max_pages=5, delay=delay)

    afternoon_courses = []
    for course in courses:
        for meeting in course.get("meetings", []):
            start_time = meeting.get("start_time", "")
            # Time format is "HH.MM.SS.000000"
            if start_time:
                hour = int(start_time.split(".")[0])
                if hour >= 14:  # 2 PM or later
                    afternoon_courses.append(course)
                    break

    print(f"Found {len(afternoon_courses)} afternoon courses")
    return afternoon_courses


def example_group_by_subject(scraper, term, delay=0.5):
    """Group courses by subject and show statistics."""
    print("\n" + "=" * 60)
    print("Courses grouped by subject (with availability)")
    print("=" * 60)

    courses = scraper.search_courses(term=term, max_pages=10, delay=delay)

    by_subject = defaultdict(list)
    for course in courses:
        subject = course.get("subject", "Unknown")
        by_subject[subject].append(course)

    # Print summary for each subject
    for subject in sorted(by_subject.keys()):
        courses_in_subject = by_subject[subject]
        total_seats = sum(c.get("class_capacity", 0) for c in courses_in_subject)
        total_enrolled = sum(c.get("enrollment_total", 0) for c in courses_in_subject)
        open_courses = sum(1 for c in courses_in_subject if c.get("enrl_stat") == "O")

        print(f"\n{subject}:")
        print(f"  Total courses: {len(courses_in_subject)}")
        print(f"  Open courses: {open_courses}")
        print(f"  Total seats: {total_seats}")
        print(f"  Enrolled: {total_enrolled}")
        if total_seats > 0:
            print(f"  Fill rate: {total_enrolled/total_seats*100:.1f}%")


def example_find_small_classes(scraper, term, max_size=20, delay=0.5):
    """Find small seminar-style classes."""
    print("\n" + "=" * 60)
    print(f"Finding small classes (capacity ≤ {max_size})")
    print("=" * 60)

    courses = scraper.search_courses(term=term, max_pages=10, delay=delay)

    small_classes = [
        c for c in courses
        if c.get("class_capacity", 0) <= max_size and c.get("class_capacity", 0) > 0
    ]

    print(f"Found {len(small_classes)} small classes\n")

    # Show a few examples
    for course in small_classes[:10]:
        print(f"{course['subject']} {course['catalog_nbr']}: {course['descr']}")
        print(f"  Capacity: {course['class_capacity']}, "
              f"Enrolled: {course['enrollment_total']}, "
              f"Available: {course['enrollment_available']}")
        if course.get("instructors"):
            instructors = ", ".join(i["name"] for i in course["instructors"])
            print(f"  Instructor(s): {instructors}")
        print()

    return small_classes


def example_search_multiple_subjects(scraper, term, subjects, delay=0.5):
    """Search multiple subjects and combine results."""
    print("\n" + "=" * 60)
    print(f"Searching multiple subjects: {', '.join(subjects)}")
    print("=" * 60)

    all_courses = []
    for subject in subjects:
        print(f"\nSearching {subject}...")
        courses = scraper.search_courses(
            term=term,
            subject=subject,
            delay=delay
        )
        all_courses.extend(courses)
        print(f"  Found {len(courses)} courses")

    print(f"\nTotal: {len(all_courses)} courses across all subjects")
    return all_courses


def main():
    # Load configuration from environment
    session_file = os.getenv("SESSION_FILE", "duke_session.pkl")
    default_term = os.getenv("DEFAULT_TERM", "1950")
    delay = float(os.getenv("REQUEST_DELAY", "0.5"))
    output_dir = Path(os.getenv("OUTPUT_DIR", "data"))

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize authentication
    auth = DukeSSOAuth(cookie_file=session_file)

    # First try to use a cached session from session_file
    if auth.login():
        print("\nUsing cached DukeHub session.")
    else:
        print("\nNo cached session found")
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

    scraper = DukeCourseScraper(auth)

    # Run various examples
    example_filter_by_time(scraper, default_term, delay=delay)
    example_group_by_subject(scraper, default_term, delay=delay)
    example_find_small_classes(scraper, default_term, max_size=15, delay=delay)

    # Search multiple subjects
    subjects_of_interest = ["COMPSCI", "MATH", "PHYSICS"]
    all_stem_courses = example_search_multiple_subjects(
        scraper, default_term, subjects_of_interest, delay=delay
    )

    # Save combined results
    scraper.courses = all_stem_courses
    scraper.save_json(str(output_dir / f"stem_courses_term{default_term}.json"))

    print("\n" + "=" * 60)
    print("Advanced examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
