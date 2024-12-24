"""
GitBisector to find the change in foo()
"""
from gitbi.git_bisector import GitBisector
from example.foo import foo


class FooBisector(GitBisector):
    def get_output(self, cache_dir: Optiona[str] = None) -> str:
        return foo()

    def are_outputs_identical(self, output1: str, output2: str) -> bool:
        """
        Compare two outputs to determine if they are identical.
        
        Args:
            output1 (str): First output to compare
            output2 (str): Second output to compare
        
        Returns:
            bool: True if outputs are considered identical, False otherwise
        """
        return int(output1) == int(output2)


if __name__ == '__main__':
    bisector = FooBisector()
    bisector.main()
