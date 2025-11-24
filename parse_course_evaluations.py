#!/usr/bin/env python3
"""
Parse Duke Course Evaluation HTML files into CSV format.
Extracts course info, questions, responses, and statistics.
"""

import csv
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, List, Optional


# Junk text to filter out from free text responses
JUNK_PATTERNS = [
    'sitemap', 'terms & conditions', 'privacy policy', 'accessibility policy',
    'terms of use', 'cookie policy', 'copyright', 'all rights reserved',
    'write-in responses:', 'response option', 'weight', 'frequency', 'percentage'
]


def is_junk_text(text: str) -> bool:
    """Check if text is likely junk (footer links, navigation, etc)."""
    text_lower = text.lower().strip()

    # Too short
    if len(text_lower) < 10:
        return True

    # Matches junk patterns
    for pattern in JUNK_PATTERNS:
        if pattern in text_lower:
            return True

    # Only contains common navigation words
    if text_lower in ['home', 'about', 'contact', 'help', 'login', 'logout']:
        return True

    return False


class CourseEvaluationParser:
    """Parser for Duke Course Evaluation HTML files."""

    def __init__(self, html_path: str):
        """Initialize parser with HTML file path."""
        self.html_path = html_path
        with open(html_path, 'r', encoding='utf-8') as f:
            self.soup = BeautifulSoup(f.read(), 'html.parser')

        self.course_info = self._extract_course_info()
        self.questions = self._extract_questions()

    def _extract_course_info(self) -> Dict[str, str]:
        """Extract course metadata (course code, instructor, semester)."""
        info = {
            'course': '',
            'instructor': '',
            'semester': '',
            'filename': Path(self.html_path).name
        }

        # Extract semester
        semester_h2 = self.soup.find('h2')
        if semester_h2:
            info['semester'] = semester_h2.get_text(strip=True)

        # Extract course
        course_h3 = self.soup.find('h3', string=re.compile(r'Course:'))
        if course_h3:
            course_span = course_h3.find_next_sibling('span')
            if course_span:
                info['course'] = course_span.get_text(strip=True)

        # Extract instructor
        instructor_h3 = self.soup.find('h3', string=re.compile(r'Instructor:'))
        if instructor_h3:
            instructor_span = instructor_h3.find_next_sibling('span')
            if instructor_span:
                info['instructor'] = instructor_span.get_text(strip=True)

        return info

    def _extract_questions(self) -> List[Dict]:
        """Extract all questions and their associated data."""
        questions = []

        # Find all h4 headings (questions)
        h4_elements = self.soup.find_all('h4')

        for i, h4 in enumerate(h4_elements):
            question_text = h4.get_text(strip=True)

            # Skip if not a numbered question
            if not re.match(r'^\d+\s*-', question_text):
                continue

            # Extract question number
            match = re.match(r'^(\d+)\s*-\s*(.+)', question_text)
            if not match:
                continue

            question_num = match.group(1)
            question_full_text = match.group(2)

            question_data = {
                'number': question_num,
                'text': question_full_text,
                'responses': [],
                'statistics': {},
                'free_text': []
            }

            # Find the next h4 to know when to stop
            next_h4 = None
            for j in range(i + 1, len(h4_elements)):
                next_text = h4_elements[j].get_text(strip=True)
                if re.match(r'^\d+\s*-', next_text):
                    next_h4 = h4_elements[j]
                    break

            # Get all following elements until the next h4
            following_elements = h4.find_all_next()

            for elem in following_elements:
                # Stop if we reached the next question
                if next_h4 and elem == next_h4:
                    break

                if elem.name == 'table':
                    self._parse_table(elem, question_data)

                elif elem.name == 'li':
                    # Free text responses are in list items
                    li_text = elem.get_text(strip=True)
                    # Filter out junk and check minimum length
                    if li_text and len(li_text) >= 10 and not is_junk_text(li_text):
                        question_data['free_text'].append(li_text)

                elif elem.name == 'p':
                    # Check if it's a free text response
                    p_text = elem.get_text(strip=True)
                    # Filter out junk
                    if p_text and len(p_text) >= 15 and not is_junk_text(p_text):
                        question_data['free_text'].append(p_text)

            questions.append(question_data)

        return questions

    def _parse_table(self, table, question_data: Dict):
        """Parse a table and extract response data or statistics."""
        rows = table.find_all('tr')
        if not rows:
            return

        # Check first row to determine table type
        headers = [cell.get_text(strip=True) for cell in rows[0].find_all(['th', 'td'])]

        # Response distribution table
        if 'Response Option' in headers or 'Weight' in headers:
            for row in rows[1:]:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 4:
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    question_data['responses'].append({
                        'option': cell_texts[0],
                        'weight': cell_texts[1],
                        'frequency': cell_texts[2],
                        'percentage': cell_texts[3]
                    })

        # Statistics table
        elif 'Response Rate' in headers or 'Mean' in headers:
            if len(rows) > 1:
                cells = rows[1].find_all(['th', 'td'])
                cell_texts = [cell.get_text(strip=True) for cell in cells]

                # Parse based on what we find
                for i, header in enumerate(headers):
                    if i < len(cell_texts):
                        question_data['statistics'][header] = cell_texts[i]

        # Hours table (for question about time spent)
        elif 'Hours' in headers or 'Range' in headers:
            for row in rows[1:]:
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    question_data['responses'].append({
                        'option': cell_texts[0],
                        'frequency': cell_texts[1] if len(cell_texts) > 1 else '',
                        'percentage': cell_texts[2] if len(cell_texts) > 2 else ''
                    })

    def get_response_rows(self) -> List[Dict]:
        """Get all response-level rows for this course."""
        rows = []
        for question in self.questions:
            base_row = {
                'filename': self.course_info['filename'],
                'semester': self.course_info['semester'],
                'course': self.course_info['course'],
                'instructor': self.course_info['instructor'],
                'question_number': question['number'],
                'question_text': question['text'],
                'response_rate': question['statistics'].get('Response Rate', ''),
                'mean': question['statistics'].get('Mean', ''),
                'std': question['statistics'].get('STD', ''),
                'median': question['statistics'].get('Median', '')
            }

            if question['responses']:
                # One row per response option
                for response in question['responses']:
                    row = base_row.copy()
                    row['response_option'] = response.get('option', '')
                    row['weight'] = response.get('weight', '')
                    row['frequency'] = response.get('frequency', '')
                    row['percentage'] = response.get('percentage', '')
                    rows.append(row)
            else:
                # One row even if no responses (for free text questions)
                rows.append(base_row)

        return rows

    def get_question_rows(self) -> List[Dict]:
        """Get all question-level rows for this course."""
        rows = []
        for question in self.questions:
            # Create response distribution string
            response_dist = '; '.join([
                f"{r.get('option', '')}: {r.get('frequency', '')} ({r.get('percentage', '')})"
                for r in question['responses']
            ])

            # Calculate total responses
            total = sum([
                int(r.get('frequency', '0'))
                for r in question['responses']
                if r.get('frequency', '').isdigit()
            ])

            row = {
                'filename': self.course_info['filename'],
                'semester': self.course_info['semester'],
                'course': self.course_info['course'],
                'instructor': self.course_info['instructor'],
                'question_number': question['number'],
                'question_text': question['text'],
                'response_rate': question['statistics'].get('Response Rate', ''),
                'mean': question['statistics'].get('Mean', ''),
                'std': question['statistics'].get('STD', ''),
                'median': question['statistics'].get('Median', ''),
                'total_responses': str(total) if total > 0 else '',
                'response_distribution': response_dist
            }
            rows.append(row)

        return rows

    def get_free_text_rows(self) -> List[Dict]:
        """Get all free text response rows for this course."""
        rows = []
        for question in self.questions:
            if question['free_text']:
                for response_text in question['free_text']:
                    row = {
                        'filename': self.course_info['filename'],
                        'semester': self.course_info['semester'],
                        'course': self.course_info['course'],
                        'instructor': self.course_info['instructor'],
                        'question_number': question['number'],
                        'question_text': question['text'],
                        'response_text': response_text
                    }
                    rows.append(row)

        return rows


