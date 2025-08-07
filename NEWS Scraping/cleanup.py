import os
import shutil
from tqdm import tqdm

def cleanup_pycache():
    """Remove all __pycache__ directories and .pyc files in the current directory and subdirectories."""
    current_dir = os.getcwd()
    
    # First, collect all items to clean
    pycache_dirs = []
    pyc_files = []
    
    # Walk through all directories and collect targets
    for root, dirs, files in os.walk(current_dir):
        if '__pycache__' in dirs:
            pycache_dirs.append(os.path.join(root, '__pycache__'))
        for file in files:
            if file.endswith('.pyc'):
                pyc_files.append(os.path.join(root, file))
    
    # Remove __pycache__ directories with progress bar
    if pycache_dirs:
        for pycache_path in tqdm(pycache_dirs, desc="Removing __pycache__ directories"):
            try:
                shutil.rmtree(pycache_path)
            except:
                pass
    
    # Remove .pyc files with progress bar
    if pyc_files:
        for pyc_file in tqdm(pyc_files, desc="Removing .pyc files"):
            try:
                os.remove(pyc_file)
            except:
                pass
    
    print("Cleaned everything boiiii")

if __name__ == "__main__":
    cleanup_pycache() 