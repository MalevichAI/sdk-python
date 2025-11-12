from subprocess import Popen, PIPE


class UserVirtualEnvironment:
    """Class to run commands with Python interpreter from specified virtual environments.
    
    Supports both module calls (python -m module) and script calls (python script.py).
    """
    
    def __init__(self, python_path: str):
        """Initialize with the path to the Python interpreter.
        
        Args:
            python_path: Path to the Python executable (e.g., '/path/to/venv/bin/python')
        """
        self.python_path = python_path

    def run_python_m(self, module_name: str, *args: str, encoding: str = 'utf-8') -> tuple[str, str]:
        """Run a Python module using the -m flag.
        
        Args:
            module_name: Name of the module to run (e.g., 'pip', 'mypy')
            *args: Additional arguments to pass to the module
            encoding: Text encoding for stdout/stderr (default: 'utf-8')
            
        Returns:
            Tuple of (stdout, stderr) as decoded strings
            
        Raises:
            RuntimeError: If the command fails (non-zero return code)
        """
        cmd = [self.python_path, '-m', module_name] + list(args)
        process = Popen(cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode(encoding) if stderr else f"Module '{module_name}' failed with return code {process.returncode}"
            raise RuntimeError(f"Failed to run Python module '{module_name}': {error_msg}")
        
        return stdout.decode(encoding), stderr.decode(encoding)

    def run_python_script(self, script_path: str, *args: str, encoding: str = 'utf-8') -> tuple[str, str]:
        """Run a Python script file.
        
        Args:
            script_path: Path to the Python script file
            *args: Additional arguments to pass to the script
            encoding: Text encoding for stdout/stderr (default: 'utf-8')
            
        Returns:
            Tuple of (stdout, stderr) as decoded strings
            
        Raises:
            RuntimeError: If the command fails (non-zero return code)
        """
        cmd = [self.python_path, script_path] + list(args)
        process = Popen(cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode(encoding) if stderr else f"Script '{script_path}' failed with return code {process.returncode}"
            raise RuntimeError(f"Failed to run Python script '{script_path}': {error_msg}")
        
        return stdout.decode(encoding), stderr.decode(encoding)

    def run_python_code(self, code: str, encoding: str = 'utf-8') -> tuple[str, str]:
        """Run Python code directly using the -c flag.
        
        Args:
            code: Python code string to execute
            encoding: Text encoding for stdout/stderr (default: 'utf-8')
            
        Returns:
            Tuple of (stdout, stderr) as decoded strings
            
        Raises:
            RuntimeError: If the command fails (non-zero return code)
        """
        cmd = [self.python_path, '-c', code]
        process = Popen(cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode(encoding) if stderr else f"Python code execution failed with return code {process.returncode}"
            raise RuntimeError(f"Failed to run Python code: {error_msg}")
        
        return stdout.decode(encoding), stderr.decode(encoding)