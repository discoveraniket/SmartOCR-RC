import subprocess
import sys
import os

def main():
    # Ensure we are in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # Path to the virtual environment's python
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    
    if not os.path.exists(venv_python):
        print(f"Error: Virtual environment not found at {venv_python}")
        sys.exit(1)

    print("--- Running RC-PaddleOCR Test Suite ---\n")
    
    # Run pytest on the entire tests folder
    result = subprocess.run([venv_python, "-m", "pytest", "tests/", "-v", "-p", "no:warnings"])
    
    if result.returncode == 0:
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed. Please check the output above.")
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
