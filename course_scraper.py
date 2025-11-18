"""
Duke Course Data Scraper

Scrapes course information from DukeHub class search API.
"""

import json
import csv
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from duke_sso import DukeSSOAuth


class DukeCourseScraperError(Exception):
    """Base exception for course scraper errors."""
    pass


class DukeCourseScraper:
    """
    Scraper for Duke course catalog data.

    This class handles querying the DukeHub class search API,
    managing pagination, and exporting course data.
    """

    CLASS_SEARCH_URL = (
        "https://dukehub.duke.edu/psc/CSPRD01/EMPLOYEE/SA/s/"
        "WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch"
    )

    def __init__(self, auth: DukeSSOAuth):
        """
        Initialize the course scraper.

        Args:
            auth: Authenticated DukeSSOAuth instance
        """
        self.auth = auth
        self.courses = []

    def search_courses(
        self,
        term: str,
        institution: str = "DUKEU",
        subject: str = "",
        catalog_nbr: str = "",
        enrl_stat: str = "",
        keyword: str = "",
        instructor_name: str = "",
        campus: str = "",
        acad_career: str = "",
        max_pages: Optional[int] = None,
        delay: float = 0.5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for courses with the given criteria.

        Args:
            term: Term code (e.g., "1950" for Spring 2026)
            institution: Institution code (default: "DUKEU")
            subject: Subject code (e.g., "COMPSCI")
            catalog_nbr: Catalog number (e.g., "101")
            enrl_stat: Enrollment status ("O" for Open, "C" for Closed, "" for all)
            keyword: Search keyword
            instructor_name: Instructor last name
            campus: Campus code
            acad_career: Academic career (e.g., "UGRD" for undergraduate)
            max_pages: Maximum number of pages to fetch (None for all)
            delay: Delay between requests in seconds (default: 0.5)
            **kwargs: Additional query parameters

        Returns:
            List of course dictionaries
        """
        self.courses = []
        page = 1
        total_pages = None

        print(f"Searching courses for term {term}...")

        while True:
            # Build query parameters
            params = {
                "institution": institution,
                "term": term,
                "subject": subject,
                "catalog_nbr": catalog_nbr,
                "enrl_stat": enrl_stat,
                "keyword": keyword,
                "instructor_name": instructor_name,
                "campus": campus,
                "x_acad_career": acad_career,
                "page": page,
                # Default empty parameters
                "date_from": "",
                "date_thru": "",
                "subject_like": "",
                "start_time_equals": "",
                "end_time_equals": "",
                "start_time_ge": "",
                "end_time_le": "",
                "days": "",
                "location": "",
                "acad_group": "",
                "rqmnt_designtn": "",
                "instruction_mode": "",
                "class_nbr": "",
                "acad_org": "",
                "crse_attr": "",
                "crse_attr_value": "",
                "instr_first_name": "",
                "session_code": "",
                "units": "",
                "trigger_search": "",
            }

            # Add any additional parameters
            params.update(kwargs)

            try:
                # Make the request
                response = self.auth.get(self.CLASS_SEARCH_URL, params=params)
                response.raise_for_status()

                # Parse JSON response
                data = response.json()

                # Get total pages from first response
                if total_pages is None and "pageCount" in data:
                    total_pages = data.get("pageCount", 1)
                    print(f"Found {total_pages} pages of results")

                # Extract courses
                courses = data.get("classes", [])
                if not courses:
                    print(f"No courses found on page {page}")
                    break

                print(f"Fetched page {page}/{total_pages or '?'} - {len(courses)} courses")
                self.courses.extend(courses)

                # Check if we should continue
                if max_pages and page >= max_pages:
                    print(f"Reached max pages limit ({max_pages})")
                    break

                if total_pages and page >= total_pages:
                    print("Reached last page")
                    break

                # Move to next page
                page += 1

                # Delay to avoid overwhelming the server
                if delay > 0:
                    time.sleep(delay)

            except requests.exceptions.RequestException as e:
                raise DukeCourseScraperError(f"Request failed on page {page}: {e}")
            except json.JSONDecodeError as e:
                raise DukeCourseScraperError(f"Failed to parse JSON on page {page}: {e}")

        print(f"Scraping complete. Total courses: {len(self.courses)}")
        return self.courses

    def save_json(self, filepath: str, pretty: bool = True) -> None:
        """
        Save scraped courses to a JSON file.

        Args:
            filepath: Output file path
            pretty: Whether to pretty-print the JSON (default: True)
        """
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(self.courses, f, indent=2, ensure_ascii=False)
            else:
                json.dump(self.courses, f, ensure_ascii=False)

        print(f"Saved {len(self.courses)} courses to {filepath}")

    def save_csv(self, filepath: str, include_meetings: bool = False) -> None:
        """
        Save scraped courses to a CSV file.

        Args:
            filepath: Output file path
            include_meetings: Whether to include meeting details (flattens the data)
        """
        if not self.courses:
            print("No courses to save")
            return

        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Define base fields to export
        base_fields = [
            "class_nbr", "subject", "catalog_nbr", "class_section",
            "descr", "topic", "units", "component", "class_type",
            "acad_career_descr", "instruction_mode_descr",
            "campus_descr", "location_descr",
            "session_descr", "start_dt", "end_dt",
            "enrl_stat_descr", "class_capacity", "enrollment_total",
            "enrollment_available", "wait_tot", "wait_cap",
            "grading_basis", "combined_section"
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            if include_meetings:
                # Flatten courses with meeting information
                fieldnames = base_fields + [
                    "instructor_name", "instructor_email",
                    "meeting_days", "meeting_start_time", "meeting_end_time",
                    "meeting_building", "meeting_room"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for course in self.courses:
                    # Get instructor info
                    instructors = course.get("instructors", [])
                    instructor_name = instructors[0]["name"] if instructors else ""
                    instructor_email = instructors[0]["email"] if instructors else ""

                    # Get meeting info
                    meetings = course.get("meetings", [])
                    if meetings:
                        for meeting in meetings:
                            row = {k: course.get(k, "") for k in base_fields}
                            row.update({
                                "instructor_name": instructor_name,
                                "instructor_email": instructor_email,
                                "meeting_days": meeting.get("days", ""),
                                "meeting_start_time": meeting.get("start_time", ""),
                                "meeting_end_time": meeting.get("end_time", ""),
                                "meeting_building": meeting.get("bldg_cd", ""),
                                "meeting_room": meeting.get("room", ""),
                            })
                            writer.writerow(row)
                    else:
                        # No meetings, just write course info
                        row = {k: course.get(k, "") for k in base_fields}
                        row.update({
                            "instructor_name": instructor_name,
                            "instructor_email": instructor_email,
                        })
                        writer.writerow(row)
            else:
                # Simple course list without meeting details
                fieldnames = base_fields + ["instructors"]
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for course in self.courses:
                    row = {k: course.get(k, "") for k in base_fields}
                    # Convert instructors list to string
                    instructors = course.get("instructors", [])
                    instructor_names = "; ".join([i.get("name", "") for i in instructors])
                    row["instructors"] = instructor_names
                    writer.writerow(row)

        print(f"Saved {len(self.courses)} courses to {filepath}")

    def get_course_summary(self) -> Dict[str, Any]:
        """
        Get a summary of scraped courses.

        Returns:
            Dictionary with summary statistics
        """
        if not self.courses:
            return {"total_courses": 0}

        # Collect statistics
        subjects = {}
        instructors = set()
        total_seats = 0
        total_enrolled = 0

        for course in self.courses:
            subject = course.get("subject", "Unknown")
            subjects[subject] = subjects.get(subject, 0) + 1

            for instructor in course.get("instructors", []):
                instructors.add(instructor.get("name", ""))

            total_seats += course.get("class_capacity", 0)
            total_enrolled += course.get("enrollment_total", 0)

        return {
            "total_courses": len(self.courses),
            "unique_subjects": len(subjects),
            "subjects": dict(sorted(subjects.items(), key=lambda x: x[1], reverse=True)),
            "unique_instructors": len(instructors),
            "total_seats": total_seats,
            "total_enrolled": total_enrolled,
            "enrollment_rate": f"{(total_enrolled / total_seats * 100):.1f}%" if total_seats > 0 else "N/A"
        }


# Import requests for the scraper
import requests
