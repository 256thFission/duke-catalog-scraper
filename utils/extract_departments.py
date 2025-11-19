"""
Utility script to extract department/area IDs from the Duke evaluation search page.

Run this script after authenticating to get the complete list of departments
and their corresponding AreaId values.
"""

import re
import json
from html import unescape
import requests


def extract_departments_from_html(html: str) -> dict:
    """
    Extract department codes and IDs from the search page HTML.

    Args:
        html: HTML content of the search page

    Returns:
        Dictionary mapping department codes to area IDs
    """
    # Find the Area wm-select element
    area_select_match = re.search(
        r'<wm-select[^>]*(?:id="[^"]*Area[^"]*"|label="Area")[^>]*>(.*?)</wm-select>',
        html,
        re.DOTALL | re.IGNORECASE
    )

    if not area_select_match:
        raise ValueError("Could not find Area select element in HTML")

    area_html = area_select_match.group(1)

    # Extract all wm-option elements
    area_options = re.findall(
        r'<wm-option value="(\d+)"[^>]*>(.*?)</wm-option>',
        area_html,
        re.DOTALL
    )

    departments = {}

    for value, text in area_options:
        # Clean up the text - unescape HTML entities and remove whitespace
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace('\xa0', '').strip()  # Remove non-breaking spaces

        if value and text:
            # Handle duplicates by using a list
            if text in departments:
                # If duplicate, store as list
                if not isinstance(departments[text], list):
                    departments[text] = [departments[text]]
                departments[text].append(value)
            else:
                departments[text] = value

    return departments


def extract_departments_from_url(url: str, cookies: dict) -> dict:
    """
    Fetch the search page and extract departments.

    Args:
        url: URL of the search page
        cookies: Authentication cookies

    Returns:
        Dictionary mapping department codes to area IDs
    """
    session = requests.Session()
    session.cookies.update(cookies)

    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/145.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })

    response = session.get(url)
    response.raise_for_status()

    return extract_departments_from_html(response.text)


def print_departments_dict(departments: dict, deduplicate: bool = True):
    """
    Print departments in Python dictionary format.

    Args:
        departments: Dictionary of department codes to IDs
        deduplicate: If True, only include first occurrence of duplicate codes
    """
    print("DEPARTMENTS = {")

    # Sort by department code
    sorted_depts = sorted(departments.items())

    seen = set()
    for code, value in sorted_depts:
        # Handle duplicates
        if isinstance(value, list):
            if deduplicate:
                value = value[0]  # Take first occurrence
                if code in seen:
                    continue
            else:
                # Show all with suffixes
                for i, v in enumerate(value):
                    suffix = f"_{i+1}" if i > 0 else ""
                    print(f'    "{code}{suffix}": "{v}",')
                continue

        if deduplicate and code in seen:
            continue

        print(f'    "{code}": "{value}",')
        seen.add(code)

    print("}")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Example usage
    print("Duke Course Evaluation - Department Extractor")
    print("=" * 60)

    # Option 1: Extract from HAR file
    har_file = Path(__file__).parent.parent / "watermark_html.har"
    if har_file.exists():
        print(f"\nExtracting from HAR file: {har_file}")
        with open(har_file) as f:
            har_data = json.load(f)
            html = har_data['log']['entries'][0]['response']['content']['text']

        departments = extract_departments_from_html(html)
        print(f"\nFound {len(departments)} unique department codes\n")

        print("=" * 60)
        print("Deduplicated Department Mapping:")
        print("=" * 60)
        print_departments_dict(departments, deduplicate=True)

        # Save to JSON file
        output_file = Path(__file__).parent.parent / "departments.json"
        with open(output_file, 'w') as f:
            # Convert lists to first value for JSON
            clean_depts = {}
            for k, v in departments.items():
                clean_depts[k] = v[0] if isinstance(v, list) else v
            json.dump(clean_depts, f, indent=2)

        print(f"\n\nSaved to: {output_file}")

    else:
        print(f"HAR file not found: {har_file}")
        print("\nTo use this script:")
        print("1. Capture a HAR file from the evaluation search page")
        print("2. Save it as 'watermark_html.har' in the root directory")
        print("3. Run this script again")
