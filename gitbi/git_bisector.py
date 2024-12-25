from typing import Optional
from abc import ABC, abstractmethod
import os
import argparse
import subprocess
import sys
import time
import tempfile

MAX_ITERATIONS = 1000

class GitBisector(ABC):
    """
    Abstract base class for performing git bisect operations to detect code changes.
    """

    @abstractmethod
    def get_output(self, cache_dir: Optional[str] = None) -> str:
        """
        Get a single example output.
        
        Args:
            None
        
        Returns:
            str: The output of the example
        """
        pass

    @abstractmethod
    def are_outputs_identical(self, output1: str, output2: str) -> bool:
        """
        Compare two outputs to determine if they are identical.
        
        Args:
            output1 (str): First output to compare
            output2 (str): Second output to compare
        
        Returns:
            bool: True if outputs are considered identical, False otherwise
        """
        pass

    def get_example_in_subprocess(self, main_name: str, main_content: str,
                                  cache_dir: Optional[str] = None) -> str:
        """
        Run the example in a subprocess and return the output.
        
        Args:
            None
        
        Returns:
            str: The output of the example
        """
        print('Getting example in subprocess')
        start_time = time.time()

        main_is_missing = not os.path.exists(main_name)
        if main_is_missing:
            print(f'Writing main file to {main_name}')
            os.makedirs(os.path.dirname(main_name), exist_ok=True)
            with open(main_name, 'w') as f:
                f.write(main_content)
        command = [sys.executable, sys.argv[0], 'example']
        if cache_dir is not None:
            command.extend(['--cache-dir', cache_dir])
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f'Error running subprocess: {e}')
            print(f'Stdout: {e.stdout}\nsterr: {e.stderr}')
            raise
        finally:
            if main_is_missing:
                print(f'Removing main file {main_name}')
                try:
                    os.remove(main_name)
                except OSError as e:
                    print(f'Warning: Failed to remove temporary file {main_name}: {e}')
        end_time = time.time()
        execution_time = end_time - start_time
        print(f'Got output length {len(result.stdout)}. '
                f'Subprocess execution time: {execution_time:.2f} seconds')
        return result.stdout


    def run_git_bisect(
        self,
        start_commit: str, 
        end_commit: str
    ) -> str:
        """
        Perform git bisect to find the commit where output changes.
        
        Args:
            start_commit (str): The earlier commit to start from
            end_commit (str): The later commit to end at
            bisector_instance (GitBisector): Instance of a GitBisector subclass
            extra_args (list, optional): Additional arguments to pass to example command
        
        Returns:
            str: The first commit where the output changes
        """
        current_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                        capture_output=True, text=True, check=True)
        main_name = sys.argv[0]
        try:
            file_size = os.path.getsize(main_name)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                raise ValueError(f"Main file too large: {file_size} bytes")
            with open(main_name, 'r') as f:
                main_content = f.read()
        except (IOError, OSError) as e:
            print(f'Failed to read main file: {e}')
            raise
        try:
            with tempfile.TemporaryDirectory() as cache_dir:
                # Run initial example
                subprocess.run(['git', 'checkout', start_commit], check=True)
                baseline_output = self.get_example_in_subprocess(main_name, main_content, cache_dir)
                
                # Run the end commit example
                subprocess.run(['git', 'checkout', end_commit], check=True)
                final_output = self.get_example_in_subprocess(main_name, main_content, cache_dir)

                if self.are_outputs_identical(baseline_output, final_output):
                    print('No change detected between start and end commits')
                    return None

                # Set up git bisect
                subprocess.run(['git', 'bisect', 'start'], check=True)
                subprocess.run(['git', 'bisect', 'good', start_commit], check=True)
                subprocess.run(['git', 'bisect', 'bad', end_commit], check=True)
                
                for _ in range(MAX_ITERATIONS):
                    # Get output for current commit
                    current_output = self.get_example_in_subprocess(main_name, main_content, cache_dir)

                    # Compare outputs
                    if self.are_outputs_identical(baseline_output, current_output):
                        # Output is the same, continue bisecting
                        result = subprocess.run(['git', 'bisect', 'good'], 
                                                capture_output=True, text=True)
                    else:
                        if not self.are_outputs_identical(final_output, current_output):
                            current_commit_hash = subprocess.run(
                                ['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)
                            commit_hash_str = current_commit_hash.stdout.strip()
                            print(f'Warning: output at {commit_hash_str} is different '
                                f'from both start and end commits')
                        # Output has changed, mark as bad
                        result = subprocess.run(['git', 'bisect', 'bad'], 
                                                capture_output=True, text=True)
                    
                    # Check if bisect is complete
                    if 'is the first bad commit' in result.stdout:
                        # Extract the commit hash
                        commit_match = result.stdout.split('\n')[0].split(':')[0].strip()
                        return commit_match
                    
                    if 'There are no more revisions' in result.stdout:
                        print("No change detected between commits")
                        return None
            print(f'Could not find a change in {MAX_ITERATIONS} iterations, potentially git bisect output changed')
        finally:
            # Return to the original commit
            subprocess.run(['git', 'bisect', 'reset'], check=False)
            subprocess.run(['git', 'checkout', current_commit.stdout.strip()], check=True)

    def main(self) -> None:
        """
        Command-line interface for git bisector.
        Supports multiple modes of operation:
        1. Git bisect mode
        2. Example running mode
        """
        parser = argparse.ArgumentParser(description='Git Bisector tool')
        
        # Create subparsers for different modes
        subparsers = parser.add_subparsers(dest='mode', help='Operation mode', required=True)
        
        # Bisect mode
        bisect_parser = subparsers.add_parser('bisect', help='Perform git bisect')
        bisect_parser.add_argument('start_commit', help='The starting (earlier) commit')
        bisect_parser.add_argument('end_commit', help='The ending (later) commit')
        bisect_parser.add_argument('--extra-args', 
                                help='Extra arguments to pass to the example command (comma-separated)',
                                default=None)
        
        # Example mode
        example_parser = subparsers.add_parser('example', help='Run example')
        example_parser.add_argument('--cache-dir', type=str, 
                                    help='Directory to cache example files',
                                    required=False, default=None)
        example_parser.add_argument('--extra-args', 
                                help='Extra arguments to pass to the example command (comma-separated)',
                                default=None)

        # Parse arguments
        args = parser.parse_args()
        
        if args.mode == 'bisect':
            # Run git bisect
            changed_commit = self.run_git_bisect(
                args.start_commit, 
                args.end_commit, 
            )
            print(f"First commit with change: {changed_commit}")
        
        elif args.mode == 'example':
            # Run example
            output = self.get_output(args.cache_dir)
            print(output)

        else:
            parser.print_help()
            sys.exit(1)
