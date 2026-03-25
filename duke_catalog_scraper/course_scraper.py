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
        "WEBLIB_HCX_CM.H_BROWSE_CLASSES.FieldFormula.IScript_BrowseCourses"
    )

    CLASS_DETAILS_URL = (
        "https://dukehub.duke.edu/psc/CSPRD01/EMPLOYEE/SA/s/"
        "WEBLIB_HCX_CM.H_BROWSE_CLASSES.FieldFormula.IScript_BrowseSections"
    )

    def __init__(self, auth: DukeSSOAuth):
        """
        Initialize the course scraper.

        Args:
            auth: Authenticated DukeSSOAuth instance
        """
        self.auth = auth
        self.courses = []

    def get_sections(self, term: str, course: Dict[str, Any], acad_career: str = "UGRD", institution: str = "DUKEU") -> List[Dict[str, Any]]:
        """Fetch sections for a specific course via BrowseSections."""
        params = {
            "institution": institution,
            "term": term,
            "x_acad_career": acad_career,
            "subject": course.get("subject", ""),
            "catalog_nbr": course.get("catalog_nbr", ""),
            "course_id": course.get("crse_id", ""),
            "campus": "",
            "location": "",
        }

        try:
            response = self.auth.get(self.CLASS_DETAILS_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("sections", [])
        except Exception as e:
            print(f"Warning: Failed to fetch sections for {course.get('subject', '')} {course.get('catalog_nbr', '')}. Error: {e}")
            return []

    def browse_courses(
        self,
        term: str,
        institution: str = "DUKEU",
        subject: str = "",
        acad_career: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Browse all courses for a term via the DukeHub browse-classes API.

        Pass subject="" to retrieve every subject in one request.

        Args:
            term: Term code (e.g., "1970" for Fall 2026)
            institution: Institution code (default: "DUKEU")
            subject: Subject filter ("" for all)
            acad_career: Academic career (e.g., "UGRD")

        Returns:
            List of course dicts (crse_id, descr, subject, catalog_nbr)
        """
        params = {
            "institution": institution,
            "term": term,
            "acad_career": acad_career,
            "subject": subject,
        }

        print(f"Browsing courses for term {term}...")

        try:
            response = self.auth.get(self.CLASS_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
            courses = data.get("courses", [])
            print(f"Found {len(courses)} courses")
            return courses

        except requests.exceptions.RequestException as e:
            raise DukeCourseScraperError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            raise DukeCourseScraperError(f"Failed to parse JSON: {e}")

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
            "descr", "catalog_description", "topic", "units", "component", "class_type",
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
