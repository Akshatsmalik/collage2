import os
import subprocess


def run_python(working_directory, file_path: str):
    abs_working_dir = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))
    if not abs_file_path.startswith(abs_working_dir):
        return f"Error: {file_path} is not a valid file"
    if not os.path.isfile(abs_file_path):
        return f"Error: {file_path} is not a file"
    if not file_path.endswith(".py"):
        return f"Error: {file_path} is not a python file"
    try:
        output = subprocess.run(
            ["python", abs_file_path],
            cwd=abs_working_dir,
            timeout=30,
            capture_output=True,
            text=True,
        )
        final_string = f"STDOUT:{output.stdout}\nSTDERR:{output.stderr}"
        if output.stdout.strip() == "" and output.stderr.strip() == "":
            final_string = "No output produced"
        if output.returncode != 0:
            final_string += f"\nprocess exited with code {output.returncode}"
        return final_string
    except Exception as e:
        return f"Error executing file {e}"
