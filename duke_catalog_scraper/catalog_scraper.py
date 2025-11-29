"""
Duke Course Catalog Scraper

Scrapes course information from the Duke Course Catalog API.
This scraper fetches ALL courses from the catalog (not just currently offered sections).
"""

import json
import csv
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from duke_sso import DukeSSOAuth


class DukeCatalogScraperError(Exception):
    """Base exception for catalog scraper errors."""
    pass


class DukeCatalogScraper:
    """
    Scraper for Duke Course Catalog data.

    Unlike DukeCourseScraper which fetches class sections for a specific term,
    this scraper fetches the complete course catalog with all course definitions,
    descriptions, and attributes.
    """

    BASE_URL = "https://dukehub.duke.edu/psc/CSPRD01/EMPLOYEE/SA/s/WEBLIB_HCX_CM.H_COURSE_CATALOG.FieldFormula"

    CATALOG_SUBJECTS_URL = f"{BASE_URL}.IScript_CatalogSubjects"
    SUBJECT_COURSES_URL = f"{BASE_URL}.IScript_SubjectCourses"
    COURSE_DETAILS_URL = f"{BASE_URL}.IScript_CatalogCourseDetails"

    def __init__(self, auth: DukeSSOAuth):
        """
        Initialize the catalog scraper.

        Args:
            auth: Authenticated DukeSSOAuth instance
        """
        self.auth = auth
        self.subjects: List[Dict[str, str]] = []
        self.courses: List[Dict[str, Any]] = []

    def get_subjects(
        self,
        institution: str = "DUKEU",
        acad_career: str = "UGRD"
    ) -> List[Dict[str, str]]:
        """
        Get all available subjects/departments from the catalog.

        Args:
            institution: Institution code (default: "DUKEU")
            acad_career: Academic career (e.g., "UGRD", "GRAD")

        Returns:
            List of subject dictionaries with 'subject' and 'descr' keys
        """
        params = {
            "institution": institution,
            "x_acad_career": acad_career
        }

        try:
            response = self.auth.get(self.CATALOG_SUBJECTS_URL, params=params)
            response.raise_for_status()
            data = response.json()
            self.subjects = data.get("subjects", [])
            print(f"Found {len(self.subjects)} subjects for {acad_career}")
            return self.subjects
        except Exception as e:
            raise DukeCatalogScraperError(f"Failed to fetch subjects: {e}")

    def get_subject_courses(
        self,
        subject: str,
        institution: str = "DUKEU",
        acad_career: str = "UGRD"
    ) -> List[Dict[str, Any]]:
        """
        Get all courses for a specific subject.

        Args:
            subject: Subject code (e.g., "COMPSCI", "MATH")
            institution: Institution code (default: "DUKEU")
            acad_career: Academic career (e.g., "UGRD", "GRAD")

        Returns:
            List of course dictionaries
        """
        params = {
            "institution": institution,
            "x_acad_career": acad_career,
            "subject": subject
        }

        try:
            response = self.auth.get(self.SUBJECT_COURSES_URL, params=params)
            response.raise_for_status()
            data = response.json()
            courses = data.get("courses", [])
            # Add subject to each course for clarity
            for course in courses:
                course["subject"] = subject
            return courses
        except Exception as e:
            print(f"Warning: Failed to fetch courses for {subject}: {e}")
            return []

    def get_course_details(
        self,
        course: Dict[str, Any],
        institution: str = "DUKEU"
    ) -> Dict[str, Any]:
        """
        Get detailed information for a specific course.

        Args:
            course: Course dictionary from get_subject_courses()
            institution: Institution code (default: "DUKEU")

        Returns:
            Course details dictionary
        """
        params = {
            "institution": institution,
            "course_id": course.get("crse_id", ""),
            "use_catalog_print": "Y",
            "effdt": course.get("effdt", ""),
            "x_acad_career": course.get("acad_career", "UGRD"),
            "crse_offer_nbr": course.get("crse_offer_nbr", "1"),
            "subject": course.get("subject", ""),
            "catalog_nbr": course.get("catalog_nbr", ""),
            "typ_offr": course.get("typ_offr", "")
        }

        try:
            response = self.auth.get(self.COURSE_DETAILS_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("course_details", {})
        except Exception as e:
            print(f"Warning: Failed to fetch details for {course.get('subject', '')} {course.get('catalog_nbr', '')}: {e}")
            return {}

    def scrape_all_courses(
        self,
        institution: str = "DUKEU",
        acad_career: str = "UGRD",
        include_details: bool = True,
        subjects_filter: Optional[List[str]] = None,
        delay: float = 0.3,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape all courses from the catalog.

        Args:
            institution: Institution code (default: "DUKEU")
            acad_career: Academic career (e.g., "UGRD", "GRAD")
            include_details: Whether to fetch detailed course info (slower but more complete)
            subjects_filter: Optional list of subjects to scrape (None for all)
            delay: Delay between requests in seconds (default: 0.3)
            progress_callback: Optional callback function(subject, courses_count) for progress updates

        Returns:
            List of all course dictionaries
        """
        self.courses = []

        # Get all subjects
        print(f"Fetching subjects for {acad_career}...")
        all_subjects = self.get_subjects(institution, acad_career)

        if subjects_filter:
            all_subjects = [s for s in all_subjects if s["subject"] in subjects_filter]
            print(f"Filtered to {len(all_subjects)} subjects")

        total_subjects = len(all_subjects)

        for idx, subject_info in enumerate(all_subjects, 1):
            subject = subject_info["subject"]
            subject_descr = subject_info.get("descr", "")

            print(f"[{idx}/{total_subjects}] Fetching courses for {subject} ({subject_descr})...")

            # Get courses for this subject
            subject_courses = self.get_subject_courses(subject, institution, acad_career)

            if include_details:
                # Fetch detailed info for each course
                for course in subject_courses:
                    details = self.get_course_details(course, institution)
                    course["details"] = details
                    if delay > 0:
                        time.sleep(delay)

            self.courses.extend(subject_courses)

            if progress_callback:
                progress_callback(subject, len(subject_courses))

            print(f"  Found {len(subject_courses)} courses")

            if delay > 0:
                time.sleep(delay)

        print(f"\nScraping complete. Total courses: {len(self.courses)}")
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

    def save_csv(self, filepath: str) -> None:
        """
        Save scraped courses to a CSV file.

        Args:
            filepath: Output file path
        """
        if not self.courses:
            print("No courses to save")
            return

        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Define fields to export
        base_fields = [
            "subject", "catalog_nbr", "crse_id", "descr",
            "acad_career", "crse_offer_nbr", "effdt",
            "typ_offr", "typ_offr_descr"
        ]

        detail_fields = [
            "descrlong", "units_minimum", "units_maximum",
            "grading_basis", "grading_basis_descr", "course_title"
        ]

        fieldnames = base_fields + detail_fields + ["attributes", "components"]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for course in self.courses:
                row = {k: course.get(k, "") for k in base_fields}

                # Handle catalog_nbr (strip leading spaces)
                if "catalog_nbr" in row:
                    row["catalog_nbr"] = row["catalog_nbr"].strip()

                # Extract details if available
                details = course.get("details", {})
                for field in detail_fields:
                    row[field] = details.get(field, "")

                # Flatten attributes
                attributes = details.get("attributes", [])
                attr_strs = [f"{a.get('crse_attribute', '')}:{a.get('crse_attribute_value', '')}" 
                            for a in attributes]
                row["attributes"] = "; ".join(attr_strs)

                # Flatten components
                components = details.get("components", [])
                comp_strs = [f"{c.get('component', '')}:{c.get('optional', '')}" 
                            for c in components]
                row["components"] = "; ".join(comp_strs)

                writer.writerow(row)

        print(f"Saved {len(self.courses)} courses to {filepath}")

    def get_catalog_summary(self) -> Dict[str, Any]:
        """
        Get a summary of scraped catalog courses.

        Returns:
            Dictionary with summary statistics
        """
        if not self.courses:
            return {"total_courses": 0}

        subjects = {}
        for course in self.courses:
            subject = course.get("subject", "Unknown")
            subjects[subject] = subjects.get(subject, 0) + 1

        return {
            "total_courses": len(self.courses),
            "unique_subjects": len(subjects),
            "subjects": dict(sorted(subjects.items(), key=lambda x: x[1], reverse=True)),
            "courses_per_subject_avg": len(self.courses) / len(subjects) if subjects else 0
        }
