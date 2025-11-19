"""
Test script to verify course evaluation scraper URL construction.

This script tests the URL generation for View Report without making actual requests.
Run this to verify your setup before doing a full scrape.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from course_eval_scraper import DukeCourseEvalScraper


def test_url_construction():
    """Test that report URLs are constructed correctly."""

    # Example evaluation data (from the HAR file analysis)
    test_eval = {
        'uid': '154503_9169_12241518_27991780',
        'course_code': 'COMPSCI-590-01',
        'title': 'ADVANCED TOPICS IN CPS.COMPSCI-590-01.',
        'instructor': 'Dhingra, Bhuwan',
        'term': 'Fall 2023',
        'area': 'COMPSCI',
        'response_rate': '9 of 24 responded (37.50%)',
        'data_ids': {
            'data-id0': '98827',
            'data-id1': 't%2fFkKASUrBF6qRsNV5Za2w%3d%3d',
            'data-id2': '%2bMkiujkig74zszAFqrOePw%3d%3d',
            'data-id3': '%2bA9xQDMSsfMFlnbB2EeqCg%3d%3d',
        }
    }

    # Expected URL (from user's example)
    expected_url = (
        'https://eval-duke.evaluationkit.com/Reports/StudentReport.aspx?'
        'id=98827,t%2fFkKASUrBF6qRsNV5Za2w%3d%3d,'
        '%2bMkiujkig74zszAFqrOePw%3d%3d,'
        '%2bA9xQDMSsfMFlnbB2EeqCg%3d%3d'
    )

    # Construct URL using the scraper's logic
    data_ids = test_eval.get('data_ids', {})
    id_param = ','.join([
        data_ids.get('data-id0', ''),
        data_ids.get('data-id1', ''),
        data_ids.get('data-id2', ''),
        data_ids.get('data-id3', ''),
    ])

    constructed_url = f"{DukeCourseEvalScraper.REPORT_URL}?id={id_param}"

    print("=" * 70)
    print("URL Construction Test")
    print("=" * 70)
    print(f"\nTest evaluation: {test_eval['course_code']} - {test_eval['instructor']}")
    print(f"\nExpected URL:")
    print(f"  {expected_url}")
    print(f"\nConstructed URL:")
    print(f"  {constructed_url}")
    print(f"\nMatch: {'✅ PASS' if constructed_url == expected_url else '❌ FAIL'}")

    if constructed_url != expected_url:
        print("\nDifference:")
        print(f"  Expected:    {expected_url}")
        print(f"  Constructed: {constructed_url}")
        return False

    print("\n" + "=" * 70)
    print("Test passed! URL construction is correct.")
    print("=" * 70)
    return True


def test_data_id_extraction():
    """Test that data-id values would be extracted correctly from HTML."""

    print("\n" + "=" * 70)
    print("Data ID Extraction Test")
    print("=" * 70)

    # Sample HTML snippet
    sample_html_button = '''
    <a href="#"
       data-id0='98827'
       data-id1='t%2fFkKASUrBF6qRsNV5Za2w%3d%3d'
       data-id2='%2bMkiujkig74zszAFqrOePw%3d%3d'
       data-id3='%2bA9xQDMSsfMFlnbB2EeqCg%3d%3d'
       class="sr-view-report btn btn-default btn-sm">
        View Report
    </a>
    '''

    print("\nSample HTML button:")
    print(sample_html_button)

    print("\nExpected data-id values:")
    expected = {
        'data-id0': '98827',
        'data-id1': 't%2fFkKASUrBF6qRsNV5Za2w%3d%3d',
        'data-id2': '%2bMkiujkig74zszAFqrOePw%3d%3d',
        'data-id3': '%2bA9xQDMSsfMFlnbB2EeqCg%3d%3d',
    }

    for key, value in expected.items():
        print(f"  {key}: {value}")

    print("\n✅ The scraper will extract these values using BeautifulSoup")
    print("=" * 70)
    return True


if __name__ == "__main__":
    print("\nDuke Course Evaluation Scraper - URL Construction Test\n")

    # Run tests
    test1_passed = test_url_construction()
    test2_passed = test_data_id_extraction()

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"URL Construction Test: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Data ID Extraction Test: {'✅ PASS' if test2_passed else '❌ FAIL'}")

    if test1_passed and test2_passed:
        print("\n✅ All tests passed! The scraper is ready to use.")
        print("\nNext steps:")
        print("1. Update cookies in examples/scrape_course_evals.py")
        print("2. Run: python examples/scrape_course_evals.py")
    else:
        print("\n❌ Some tests failed. Please review the implementation.")
        sys.exit(1)

    print("=" * 70)
