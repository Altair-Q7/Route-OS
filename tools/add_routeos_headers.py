#!/usr/bin/env python3
"""
RouteOS Header Injection Script
Adds RouteOS identification headers to all RouteOS-specific source files.
"""

import os
import sys
from pathlib import Path

# RouteOS header templates by file extension
HEADERS = {
    '.py': '''"""
RouteOS - Driver/Ride Management Backend
This file is part of RouteOS, a driver management layer built on Organic Maps.
Organic Maps is an open-source offline maps & GPS app (https://organicmaps.app).
RouteOS extends Organic Maps with ride/route management, driver tracking, and admin features.
"""

''',
    '.dart': '''// RouteOS - Driver/Ride Management UI Layer
// This file is part of RouteOS, a driver management layer built on Organic Maps.
// Organic Maps is an open-source offline maps & GPS app (https://organicmaps.app).
// RouteOS extends Organic Maps with ride/route management, driver tracking, and admin features.

''',
    '.java': '''/**
 * RouteOS - Driver/Ride Management Android Layer
 * This file is part of RouteOS, a driver management layer built on Organic Maps.
 * Organic Maps is an open-source offline maps & GPS app (https://organicmaps.app).
 * RouteOS extends Organic Maps with ride/route management, driver tracking, and admin features.
 */

''',
    '.kt': '''/**
 * RouteOS - Driver/Ride Management Android Layer
 * This file is part of RouteOS, a driver management layer built on Organic Maps.
 * Organic Maps is an open-source offline maps & GPS app (https://organicmaps.app).
 * RouteOS extends Organic Maps with ride/route management, driver tracking, and admin features.
 */

''',
    '.sh': '''#!/bin/bash
# RouteOS - Build/Run Scripts
# This file is part of RouteOS, a driver management layer built on Organic Maps.
# Organic Maps is an open-source offline maps & GPS app (https://organicmaps.app).
# RouteOS extends Organic Maps with ride/route management, driver tracking, and admin features.

''',
    '.md': '''# RouteOS Documentation
# This file is part of RouteOS, a driver management layer built on Organic Maps.
# Organic Maps is an open-source offline maps & GPS app (https://organicmaps.app).
# RouteOS extends Organic Maps with ride/route management, driver tracking, and admin features.

''',
}

# RouteOS-specific files to process
ROUTEOS_FILES = [
    # Backend Python files
    "backend/app.py",
    "backend/tests/conftest.py",
    "backend/tests/test_auth.py",
    "backend/tests/test_create_route.py",
    "backend/tests/test_database.py",
    "backend/tests/test_rides.py",
    "backend/tests/test_track_timestamps.py",
    "backend/tests/test_permissions.py",
    "backend/tests/test_planned_routes.py",
    "backend/tests/test_sessions.py",
    "backend/provision_password.py",
    
    # Flutter Dart files
    "flutter_routeos/lib/main.dart",
    "flutter_routeos/lib/app/app.dart",
    "flutter_routeos/lib/core/bridge.dart",
    "flutter_routeos/lib/home/home.dart",
    "flutter_routeos/lib/map/native_map.dart",
    "flutter_routeos/lib/routing/planner.dart",
    
    # Android RouteOS package Java files
    "android/app/src/main/java/app/routeos/RouteOsAdminOverlay.java",
    "android/app/src/main/java/app/routeos/RouteOsHomeOverlay.java",
    "android/app/src/main/java/app/routeos/RouteOsLoginActivity.java",
    "android/app/src/main/java/app/routeos/RouteOsNavigationOverlay.java",
    "android/app/src/main/java/app/routeos/RouteOsRecordingSession.java",
    "android/app/src/main/java/app/routeos/RouteOsRoutesActivity.java",
    "android/app/src/main/java/app/routeos/RouteOsSearchActivity.java",
    "android/app/src/main/java/app/routeos/RouteOsTrackPreview.java",
    "android/app/src/main/java/app/routeos/RouteOsUi.java",
    "android/app/src/main/java/app/routeos/RouteOsVehicleActivity.java",
    "android/app/src/main/java/app/routeos/bridge/RouteOsFlutterHost.java",
    "android/sdk/src/main/java/app/routeos/RouteOsApi.java",
    "android/sdk/src/main/java/app/routeos/RouteOsCredentials.java",
    
    # Modified Organic Maps integration files
    "android/app/src/main/java/app/organicmaps/MwmActivity.java",
    "android/app/src/main/java/app/organicmaps/location/TrackRecordingService.java",
    "android/libs/routing/src/main/java/app/organicmaps/routing/NavigationService.java",
    
    # Scripts and docs
    "run_routeos.py",
    "ROUTEOS_STRUCTURE.md",
    "README-ROUTEOS.md",
    "tools/build-routeos-flutter-aar.sh",
]


def get_header_for_file(filepath: Path) -> str:
    """Get the appropriate header for a file based on its extension."""
    suffix = filepath.suffix.lower()
    return HEADERS.get(suffix, '')


def has_routeos_header(content: str) -> bool:
    """Check if file already has a RouteOS header."""
    return 'RouteOS' in content[:500] and ('Organic Maps' in content[:500] or 'organicmaps.app' in content[:500])


def add_header(filepath: Path, dry_run: bool = False) -> bool:
    """Add RouteOS header to a file if it doesn't already have one."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}")
        return False
    
    if has_routeos_header(content):
        print(f"  SKIP (already has header): {filepath}")
        return True
    
    header = get_header_for_file(filepath)
    if not header:
        print(f"  SKIP (no header template): {filepath}")
        return True
    
    new_content = header + content
    
    if dry_run:
        print(f"  WOULD ADD HEADER: {filepath}")
        return True
    
    try:
        filepath.write_text(new_content, encoding='utf-8')
        print(f"  ADDED HEADER: {filepath}")
        return True
    except Exception as e:
        print(f"  ERROR writing {filepath}: {e}")
        return False


def main():
    repo_root = Path("/home/altair/Altair/Projects/Route App/Route-OS")
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("=== DRY RUN MODE ===")
    
    print(f"\nProcessing {len(ROUTEOS_FILES)} RouteOS files...\n")
    
    success = 0
    failed = 0
    
    for rel_path in ROUTEOS_FILES:
        filepath = repo_root / rel_path
        if not filepath.exists():
            print(f"  MISSING: {rel_path}")
            failed += 1
            continue
        
        if add_header(filepath, dry_run):
            success += 1
        else:
            failed += 1
    
    print(f"\n=== SUMMARY ===")
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    print(f"Total: {len(ROUTEOS_FILES)}")


if __name__ == '__main__':
    main()