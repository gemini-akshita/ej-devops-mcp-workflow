import os
import re
import json
import logging
from functools import wraps
from threading import Thread, Lock
from typing import Callable, List, Dict, Any

print("Hello, World Test124453dsf!")
print("Hello, World Test!")
print("Hello, World Test!")

def test():
    print("This is a test function.")


def log_and_thread_safe(lock: Lock):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                logging.info(f"Executing {func.__name__} with args={args} kwargs={kwargs}")
                try:
                    result = func(*args, **kwargs)
                    logging.info(f"{func.__name__} executed successfully.")
                    return result
                except Exception as e:
                    logging.error(f"Error in {func.__name__}: {e}")
                    raise
        return wrapper
    return decorator

# Complex processor class
class FileDataProcessor:
    def __init__(self, directory: str):
        self.directory = directory
        self.results: Dict[str, Any] = {}
        self.lock = Lock()

    @log_and_thread_safe(lock=Lock())
    def process_files(self, pattern: str):
        threads = []
        for filename in os.listdir(self.directory):
            if filename.endswith('.txt'):
                filepath = os.path.join(self.directory, filename)
                thread = Thread(target=self._process_single_file, args=(filepath, pattern))
                threads.append(thread)
                thread.start()
        for t in threads:
            t.join()

    def _process_single_file(self, filepath: str, pattern: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            matches = re.findall(pattern, content)
            summary = {
                "filename": os.path.basename(filepath),
                "match_count": len(matches),
                "matches": matches[:5]  # Limit output for brevity
            }
            with self.lock:
                self.results[os.path.basename(filepath)] = summary
        except Exception as e:
            logging.error(f"Failed to process {filepath}: {e}")

    def export_summary(self, output_file: str):
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=4)
            logging.info(f"Summary exported to {output_file}")
        except Exception as e:
            logging.error(f"Failed to write summary: {e}")