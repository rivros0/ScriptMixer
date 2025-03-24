import os

def update_directory_listing(directory, entry_extension, report_text):
    report_text.delete("1.0", "end")
    file_extension = entry_extension.get().strip()
    if file_extension != '' and not file_extension.startswith('.'):
        file_extension = f".{file_extension}"
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file_extension == '' or file.endswith(file_extension):
                file_path = os.path.join(root, file)
                report_text.insert("end", f"{file_path}\n")

def update_subdirectories_list(selected_directory, tree, entry_extension):
    subdirectories = [d for d in os.listdir(selected_directory) if os.path.isdir(os.path.join(selected_directory, d))]
    subdirectories.sort()
    tree.delete(*tree.get_children())
    for subdir in subdirectories:
        check_directory_content(selected_directory, subdir, tree, entry_extension)

def check_directory_content(base_directory, subdir, tree, entry_extension):
    full_path = os.path.join(base_directory, subdir)
    num_folders, num_files, num_extension_files, extension_files = count_directory_content(full_path, entry_extension)
    mix_file_path = os.path.join(base_directory, "00_MixOutput", f"{subdir}_mix.txt")
    if os.path.exists(mix_file_path):
        button_text = "CopiaInClipboard"
    else:
        button_text = "-----"
    tree.insert("", "end", values=(subdir, num_folders, num_files, num_extension_files, ", ".join(extension_files), button_text))


def count_directory_content(directory, entry_extension):
    num_folders = 0
    num_files = 0
    num_extension_files = 0
    extension_files = []
    for root, dirs, files in os.walk(directory):
        num_folders += len(dirs)
        num_files += len(files)
        current_extension_files = [f for f in files if f.endswith(entry_extension.get())]
        num_extension_files += len(current_extension_files)
        extension_files += current_extension_files
    return num_folders, num_files, num_extension_files, extension_files
