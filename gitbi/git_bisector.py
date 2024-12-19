from abc import ABC, abstractmethod
import argparse
import subprocess
import sys

MAX_ITERATIONS = 1000

class GitBisector(ABC):
    """
    Abstract base class for performing git bisect operations to detect code changes.
    """

    @abstractmethod
    def get_output(self) -> str:
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

    def get_example_in_subprocess(self, main_name: str, main_content: str) -> str:
        """
        Run the example in a subprocess and return the output.
        
        Args:
            None
        
        Returns:
            str: The output of the example
        """
        main_is_missing = not os.path.exists(main_name)
        if main_is_missing:
            with open(main_name, 'w') as f:
                f.write(main_content)
        command = [sys.executable, sys.argv[0], 'example']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if main_is_missing:
            os.remove(main_name)
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
        with open(main_name, 'r') as f:
            main_content = f.read()
        try:
            # Checkout the start commit
            subprocess.run(['git', 'checkout', start_commit], check=True)
            
            # Run initial example
            baseline_output = self.get_example_in_subprocess(main_name, main_content)
            
            # Set up git bisect
            subprocess.run(['git', 'bisect', 'start', end_commit, start_commit], check=True)
            
            # Perform the bisect
            for _ in range(MAX_ITERATIONS):
                # Run the current example
                current_output = self.get_example_in_subprocess(main_name, main_content)
                
                # Compare outputs
                if self.are_outputs_identical(baseline_output, current_output):
                    # Output is the same, continue bisecting
                    result = subprocess.run(['git', 'bisect', 'good'], 
                                            capture_output=True, text=True)
                else:
                    # Output has changed, mark as bad
                    result = subprocess.run(['git', 'bisect', 'bad'], 
                                            capture_output=True, text=True)
                
                # Check if bisect is complete
                if 'is the first bad commit' in result.stdout:
                    # Extract the commit hash
                    commit_match = result.stdout.split('\n')[0].split(':')[0].strip()
                    return commit_match
                
                if 'There are no more revisions' in result.stdout:
                    raise ValueError("No change detected between commits")
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
            output = self.get_output()
            print(output)

        else:
            parser.print_help()
            sys.exit(1)
