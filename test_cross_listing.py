#!/usr/bin/env python3
"""
Test script to verify cross-listed course code extraction.
"""

import re
from typing import List


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


def test_cross_listing_extraction():
    """Test the department code extraction function."""

    # Test case from user's example
    test_cases = [
        {
            "title": "TOPICS IN CUL. ANTHROPOLOGY.CULANTH-190S-01.AAAS-190S-01.AMES-190S-01.ICS-190S-01.",
            "expected": ["CULANTH", "AAAS", "AMES", "ICS"]
        },
        {
            "title": "ADVANCED TOPICS IN CPS.COMPSCI-590-01.",
            "expected": ["COMPSCI"]
        },
        {
            "title": "MACHINE LEARNING.COMPSCI-371-01.ECE-271-01.STATS-371-01.",
            "expected": ["COMPSCI", "ECE", "STATS"]
        },
        {
            "title": "Introduction to Programming.CS-101-01.",
            "expected": ["CS"]
        },
        {
            "title": "Just a title with no course codes",
            "expected": []
        }
    ]

    print("Testing cross-listed course code extraction:\n")
    print("=" * 80)

    all_passed = True
    for i, test in enumerate(test_cases, 1):
        title = test["title"]
        expected = test["expected"]

        result = extract_department_codes_from_title(title)

        passed = result == expected
        all_passed = all_passed and passed

        status = "✓ PASS" if passed else "✗ FAIL"

        print(f"\nTest {i}: {status}")
        print(f"  Title: {title}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")

    print("\n" + "=" * 80)

    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")

    return all_passed


if __name__ == "__main__":
    success = test_cross_listing_extraction()
    exit(0 if success else 1)