def find_html_files(base_dir: Path) -> List[Path]:
    """
    Find all course evaluation HTML files in the directory structure.
    Expected structure: data/course_evaluations/DEPARTMENT/reports/*.html
    """
    html_files = []

    # Look for the pattern: base_dir/**/reports/*.html
    reports_dirs = base_dir.glob('**/reports')

    for reports_dir in reports_dirs:
        for html_file in reports_dir.glob('*.html'):
            html_files.append(html_file)

    return sorted(html_files)


def main():
    """Main function to parse evaluation files."""
    # Default to 'data' directory if not specified
    if len(sys.argv) < 2:
        # Try to use 'data' directory by default
        if Path('data').exists() and Path('data').is_dir():
            target_dir = Path('data')
            print("No directory specified, using default: data/")
        else:
            print("Usage: python parse_course_evaluations.py [directory]")
            print("\nExample:")
            print("  python parse_course_evaluations.py data")
            print("  python parse_course_evaluations.py      # defaults to 'data' if it exists")
            print("\nExpected structure:")
            print("  data/course_evaluations/DEPARTMENT/reports/*.html")
            print("\nThis will:")
            print("  - Recursively find all HTML files in <dir>/**/reports/*.html")
            print("  - Parse all course evaluations from all departments")
            print("  - Generate three CSV files per department in their respective folders:")
            print("    • evaluations_responses.csv (detailed response-level data)")
            print("    • evaluations_questions.csv (summary question-level data)")
            print("    • evaluations_free_text.csv (free text responses)")
            sys.exit(1)
    else:
        target_dir = Path(sys.argv[1])

    if not target_dir.exists():
        print(f"Error: Directory not found: {target_dir}")
        sys.exit(1)

    if not target_dir.is_dir():
        print(f"Error: Not a directory: {target_dir}")
        sys.exit(1)

    # Find all HTML files
    print(f"Searching for HTML files in {target_dir}...")
    print(f"Looking for pattern: {target_dir}/**/reports/*.html\n")
    html_files = find_html_files(target_dir)

    if not html_files:
        print(f"Error: No HTML files found!")
        print(f"\nSearched for: {target_dir}/**/reports/*.html")
        print(f"\nPlease ensure your data follows this structure:")
        print(f"  {target_dir}/")
        print(f"  └── course_evaluations/")
        print(f"      ├── COMPSCI/")
        print(f"      │   └── reports/")
        print(f"      │       ├── COMPSCI-512-01_Maggs_Bruce_Fall_2024.html")
        print(f"      │       └── ...")
        print(f"      ├── MATH/")
        print(f"      │   └── reports/")
        print(f"      │       └── ...")
        print(f"      └── ...")
        sys.exit(1)

    # Group files by department
    dept_files = {}
    for html_file in html_files:
        # Get department name from path (parent of parent of file)
        dept = html_file.parent.parent.name
        if dept not in dept_files:
            dept_files[dept] = []
        dept_files[dept].append(html_file)

    print(f"Found {len(html_files)} HTML files across {len(dept_files)} departments:")
    for dept, files in sorted(dept_files.items()):
        print(f"  • {dept}: {len(files)} courses")
    print()

    # Process each department separately
    total_success = 0
    total_errors = 0

    for dept_name, dept_html_files in sorted(dept_files.items()):
        print(f"\n{'='*70}")
        print(f"Processing {dept_name} ({len(dept_html_files)} courses)")
        print(f"{'='*70}")

        dept_response_rows = []
        dept_question_rows = []
        dept_free_text_rows = []
        dept_errors = []

        # Parse all files in this department
        for i, html_file in enumerate(dept_html_files, 1):
            try:
                print(f"[{i}/{len(dept_html_files)}] {html_file.name}")
                parser = CourseEvaluationParser(str(html_file))

                # Collect rows
                response_rows = parser.get_response_rows()
                question_rows = parser.get_question_rows()
                free_text_rows = parser.get_free_text_rows()

                dept_response_rows.extend(response_rows)
                dept_question_rows.extend(question_rows)
                dept_free_text_rows.extend(free_text_rows)

                # Show concise summary
                course_short = parser.course_info['course'].split(':')[0] if ':' in parser.course_info['course'] else parser.course_info['course']
                instructor_short = parser.course_info['instructor'].split(',')[0] if ',' in parser.course_info['instructor'] else parser.course_info['instructor']
                print(f"  ✓ {course_short} - {instructor_short} ({len(parser.questions)} Qs, {len(free_text_rows)} comments)")

            except Exception as e:
                error_msg = f"{html_file.name}: {str(e)}"
                dept_errors.append(error_msg)
                print(f"  ✗ Error: {str(e)}")

        # Write CSV files for this department
        if not dept_html_files:
            continue
            
        dept_dir = dept_html_files[0].parent.parent  # Get department directory

        print(f"\nWriting CSV files to {dept_dir}/...")

        # Response-level CSV
        responses_csv = dept_dir / 'evaluations_responses.csv'
        with open(responses_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'filename', 'semester', 'course', 'instructor',
                'question_number', 'question_text',
                'response_option', 'weight', 'frequency', 'percentage',
                'response_rate', 'mean', 'std', 'median'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dept_response_rows)

        print(f"  ✓ evaluations_responses.csv ({len(dept_response_rows)} rows)")

        # Question-level CSV
        questions_csv = dept_dir / 'evaluations_questions.csv'
        with open(questions_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'filename', 'semester', 'course', 'instructor',
                'question_number', 'question_text',
                'response_rate', 'mean', 'std', 'median',
                'total_responses', 'response_distribution'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dept_question_rows)

        print(f"  ✓ evaluations_questions.csv ({len(dept_question_rows)} rows)")

        # Free text CSV
        free_text_csv = dept_dir / 'evaluations_free_text.csv'
        with open(free_text_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'filename', 'semester', 'course', 'instructor',
                'question_number', 'question_text', 'response_text'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dept_free_text_rows)

        print(f"  ✓ evaluations_free_text.csv ({len(dept_free_text_rows)} rows)")

        # Update totals
        total_success += len(dept_html_files) - len(dept_errors)
        total_errors += len(dept_errors)

        if dept_errors:
            print(f"\n  Errors in {dept_name}:")
            for error in dept_errors[:5]:
                print(f"    - {error}")
            if len(dept_errors) > 5:
                print(f"    ... and {len(dept_errors) - 5} more")

    print(f"\n{'='*70}")
    print("Done! All departments processed.")
    print(f"\nSummary:")
    print(f"  Departments processed: {len(dept_files)}")
    print(f"  Total courses parsed: {total_success}/{len(html_files)}")
    print(f"  Total errors: {total_errors}")
    print(f"\nCSV files have been written to each department folder:")
    for dept_name in sorted(dept_files.keys()):
        if dept_name in dept_files and dept_files[dept_name]:
             dept_path = dept_files[dept_name][0].parent.parent
             if dept_path.exists():
                 print(f"  • {dept_path}/")


if __name__ == '__main__':
    main()
