#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import re
from pathlib import Path

def resolve_venv_path():
    """Resolve the virtual environment path"""
    paths = [
        Path(r"C:\python\virtualenvs\mulesoft-flow-analyzer\Scripts\python.exe"),  # Windows path with Scripts
        Path(r"C:\python\virtualenvs\mulesoft-flow-analyzer\python.exe"),         # Windows path
        Path("/c/python/virtualenvs/mulesoft-flow-analyzer/Scripts/python.exe"),  # Git Bash path with Scripts
        Path("/c/python/virtualenvs/mulesoft-flow-analyzer/python.exe"),         # Git Bash path
    ]
    
    for path in paths:
        if path.exists():
            print(f"Found Python at: {path}")
            return path
            
    print("Attempted paths:")
    for path in paths:
        print(f"- {path} (exists: {path.exists()})")
    return paths[0]  # Return first path as default

VENV_PYTHON = resolve_venv_path()

def check_prerequisites():
    """Check if all required tools are installed"""
    if not VENV_PYTHON.exists():
        print(f"Error: Virtual environment Python not found at {VENV_PYTHON}")
        sys.exit(1)

    # Check PyInstaller in the virtual environment
    try:
        run_command([str(VENV_PYTHON), '-c', 'import PyInstaller'])
    except subprocess.CalledProcessError:
        print("Error: PyInstaller is not installed in the virtual environment. Please install it first.")
        sys.exit(1)

def run_command(command, cwd=None):
    """Run a command and return its output"""
    try:
        result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(command)}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)

def check_git_status():
    """Check if there are any uncommitted changes"""
    status = run_command(['git', 'status', '--porcelain'])
    if status:
        print("Error: There are uncommitted changes in the repository.")
        print("Please commit or stash them before proceeding.")
        sys.exit(1)

def commit_and_push_changes(version):
    """Commit version changes and push to origin"""
    print("\nCommitting version changes...")
    run_command(['git', 'add', 'src/mulesoft_flow_analyzer/__init__.py', 'setup.py', 'pyproject.toml'])
    run_command(['git', 'commit', '-m', f'Bump version to {version}'])
    print("Pushing changes to origin...")
    run_command(['git', 'push'])

def run_tests():
    """Run pytest in the virtual environment"""
    print("Running tests...")
    run_command([str(VENV_PYTHON), '-m', 'pytest'])
    print("All tests passed!")

def get_current_version():
    """Get current version from __init__.py"""
    init_path = Path('src/mulesoft_flow_analyzer/__init__.py')
    with open(init_path) as f:
        content = f.read()
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not match:
        print("Error: Could not find version in __init__.py")
        sys.exit(1)
    return match.group(1)

def update_version(current_version):
    """Update version based on user input"""
    print(f"\nCurrent version: {current_version}")
    while True:
        change_type = input("Enter version change type (1. major/2. minor/3. patch): ").lower()
        if change_type not in ['1', '2', '3']:
            print("Invalid input. Please enter '1', '2', or '3'")
            continue
        break

    major, minor, patch = map(int, current_version.split('.'))
    if change_type == '1':
        new_version = f"{major + 1}.0.0"
    elif change_type == '2':
        new_version = f"{major}.{minor + 1}.0"
    else:  # patch
        new_version = f"{major}.{minor}.{patch + 1}"

    # Update version in files
    files_to_update = [
        'src/mulesoft_flow_analyzer/__init__.py',
        'setup.py',
        'pyproject.toml'
    ]

    for file_path in files_to_update:
        with open(file_path) as f:
            content = f.read()
        
        # Update version pattern based on file type
        if file_path.endswith('__init__.py'):
            new_content = re.sub(
                r"__version__\s*=\s*['\"]([^'\"]+)['\"]",
                f"__version__ = '{new_version}'",
                content
            )
        else:
            new_content = re.sub(
                r'version\s*=\s*["\']([^"\']+)["\']',
                f'version="{new_version}"',
                content
            )
        
        with open(file_path, 'w') as f:
            f.write(new_content)

    return new_version

def build_packages():
    """Build wheel and exe files"""
    print("\nBuilding wheel file...")
    run_command([str(VENV_PYTHON), '-m', 'pip', 'install', 'build'])
    run_command([str(VENV_PYTHON), '-m', 'build'])

    print("\nBuilding exe file...")
    run_command([str(VENV_PYTHON), '-m', 'PyInstaller', 'mulesoft-flow-analyzer.spec'])

def copy_wheel_to_private_repo(version):
    """Copy wheel file to private packages repository"""
    # Find the wheel file
    dist_dir = Path('dist')
    wheel_files = list(dist_dir.glob('*.whl'))
    if not wheel_files:
        print("Error: No wheel file found in dist directory")
        sys.exit(1)
    wheel_file = wheel_files[0]

    # Create target directory
    target_dir = Path(f'C:/workspace/private-python-packages/mulesoft-flow-analyzer/{version}')
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy wheel file
    shutil.copy2(wheel_file, target_dir)
    print(f"\nCopied wheel file to {target_dir}")

def update_private_repo(version):
    """Update private packages repository"""
    repo_path = 'C:/workspace/private-python-packages'
    os.chdir(repo_path)
    
    run_command(['git', 'add', '.'])
    run_command(['git', 'commit', '-m', f'Add mulesoft-flow-analyzer version {version}'])
    run_command(['git', 'push'])
    print("\nPushed changes to private packages repository")

def main():
    print("Starting release process...\n")
    
    # Check prerequisites
    check_prerequisites()
    
    # Check git status
    print("Checking git status...")
    check_git_status()
    
    # Run tests
    run_tests()
    
    # Get and update version
    current_version = get_current_version()
    new_version = update_version(current_version)
    
    # Commit and push version changes
    commit_and_push_changes(new_version)
    
    # Build packages
    build_packages()
    
    # Copy wheel file and update private repo
    copy_wheel_to_private_repo(new_version)
    update_private_repo(new_version)
    
    print(f"\nRelease {new_version} completed successfully!")

if __name__ == '__main__':
    main() 