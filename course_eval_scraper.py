"""
Duke Course Evaluation Scraper

Scrapes course evaluation reports from Duke's evaluation system.
"""

import json
import csv
import time
import re
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import requests


class DukeCourseEvalScraperError(Exception):
    """Base exception for course evaluation scraper errors."""
    pass


class DukeCourseEvalScraper:
    """
    Scraper for Duke course evaluation data.

    This class handles querying the Duke evaluation search API,
    managing pagination, downloading evaluation reports, and exporting data.
    """

    SEARCH_URL = "https://eval-duke.evaluationkit.com/Report/Public/Results"
    SESSION_STATUS_URL = "https://eval-duke.evaluationkit.com/api2/session/status"
    REPORT_URL = "https://eval-duke.evaluationkit.com/Reports/StudentReport.aspx"
    REPORT_LANDING_URL = "https://eval-duke.evaluationkit.com/Report/Public"

    def __init__(self, cookies: Optional[Dict[str, str]] = None, session: Optional[requests.Session] = None):
        """
        Initialize the course evaluation scraper.

        Args:
            cookies: Dictionary of authentication cookies (.ASPXAUTH, CESJWT, etc.)
            session: An already authenticated requests.Session object (preferred over cookies)
        """
        if session is not None:
            # Use the provided authenticated session
            self.session = session
        else:
            # Create a new session and add cookies
            self.session = requests.Session()
            if cookies:
                self.session.cookies.update(cookies)

        # Set required headers (only if not already set)
        if 'User-Agent' not in self.session.headers:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            })

        self.evaluations = []
        self.last_session_check = time.time()

    def check_session(self) -> bool:
        """
        Check if the session is still valid by calling the session status endpoint.

        Returns:
            True if session is valid, False otherwise
        """
        try:
            response = self.session.get(self.SESSION_STATUS_URL)
            response.raise_for_status()
            data = response.json()

            remaining = data.get('remainingSeconds', 0)
            should_warn = data.get('shouldWarn', False)

            if should_warn:
                print(f"Warning: Session expires in {remaining} seconds")

            return remaining > 0
        except Exception as e:
            print(f"Session check failed: {e}")
            return False

    def keep_session_alive(self, force: bool = False):
        """
        Send a keep-alive request to prevent session timeout.
        Only sends if 30+ seconds have passed since last check, unless forced.

        Args:
            force: Force a session check regardless of time elapsed
        """
        now = time.time()
        if force or (now - self.last_session_check) > 30:
            self.check_session()
            self.last_session_check = now

    def search_evaluations(
        self,
        area_id: str,
        course: str = "",
        instructor: str = "",
        term_id: str = "",
        year: str = "",
        question_key: str = "",
        delay: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Search for course evaluations with the given criteria.

        Args:
            area_id: Area/Department ID (required, e.g., "98827" for COMPSCI)
            course: Course code or title (e.g., "compsci" or "history")
            instructor: Instructor name
            term_id: Term ID (e.g., "9169" for Fall 2023)
            year: Year (e.g., "2023")
            question_key: Question key for filtering
            delay: Delay between requests in seconds (default: 0.5)

        Returns:
            List of evaluation result dictionaries with extracted metadata
        """
        results = []

        # Build query parameters
        params = {
            "Course": course,
            "Instructor": instructor,
            "TermId": term_id,
            "Year": year,
            "AreaId": area_id,
            "QuestionKey": question_key,
            "Search": "true"
        }

        try:
            # Keep session alive
            self.keep_session_alive()

            # Log the search URL for debugging
            from urllib.parse import urlencode
            query_string = urlencode(params)
            full_url = f"{self.SEARCH_URL}?{query_string}"
            print(f"Searching evaluations for AreaId={area_id}, Course={course}...")
            print(f"Search URL: {full_url}")

            # Prime the session by visiting the reporting landing page
            # This initializes session state and refreshes cookies (YARP.Affinity, etc.)
            self.session.get(self.REPORT_LANDING_URL)

            # Make the request
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                headers={"Referer": self.REPORT_LANDING_URL}
            )
            response.raise_for_status()

            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract search results
            search_results = soup.find_all('div', id=re.compile(r'^sr-\d+'))
            print(f"Found {len(search_results)} evaluation results")

            for result in search_results:
                eval_data = self._parse_search_result(result)
                if eval_data:
                    results.append(eval_data)

            if delay > 0:
                time.sleep(delay)

        except requests.exceptions.RequestException as e:
            raise DukeCourseEvalScraperError(f"Search request failed: {e}")

        self.evaluations.extend(results)
        return results

    def _parse_search_result(self, result_div) -> Optional[Dict[str, Any]]:
        """
        Parse a single search result div to extract metadata and data-id attributes.

        Args:
            result_div: BeautifulSoup div element containing the search result

        Returns:
            Dictionary with evaluation metadata and data-id attributes
        """
        try:
            # Extract course code
            course_code_elem = result_div.find('span', class_='sr-dataitem-info-code')
            course_code = course_code_elem.text.strip() if course_code_elem else ""

            # Extract course title
            title_elem = result_div.find('h2')
            title = title_elem.text.strip() if title_elem else ""

            # Extract instructor
            instructor_elem = result_div.find('span', class_='sr-dataitem-info-instr')
            instructor = instructor_elem.text.strip() if instructor_elem else ""

            # Extract term and area
            term_area_elem = result_div.find('p', class_='small')
            term_area_text = term_area_elem.get_text(separator='|').strip() if term_area_elem else ""
            term_area_parts = [p.strip() for p in term_area_text.split('|') if p.strip()]
            term = term_area_parts[0] if len(term_area_parts) > 0 else ""
            area = term_area_parts[1] if len(term_area_parts) > 1 else ""

            # Extract response rate
            response_elem = result_div.find('span', class_='sr-avg')
            response_rate = response_elem.text.strip() if response_elem else ""

            # Extract UID from result div id
            uid = result_div.get('id', '').replace('sr-', '')

            # Find the View Report button and extract data-id attributes
            view_report_btn = result_div.find('a', class_='sr-view-report')
            data_ids = {}
            if view_report_btn:
                for i in range(4):
                    data_id_key = f'data-id{i}'
                    data_id_value = view_report_btn.get(data_id_key, '')
                    data_ids[data_id_key] = data_id_value

            return {
                'uid': uid,
                'course_code': course_code,
                'title': title,
                'instructor': instructor,
                'term': term,
                'area': area,
                'response_rate': response_rate,
                'data_ids': data_ids,
                'scraped_at': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error parsing search result: {e}")
            return None

    def download_report(
        self,
        eval_data: Dict[str, Any],
        output_dir: Path,
        delay: float = 0.5
    ) -> Optional[Path]:
        """
        Download the evaluation report HTML for a given evaluation.

        Args:
            eval_data: Evaluation metadata dictionary with data_ids
            output_dir: Directory to save the report HTML
            delay: Delay before request (default: 0.5)

        Returns:
            Path to the saved HTML file, or None if failed
        """
        try:
            # Keep session alive
            self.keep_session_alive()

            # Build report URL with comma-separated data-id values
            # URL format: Reports/StudentReport.aspx?id=id0,id1,id2,id3
            data_ids = eval_data.get('data_ids', {})
            id_param = ','.join([
                data_ids.get('data-id0', ''),
                data_ids.get('data-id1', ''),
                data_ids.get('data-id2', ''),
                data_ids.get('data-id3', ''),
            ])

            report_url = f"{self.REPORT_URL}?id={id_param}"

            if delay > 0:
                time.sleep(delay)

            # Request the report page
            print(f"Downloading report for {eval_data['course_code']} - {eval_data['instructor']}")
            response = self.session.get(report_url)
            response.raise_for_status()

            # Generate filename
            safe_course = re.sub(r'[^\w\-]', '_', eval_data['course_code'])
            safe_instructor = re.sub(r'[^\w\-]', '_', eval_data['instructor'])
            safe_term = re.sub(r'[^\w\-]', '_', eval_data['term'])

            filename = f"{safe_course}_{safe_instructor}_{safe_term}.html"
            filepath = output_dir / filename

            # Save HTML
            output_dir.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response.text)

            print(f"  Saved to: {filepath}")
            return filepath

        except requests.exceptions.RequestException as e:
            print(f"  Error downloading report: {e}")
            return None

    def download_all_reports(
        self,
        output_dir: str,
        delay: float = 0.5
    ) -> List[Path]:
        """
        Download all evaluation reports from the current search results.

        Args:
            output_dir: Directory to save report HTML files
            delay: Delay between downloads (default: 0.5)

        Returns:
            List of paths to saved HTML files
        """
        output_path = Path(output_dir)
        saved_files = []

        print(f"\nDownloading {len(self.evaluations)} evaluation reports...")

        for i, eval_data in enumerate(self.evaluations, 1):
            print(f"[{i}/{len(self.evaluations)}] ", end='')
            filepath = self.download_report(eval_data, output_path, delay)
            if filepath:
                saved_files.append(filepath)

        print(f"\nDownloaded {len(saved_files)}/{len(self.evaluations)} reports")
        return saved_files

    def save_metadata_json(self, filepath: str, pretty: bool = True) -> None:
        """
        Save evaluation metadata to a JSON file.

        Args:
            filepath: Output file path
            pretty: Whether to pretty-print the JSON (default: True)
        """
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(self.evaluations, f, indent=2, ensure_ascii=False)
            else:
                json.dump(self.evaluations, f, ensure_ascii=False)

        print(f"Saved metadata for {len(self.evaluations)} evaluations to {filepath}")

    def save_metadata_csv(self, filepath: str) -> None:
        """
        Save evaluation metadata to a CSV file.

        Args:
            filepath: Output file path
        """
        if not self.evaluations:
            print("No evaluations to save")
            return

        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            'uid', 'course_code', 'title', 'instructor',
            'term', 'area', 'response_rate',
            'data-id0', 'data-id1', 'data-id2', 'data-id3',
            'scraped_at'
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for eval_data in self.evaluations:
                row = {k: eval_data.get(k, '') for k in fieldnames if k not in ['data-id0', 'data-id1', 'data-id2', 'data-id3']}

                # Add data-id fields
                data_ids = eval_data.get('data_ids', {})
                row['data-id0'] = data_ids.get('data-id0', '')
                row['data-id1'] = data_ids.get('data-id1', '')
                row['data-id2'] = data_ids.get('data-id2', '')
                row['data-id3'] = data_ids.get('data-id3', '')

                writer.writerow(row)

        print(f"Saved metadata for {len(self.evaluations)} evaluations to {filepath}")


# Department/Area mappings
# These correspond to the AreaId values in the search form
DEPARTMENTS = {
    "DUKEU": "98278",
    "COMPSCI": "98827",
    "HISTORY": "98895",
    "MATH": "98931",
    "ENGLISH": "98847",
    # Add more departments as needed
    # Full list can be extracted from the search page HTML
}


# Term mappings
TERMS = {
    "Fall 2023": "9169",
    "Spring 2024": "9470",
    "Fall 2024": "9973",
    "Spring 2025": "10319",
    # Add more terms as needed
}


# Years
YEARS = {
    "2023": "2023",
    "2024": "2024",
    "2025": "2025",
}
