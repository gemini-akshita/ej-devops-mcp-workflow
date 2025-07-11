import os
import re
import json
import logging
from functools import wraps
from threading import Thread, Lock
from typing import Callable, List, Dict, Any
import time
from functools import lru_cache
from typing import Optional, Tuple
import time
import functools
import logging
import psutil
import os
import threading
import inspect
import asyncio
import os
import fnmatch
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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
                print(f"Executing {func.__name__} with args={args} kwargs={kwargs}")
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
    # def process_files(self, pattern: str):
    #     threads = []
    #     for filename in os.listdir(self.directory):
    #         if filename.endswith('.txt'):
    #             filepath = os.path.join(self.directory, filename)
    #             thread = Thread(target=self._process_single_file, args=(filepath, pattern))
    #             threads.append(thread)
    #             thread.start()
    #     for t in threads:
    #         t.join()

    def process_files(self, pattern: str, max_workers: int = 5):
        """Process files matching a pattern using multithreading."""
        start_time = time.time()
        logging.info("Started processing files...")

        matched_files = [
            os.path.join(self.directory, f)
            for f in os.listdir(self.directory)
            if fnmatch.fnmatch(f, pattern)
        ]

        def safe_process(filepath):
            try:
                logging.info(f"Processing file: {filepath}")
                self._process_single_file(filepath, pattern)
                logging.info(f"Completed file: {filepath}")
            except Exception as e:
                logging.error(f"Failed to process {filepath}: {e}", exc_info=True)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(safe_process, file) for file in matched_files]
            for future in as_completed(futures):
                # Optionally process results or exceptions
                future.result()  # Re-raise exceptions if any occurred

        end_time = time.time()
        logging.info(f"All files processed in {end_time - start_time:.2f} seconds.")

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

class EditDistanceError(Exception):
    """Custom exception for edit distance calculation errors."""
    pass


def benchmark(func):
    
    call_count = 0
    lock = threading.Lock()
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        nonlocal call_count
        with lock:
            call_count += 1
        
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024
        cpu_before = psutil.cpu_percent(interval=None)

        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            logging.error(f"Exception in {func.__name__}: {e}", exc_info=True)
        end_time = time.perf_counter()

        mem_after = process.memory_info().rss / 1024 / 1024
        cpu_after = psutil.cpu_percent(interval=None)

        elapsed = end_time - start_time
        mem_delta = mem_after - mem_before

        log_message = (
            f"[Benchmark] Function: {func.__name__} | Time: {elapsed:.6f}s | "
            f"Memory Change: {mem_delta:.2f} MB | CPU: {cpu_after - cpu_before:.2f}% | "
            f"Calls: {call_count} | Success: {success}"
        )
        print(log_message)
        logging.info(log_message)

        return result


@benchmark
def compute_edit_distance(s1: str, s2: str, verbose: Optional[bool] = False) -> Tuple[int, str]:
    """
    Computes the Levenshtein distance (edit distance) between two strings using recursion + memoization.

    Args:
        s1 (str): First string.
        s2 (str): Second string.
        verbose (bool): If True, prints the step-by-step transformation.

    Returns:
        Tuple[int, str]: Minimum number of operations and a summary of the transformation path.
    """
    if not isinstance(s1, str) or not isinstance(s2, str):
        raise EditDistanceError("Both inputs must be strings")

    @lru_cache(maxsize=None)
    def dp(i: int, j: int) -> int:
        if i == 0:
            return j
        if j == 0:
            return i
        if s1[i - 1] == s2[j - 1]:
            return dp(i - 1, j - 1)
        return 1 + min(
            dp(i - 1, j),    # Deletion
            dp(i, j - 1),    # Insertion
            dp(i - 1, j - 1) # Substitution
        )

    distance = dp(len(s1), len(s2))

    summary = f"Edit distance between '{s1}' and '{s2}' is {distance}."
    if verbose:
        summary += " (computed with memoized recursion)"

    return distance, summary