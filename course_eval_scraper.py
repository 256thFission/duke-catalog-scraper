"""
Duke Course Evaluation Scraper

Scrapes course evaluation reports from Duke's evaluation system.
"""

import json
import csv
import time
import re
import html as html_lib
import os
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import requests


def extract_department_codes_from_title(title: str) -> List[str]:
    """
    Extract all department codes from a course title.

    Handles cross-listed courses like:
    "TOPICS IN CUL. ANTHROPOLOGY.CULANTH-190S-01.AAAS-190S-01.AMES-190S-01.ICS-190S-01."

    Returns: List of unique department codes (e.g., ['CULANTH', 'AAAS', 'AMES', 'ICS'])
    """
    # Pattern to match course codes like "DEPT-###-##" or "DEPT-###S-##"
    # Department code is all uppercase letters before the dash
    pattern = r'\b([A-Z]+(?:&[A-Z]+)?)-\d+[A-Z]?-\d+\b'

    matches = re.findall(pattern, title)

    # Return unique department codes, preserving order
    seen = set()
    unique_codes = []
    for code in matches:
        if code not in seen:
            seen.add(code)
            unique_codes.append(code)

    return unique_codes


def complete_saml_flow(session: requests.Session, initial_response: requests.Response, max_redirects: int = 10) -> requests.Response:
    """
    Automatically detect and submit SAML forms until reaching the final authenticated page.

    Args:
        session: The requests session to use
        initial_response: The initial response (may be a SAML form or final page)
        max_redirects: Maximum number of SAML form submissions to prevent infinite loops

    Returns:
        The final response after completing the SAML flow
    """
    response = initial_response

    for i in range(max_redirects):
        # Check if this is a SAML form
        if "SAML" not in response.text:
            # Not a SAML form, we're done
            return response

        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        form = soup.find('form')

        if not form:
            # No form found, we're done
            return response

        # Check if it has SAML fields
        saml_response_input = form.find('input', {'name': 'SAMLResponse'})
        if not saml_response_input:
            # Not a SAML form
            return response

        # Extract form data
        action = form.get('action', '')
        if action:
            # Decode HTML entities in the action URL
            action = html_lib.unescape(action)

        form_data = {}
        for input_field in form.find_all('input'):
            name = input_field.get('name')
            value = input_field.get('value', '')
            if name:
                form_data[name] = value

        print(f"  Submitting SAML form to: {action}")

        # Submit the form
        response = session.post(action, data=form_data, allow_redirects=True)

    # If we get here, we hit the max redirects limit
    print(f"Warning: Hit max SAML redirects ({max_redirects}), returning last response")
    return response


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
    PAGINATION_API_URL = "https://eval-duke.evaluationkit.com/AppApi/Report/PublicReport"
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
        debug_flag = os.getenv("COURSE_EVAL_DEBUG_HTML", "0").lower()
        self.debug_html = debug_flag in {"1", "true", "yes", "on"}

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
            print(f"  Priming session: {self.REPORT_LANDING_URL}")
            priming_response = self.session.get(self.REPORT_LANDING_URL)

            # Complete SAML flow if needed (shouldn't happen if already authenticated)
            priming_response = complete_saml_flow(self.session, priming_response)
            print(f"  Priming complete: {len(priming_response.text)} chars")

            # Make the request
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                headers={"Referer": self.REPORT_LANDING_URL}
            )
            response.raise_for_status()

            # Debug: Check what we got
            print(f"  Search response: {len(response.text)} chars, URL: {response.url}")

            # Check if we got redirected or got a SAML form
            if "SAML" in response.text:
                print("  WARNING: Search returned SAML form, attempting to complete SAML flow...")
                response = complete_saml_flow(self.session, response)
                print(f"  After SAML: {len(response.text)} chars, URL: {response.url}")

            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')

            # Debug: Check page title
            title_elem = soup.find('title')
            if title_elem:
                print(f"  Page title: {title_elem.text.strip()}")

            # Debug: Save response for inspection (optional)
            if self.debug_html:
                debug_file = f"debug_search_response_area{area_id}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"  Saved search response to: {debug_file}")

            # Extract search results
            # Results are <li> elements with class "sr-dataitem" and id pattern "sr-{numbers}_{numbers}_{numbers}_{numbers}"
            search_results = soup.find_all('li', class_='sr-dataitem')
            print(f"Found {len(search_results)} evaluation results")

            for result in search_results:
                eval_data = self._parse_search_result(result)
                if eval_data:
                    results.append(eval_data)

            # Fetch additional pages if there are more results (initial page has 20 results max)
            print(f"  Initial page has {len(search_results)} results")
            if len(search_results) >= 20:
                print(f"  Fetching additional pages (initial page has 20+ results)...")
                page = 2
                while True:
                    if delay > 0:
                        time.sleep(delay)

                    # Build pagination API request
                    timestamp = int(time.time() * 1000)  # milliseconds
                    pagination_params = {
                        "Course": course,
                        "Instructor": instructor,
                        "TermId": term_id,
                        "Year": year,
                        "AreaId": area_id,
                        "QuestionKey": question_key,
                        "Search": "true",
                        "page": page,
                        "_": timestamp
                    }

                    # Request next page
                    print(f"  Requesting page {page}...")
                    api_response = self.session.get(
                        self.PAGINATION_API_URL,
                        params=pagination_params,
                        headers={
                            "Referer": full_url,
                            "X-Requested-With": "XMLHttpRequest",
                            "Accept": "application/json, text/javascript, */*; q=0.01"
                        }
                    )
                    api_response.raise_for_status()
                    print(f"    Response status: {api_response.status_code}, length: {len(api_response.text)}")

                    # Parse JSON response
                    try:
                        page_data = api_response.json()
                        print(f"    JSON keys: {list(page_data.keys())}")
                    except json.JSONDecodeError as e:
                        print(f"  Page {page}: Invalid JSON response - {e}")
                        print(f"    Response text preview: {api_response.text[:200]}")
                        break

                    # Check if there are more results using the hasMore flag
                    has_more = page_data.get('hasMore', False)
                    results_array = page_data.get('results', [])

                    print(f"    hasMore: {has_more}, results array length: {len(results_array)}")

                    if not results_array or not isinstance(results_array, list):
                        # Empty or invalid response
                        print(f"  Page {page}: No more results (empty or invalid response)")
                        break

                    # The results are an array of HTML strings, join them to parse
                    page_html = ''.join(results_array)

                    # Parse HTML from JSON response
                    page_soup = BeautifulSoup(page_html, 'html.parser')
                    page_results = page_soup.find_all('li', class_='sr-dataitem')

                    if not page_results:
                        print(f"  Page {page}: No more results (no results found in HTML)")
                        break

                    print(f"  Page {page}: Found {len(page_results)} results")

                    for result in page_results:
                        eval_data = self._parse_search_result(result)
                        if eval_data:
                            results.append(eval_data)

                    page += 1

            if delay > 0:
                time.sleep(delay)

        except requests.exceptions.RequestException as e:
            raise DukeCourseEvalScraperError(f"Search request failed: {e}")

        print(f"Total results collected: {len(results)}")
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
            # Extract course code (can be in <p> or <span>)
            course_code_elem = result_div.find(class_='sr-dataitem-info-code')
            course_code = course_code_elem.text.strip() if course_code_elem else ""

            # Extract course title
            title_elem = result_div.find('h2')
            title = title_elem.text.strip() if title_elem else ""

            # Extract instructor (can be in <p> or <span>)
            instructor_elem = result_div.find(class_='sr-dataitem-info-instr')
            instructor = instructor_elem.text.strip() if instructor_elem else ""

            # Extract term and area
            term_area_elem = result_div.find('p', class_='small')
            term_area_text = term_area_elem.get_text(separator='|').strip() if term_area_elem else ""
            term_area_parts = [p.strip() for p in term_area_text.split('|') if p.strip()]
            term = term_area_parts[0] if len(term_area_parts) > 0 else ""
            area = term_area_parts[1] if len(term_area_parts) > 1 else ""

            # Extract response rate (can be in various elements)
            response_elem = result_div.find(class_='sr-avg')
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

            # Extract all cross-listed department codes from the title
            department_codes = extract_department_codes_from_title(title)

            return {
                'uid': uid,
                'course_code': course_code,
                'title': title,
                'instructor': instructor,
                'term': term,
                'area': area,
                'response_rate': response_rate,
                'data_ids': data_ids,
                'department_codes': department_codes,  # List of all cross-listed departments
                'scraped_at': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error parsing search result: {e}")
            return None

    def download_report(
        self,
        eval_data: Dict[str, Any],
        base_output_dir: Path,
        delay: float = 0.5
    ) -> List[Path]:
        """
        Download the evaluation report HTML for a given evaluation.
        Saves to all relevant department folders based on cross-listed codes.

        Args:
            eval_data: Evaluation metadata dictionary with data_ids and department_codes
            base_output_dir: Base output directory (will create DEPT/reports/ subdirs)
            delay: Delay before request (default: 0.5)

        Returns:
            List of paths where the report was saved (one per department)
        """
        saved_paths = []

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

            # Generate filename
            safe_course = re.sub(r'[^\w\-]', '_', eval_data['course_code'])
            safe_instructor = re.sub(r'[^\w\-]', '_', eval_data['instructor'])
            safe_term = re.sub(r'[^\w\-]', '_', eval_data['term'])

            filename = f"{safe_course}_{safe_instructor}_{safe_term}.html"

            department_codes = eval_data.get('department_codes', [])

            # If no department codes found, use the area field as fallback
            if not department_codes:
                department_codes = [eval_data.get('area', 'UNKNOWN')]

            # Check if files already exist in all locations
            all_exist = True
            target_paths = []
            for dept_code in department_codes:
                dept_output_dir = base_output_dir / dept_code / "reports"
                target_path = dept_output_dir / filename
                target_paths.append(target_path)
                if not target_path.exists():
                    all_exist = False
            
            if all_exist and target_paths:
                print(f"  Skipping download (already exists): {filename}")
                return target_paths

            # Request the report page
            dept_str = ', '.join(department_codes) if department_codes else eval_data.get('area', 'UNKNOWN')
            print(f"Downloading report for {eval_data['course_code']} - {eval_data['instructor']} [{dept_str}]")
            response = self.session.get(report_url)
            response.raise_for_status()

            # Save to all relevant department folders
            for filepath in target_paths:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                saved_paths.append(filepath)

            # Print summary of where files were saved
            if len(saved_paths) > 1:
                print(f"  Saved to {len(saved_paths)} departments: {', '.join(department_codes)}")
            elif saved_paths:
                print(f"  Saved to: {saved_paths[0]}")

            return saved_paths

        except requests.exceptions.RequestException as e:
            print(f"  Error downloading report: {e}")
            return []

    def download_all_reports(
        self,
        output_dir: str,
        delay: float = 0.5
    ) -> List[Path]:
        """
        Download all evaluation reports from the current search results.
        Each report is saved to all relevant department folders.

        Args:
            output_dir: Base output directory (DEPT/reports/ subdirs will be created)
            delay: Delay between downloads (default: 0.5)

        Returns:
            List of all paths where files were saved
        """
        output_path = Path(output_dir)
        saved_files = []

        print(f"\nDownloading {len(self.evaluations)} evaluation reports...")

        for i, eval_data in enumerate(self.evaluations, 1):
            print(f"[{i}/{len(self.evaluations)}] ", end='')
            filepaths = self.download_report(eval_data, output_path, delay)
            saved_files.extend(filepaths)

        # Count unique evaluations (not total files saved)
        unique_reports = len(self.evaluations)
        print(f"\nDownloaded {unique_reports} reports to {len(saved_files)} locations")
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
            'department_codes',  # Cross-listed department codes
            'data-id0', 'data-id1', 'data-id2', 'data-id3',
            'scraped_at'
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for eval_data in self.evaluations:
                row = {k: eval_data.get(k, '') for k in fieldnames if k not in ['data-id0', 'data-id1', 'data-id2', 'data-id3', 'department_codes']}

                # Add data-id fields
                data_ids = eval_data.get('data_ids', {})
                row['data-id0'] = data_ids.get('data-id0', '')
                row['data-id1'] = data_ids.get('data-id1', '')
                row['data-id2'] = data_ids.get('data-id2', '')
                row['data-id3'] = data_ids.get('data-id3', '')

                # Add department codes as comma-separated string
                dept_codes = eval_data.get('department_codes', [])
                row['department_codes'] = ', '.join(dept_codes) if dept_codes else ''

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
