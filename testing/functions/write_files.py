import os


def write_files(working_directory, file_path, content):
    abs_working_dir = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))
    if not abs_file_path.startswith(abs_working_dir):
        return f"Error: {file_path} is not a valid file"
    parent_dir = os.path.dirname(abs_file_path)
    if parent_dir and not os.path.isdir(parent_dir):
        try:
            os.makedirs(parent_dir)
        except Exception as e:
            return f"Error: {e}"
    try:
        with open(abs_file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File {file_path} written successfully"
    except Exception as e:
        return f"Error: {e}"
