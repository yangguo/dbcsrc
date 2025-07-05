#!/usr/bin/env python3
"""
Validate requirements.txt for common issues
"""
import re
import sys
from pathlib import Path

def validate_requirements(requirements_file):
    """Validate requirements.txt file for common issues"""
    if not Path(requirements_file).exists():
        print(f"Error: {requirements_file} not found")
        return False
    
    packages = {}
    issues = []
    
    with open(requirements_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            # Check for package specifications
            if '==' in line:
                # Extract package name and version
                parts = line.split('==')
                if len(parts) == 2:
                    package = parts[0].strip()
                    version = parts[1].strip()
                    
                    # Check for duplicates
                    if package in packages:
                        issues.append(f"Line {line_num}: Duplicate package '{package}' (also on line {packages[package]['line']})")
                    else:
                        packages[package] = {'version': version, 'line': line_num}
    
    # Report results
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print(f"✓ No issues found in {requirements_file}")
        print(f"✓ Total packages: {len(packages)}")
        return True

if __name__ == "__main__":
    requirements_file = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    success = validate_requirements(requirements_file)
    sys.exit(0 if success else 1)