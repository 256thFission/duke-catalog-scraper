#!/usr/bin/env python3
"""
Backfill crosslisted course metadata to all relevant department folders.

This script reads existing metadata files and copies crosslisted entries
to their respective department folders. For example, if ECE-250D is 
crosslisted with COMPSCI-250D, this ensures the entry appears in both
ECE_metadata.csv and COMPSCI_metadata.csv.

Usage:
    python utils/backfill_crosslisted_metadata.py [data_dir]
    
    data_dir: Path to course_evaluations directory (default: data2/course_evaluations)
"""

import csv
import json
import re
import sys
from pathlib import Path
from collections import defaultdict


def extract_department_codes_from_title(title: str) -> list:
    """Extract all department codes from a course title."""
    pattern = r'\b([A-Z]+(?:&[A-Z]+)?)-\d+[A-Z]?-\d+\b'
    matches = re.findall(pattern, title)
    seen = set()
    unique_codes = []
    for code in matches:
        if code not in seen:
            seen.add(code)
            unique_codes.append(code)
    return unique_codes


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


def load_metadata_json(json_path: Path) -> list:
    """Load metadata from JSON file."""
    if not json_path.exists():
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_metadata_csv(csv_path: Path, entries: list):
    """Save metadata to CSV file."""
    if not entries:
        return
    
    fieldnames = [
        'uid', 'course_code', 'title', 'instructor',
        'term', 'area', 'response_rate',
        'department_codes',
        'data-id0', 'data-id1', 'data-id2', 'data-id3',
        'scraped_at'
    ]
    
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            # Ensure all fieldnames are present
            row = {k: entry.get(k, '') for k in fieldnames}
            writer.writerow(row)


def save_metadata_json(json_path: Path, entries: list):
    """Save metadata to JSON file."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def main():
    # Get data directory from args or use default
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    else:
        data_dir = Path("data2/course_evaluations")
    
    if not data_dir.exists():
        print(f"ERROR: Directory not found: {data_dir}")
        sys.exit(1)
    
    print(f"Backfilling crosslisted metadata in: {data_dir}")
    print("=" * 60)
    
    # Collect all entries from all departments
    all_entries = []  # List of (source_dept, entry_dict)
    dept_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
    
    print(f"Found {len(dept_dirs)} department directories")
    
    for dept_dir in sorted(dept_dirs):
        dept_code = dept_dir.name
        csv_path = dept_dir / f"{dept_code}_metadata.csv"
        
        if not csv_path.exists():
            continue
        
        entries = load_metadata_csv(csv_path)
        for entry in entries:
            all_entries.append((dept_code, entry))
    
    print(f"Loaded {len(all_entries)} total metadata entries")
    
    # Group entries by crosslisted departments
    # Key: target_dept, Value: list of entries that should be there
    crosslist_map = defaultdict(list)  # dept -> [(source_dept, entry), ...]
    
    for source_dept, entry in all_entries:
        title = entry.get('title', '')
        dept_codes = extract_department_codes_from_title(title)
        
        # Also check if department_codes field exists and parse it
        if not dept_codes:
            dept_codes_str = entry.get('department_codes', '')
            if dept_codes_str:
                dept_codes = [d.strip() for d in dept_codes_str.split(',')]
        
        for target_dept in dept_codes:
            if target_dept != source_dept:
                crosslist_map[target_dept].append((source_dept, entry))
    
    print(f"Found crosslisted entries for {len(crosslist_map)} departments")
    print()
    
    # Process each target department
    total_added = 0
    
    for target_dept in sorted(crosslist_map.keys()):
        entries_to_add = crosslist_map[target_dept]
        
        target_dir = data_dir / target_dept
        csv_path = target_dir / f"{target_dept}_metadata.csv"
        json_path = target_dir / f"{target_dept}_metadata.json"
        
        # Load existing entries
        existing_csv = load_metadata_csv(csv_path)
        existing_json = load_metadata_json(json_path)
        
        # Get existing UIDs
        existing_uids = set()
        for entry in existing_csv:
            existing_uids.add(entry.get('uid', ''))
        for entry in existing_json:
            existing_uids.add(entry.get('uid', ''))
        
        # Filter out entries that already exist
        new_entries = []
        for source_dept, entry in entries_to_add:
            uid = entry.get('uid', '')
            if uid and uid not in existing_uids:
                new_entries.append(entry)
                existing_uids.add(uid)  # Prevent duplicates within batch
        
        if not new_entries:
            continue
        
        # Merge and save
        merged_csv = existing_csv + new_entries
        
        # For JSON, we need to handle the data_ids structure
        merged_json = existing_json.copy()
        for entry in new_entries:
            # Convert CSV row to JSON format if needed
            json_entry = dict(entry)
            # Reconstruct data_ids dict if it was flattened
            if 'data-id0' in entry and 'data_ids' not in entry:
                json_entry['data_ids'] = {
                    'data-id0': entry.get('data-id0', ''),
                    'data-id1': entry.get('data-id1', ''),
                    'data-id2': entry.get('data-id2', ''),
                    'data-id3': entry.get('data-id3', ''),
                }
            # Convert department_codes string to list if needed
            if isinstance(json_entry.get('department_codes'), str):
                dept_str = json_entry['department_codes']
                json_entry['department_codes'] = [d.strip() for d in dept_str.split(',') if d.strip()]
            merged_json.append(json_entry)
        
        save_metadata_csv(csv_path, merged_csv)
        save_metadata_json(json_path, merged_json)
        
        source_depts = set(src for src, _ in entries_to_add)
        print(f"  {target_dept}: +{len(new_entries)} entries (from {', '.join(sorted(source_depts))})")
        total_added += len(new_entries)
    
    print()
    print("=" * 60)
    print(f"Backfill complete! Added {total_added} crosslisted entries.")


if __name__ == "__main__":
    main()
