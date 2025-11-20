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
                    if li_text and len(li_text) > 5:
                        question_data['free_text'].append(li_text)

                elif elem.name == 'p':
                    # Check if it's a free text response
                    p_text = elem.get_text(strip=True)
                    if p_text and len(p_text) > 10:
                        # This might be a free text response
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

    def to_csv_responses(self, output_path: str):
        """
        Export to CSV format with one row per response option.
        Best for quantitative analysis of rating distributions.
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'filename', 'semester', 'course', 'instructor',
                'question_number', 'question_text',
                'response_option', 'weight', 'frequency', 'percentage',
                'response_rate', 'mean', 'std', 'median'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

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
                    # Write one row per response option
                    for response in question['responses']:
                        row = base_row.copy()
                        row['response_option'] = response.get('option', '')
                        row['weight'] = response.get('weight', '')
                        row['frequency'] = response.get('frequency', '')
                        row['percentage'] = response.get('percentage', '')
                        writer.writerow(row)
                else:
                    # Write one row even if no responses (for free text questions)
                    writer.writerow(base_row)

    def to_csv_questions(self, output_path: str):
        """
        Export to CSV format with one row per question.
        Best for overview and comparison of questions.
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'filename', 'semester', 'course', 'instructor',
                'question_number', 'question_text',
                'response_rate', 'mean', 'std', 'median',
                'total_responses', 'response_distribution'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

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
                writer.writerow(row)

    def to_csv_free_text(self, output_path: str):
        """
        Export free text responses to CSV.
        Best for qualitative analysis.
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'filename', 'semester', 'course', 'instructor',
                'question_number', 'question_text', 'response_text'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

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
                        writer.writerow(row)


def main():
    """Main function to parse evaluation files."""
    if len(sys.argv) < 2:
        print("Usage: python parse_course_evaluations.py <html_file1> [html_file2] ...")
        print("\nExample:")
        print("  python parse_course_evaluations.py COMPSCI-512-01_Maggs__Bruce_Fall_2024.html")
        print("\nThis will generate three CSV files:")
        print("  - evaluations_responses.csv (detailed response-level data)")
        print("  - evaluations_questions.csv (summary question-level data)")
        print("  - evaluations_free_text.csv (free text responses)")
        sys.exit(1)

    html_files = sys.argv[1:]

    # Parse all files and combine results
    all_parsers = []
    for html_file in html_files:
        if not Path(html_file).exists():
            print(f"Warning: File not found: {html_file}")
            continue

        print(f"Parsing: {html_file}")
        parser = CourseEvaluationParser(html_file)
        all_parsers.append(parser)
        print(f"  Course: {parser.course_info['course']}")
        print(f"  Instructor: {parser.course_info['instructor']}")
        print(f"  Questions: {len(parser.questions)}")

    if not all_parsers:
        print("Error: No valid files to parse")
        sys.exit(1)

    # Generate combined CSV files
    print("\nGenerating CSV files...")

    # Response-level CSV
    responses_csv = 'evaluations_responses.csv'
    with open(responses_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'filename', 'semester', 'course', 'instructor',
            'question_number', 'question_text',
            'response_option', 'weight', 'frequency', 'percentage',
            'response_rate', 'mean', 'std', 'median'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    for parser in all_parsers:
        parser.to_csv_responses(responses_csv)

    print(f"  ✓ {responses_csv}")

    # Question-level CSV
    questions_csv = 'evaluations_questions.csv'
    with open(questions_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'filename', 'semester', 'course', 'instructor',
            'question_number', 'question_text',
            'response_rate', 'mean', 'std', 'median',
            'total_responses', 'response_distribution'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    for parser in all_parsers:
        parser.to_csv_questions(questions_csv)

    print(f"  ✓ {questions_csv}")

    # Free text CSV
    free_text_csv = 'evaluations_free_text.csv'
    with open(free_text_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'filename', 'semester', 'course', 'instructor',
            'question_number', 'question_text', 'response_text'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    for parser in all_parsers:
        parser.to_csv_free_text(free_text_csv)

    print(f"  ✓ {free_text_csv}")

    print("\nDone! CSV files generated successfully.")


if __name__ == '__main__':
    main()
