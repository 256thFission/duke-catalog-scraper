#!/usr/bin/env python3
"""
Backfill crosslisted course report files to all relevant department folders.

This script reads existing report files and copies them to crosslisted
department folders with the correct filename. For example, if ECE-250D is 
crosslisted with COMPSCI-250D, this copies:
  ECE/reports/ECE-250D-001_instructor_term.html
to:
  COMPSCI/reports/COMPSCI-250D-001_instructor_term.html

Usage:
    python utils/backfill_crosslisted_reports.py [data_dir]
    
    data_dir: Path to course_evaluations directory (default: data2/course_evaluations)
"""

import csv
import re
import shutil
import sys
from pathlib import Path


def extract_course_codes_by_department(title: str) -> dict:
    """
    Extract full course codes from a title, mapped by department.
    
    Returns: Dict mapping department to full course code
             e.g., {'ECE': 'ECE-250D-001', 'COMPSCI': 'COMPSCI-250D-001'}
    """
    pattern = r'\b([A-Z]+(?:&[A-Z]+)?-\d+[A-Z]*-\d+[A-Z]?)\b'
    matches = re.findall(pattern, title)
    
    dept_to_course = {}
    for course_code in matches:
        dept = course_code.split('-')[0]
        if dept not in dept_to_course:
            dept_to_course[dept] = course_code
    
    return dept_to_course


def load_metadata_csv(csv_path: Path) -> list:
    """Load metadata from CSV file."""
    if not csv_path.exists():
        return []
    
    entries = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(row)
    return entries


def main():
    # Get data directory from args or use default
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    else:
        data_dir = Path("data2/course_evaluations")
    
    if not data_dir.exists():
        print(f"ERROR: Directory not found: {data_dir}")
        sys.exit(1)
    
    print(f"Backfilling crosslisted reports in: {data_dir}")
    print("=" * 60)
    
    # Collect all metadata entries with crosslisted courses
    dept_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
    print(f"Found {len(dept_dirs)} department directories")
    
    total_copied = 0
    total_skipped = 0
    
    for dept_dir in sorted(dept_dirs):
        source_dept = dept_dir.name
        csv_path = dept_dir / f"{source_dept}_metadata.csv"
        reports_dir = dept_dir / "reports"
        
        if not csv_path.exists() or not reports_dir.exists():
            continue
        
        entries = load_metadata_csv(csv_path)
        
        for entry in entries:
            title = entry.get('title', '')
            primary_course_code = entry.get('course_code', '')
            instructor = entry.get('instructor', '')
            term = entry.get('term', '')
            
            # Get all course codes by department
            dept_to_course = extract_course_codes_by_department(title)
            
            if len(dept_to_course) <= 1:
                # Not crosslisted
                continue
            
            # Build source filename
            safe_primary = re.sub(r'[^\w\-]', '_', primary_course_code)
            safe_instructor = re.sub(r'[^\w\-]', '_', instructor)
            safe_term = re.sub(r'[^\w\-]', '_', term)
            source_filename = f"{safe_primary}_{safe_instructor}_{safe_term}.html"
            source_path = reports_dir / source_filename
            
            if not source_path.exists():
                # Try to find with department-specific name
                dept_course = dept_to_course.get(source_dept, primary_course_code)
                safe_dept_course = re.sub(r'[^\w\-]', '_', dept_course)
                source_filename = f"{safe_dept_course}_{safe_instructor}_{safe_term}.html"
                source_path = reports_dir / source_filename
                
                if not source_path.exists():
                    continue
            
            # Copy to each crosslisted department
            for target_dept, target_course_code in dept_to_course.items():
                if target_dept == source_dept:
                    continue
                
                target_dir = data_dir / target_dept / "reports"
                target_dir.mkdir(parents=True, exist_ok=True)
                
                safe_target = re.sub(r'[^\w\-]', '_', target_course_code)
                target_filename = f"{safe_target}_{safe_instructor}_{safe_term}.html"
                target_path = target_dir / target_filename
                
                if target_path.exists():
                    total_skipped += 1
                    continue
                
                # Copy the file
                shutil.copy2(source_path, target_path)
                print(f"  {source_dept} -> {target_dept}: {target_filename}")
                total_copied += 1
    
    print()
    print("=" * 60)
    print(f"Backfill complete! Copied {total_copied} report files, skipped {total_skipped} existing.")


if __name__ == "__main__":
    main()
