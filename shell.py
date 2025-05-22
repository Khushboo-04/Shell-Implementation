import os
import sys
import shlex
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import cpuinfo
import glob

# ------------------------------
# Command history support
# ------------------------------
history = []
history_index = -1

# ------------------------------
# Tab completion logic
# ------------------------------
def autocomplete(event):
    current = entry.get()
    cursor_pos = entry.index(tk.INSERT)
    text = current[:cursor_pos]

    if not text.strip():
        return "break"

    parts = shlex.split(text)
    if not parts:
        return "break"

    last = parts[-1]

    # Check for file completions
    matches = glob.glob(last + '*')

    # If no files, try commands from PATH
    if not matches and not os.path.sep in last:
        paths = os.environ.get("PATH", "").split(os.pathsep)
        seen = set()
        for path in paths:
            try:
                for item in os.listdir(path):
                    full_path = os.path.join(path, item)
                    if os.access(full_path, os.X_OK) and item.startswith(last) and item not in seen:
                        matches.append(item)
                        seen.add(item)
            except FileNotFoundError:
                continue

    if len(matches) == 1:
        completion = matches[0]
        if not last.startswith('"') and ' ' in completion:
            completion = f'"{completion}"'
        new_text = text[:-len(last)] + completion
        entry.delete(0, tk.END)
        entry.insert(0, new_text)
        entry.icursor(len(new_text))
    elif len(matches) > 1:
        output_box.insert(tk.END, "\n".join(matches) + "\n")
        output_box.see(tk.END)

    return "break"

# ------------------------------
# Shell command execution
# ------------------------------

def parse_command(command):
    input_file = None
    output_file = None

    if '<' in command:
        command, input_file = command.split('<', 1)
        input_file = input_file.strip()

    if '>' in command:
        command, output_file = command.split('>', 1)
        output_file = output_file.strip()

    parts = [part.strip() for part in command.strip().split('|')]
    return parts, input_file, output_file

def run_command(command_parts, input_file=None, output_file=None, capture=False):
    processes = []
    prev_pipe = None
    final_output = ""

    for i, part in enumerate(command_parts):
        args = shlex.split(part)
        if not args:
            continue

        stdin = prev_pipe
        stdout = subprocess.PIPE if i < len(command_parts) - 1 or capture else None

        if i == 0 and input_file:
            try:
                stdin = open(input_file, 'r')
            except FileNotFoundError:
                return f"Input file not found: {input_file}"

        if i == len(command_parts) - 1 and output_file:
            stdout = open(output_file, 'w')

        try:
            process = subprocess.Popen(
                part,
                shell=True,
                stdin=stdin,
                stdout=stdout,
                stderr=subprocess.PIPE
            )
            processes.append(process)

            if prev_pipe and prev_pipe != sys.stdin:
                prev_pipe.close()

            if stdout == subprocess.PIPE:
                prev_pipe = process.stdout

        except Exception as e:
            return f"Error running command: {e}"

    for p in processes:
        output, error = p.communicate()
        if capture and output:
            final_output += output.decode()
        if error:
            final_output += error.decode()

    return final_output.strip()

# ------------------------------
# GUI Setup
# ------------------------------

def show_cpu_info():
    info = cpuinfo.get_cpu_info()
    cpu_details = f"""
CPU: {info.get('brand_raw', 'Unknown')}
Architecture: {info.get('arch_string_raw', 'Unknown')}
Cores: {info.get('count', 'Unknown')}
Bits: {info.get('bits', 'Unknown')}
    """.strip()
    messagebox.showinfo("CPU Information", cpu_details)

def on_enter(event=None):
    global history, history_index
    command = entry.get().strip()
    if not command:
        return

    history.append(command)
    history_index = len(history)

    output_box.insert(tk.END, f"> {command}\n")
    output_box.see(tk.END)
    entry.delete(0, tk.END)

    def run_and_display():
        command_parts, input_file, output_file = parse_command(command)
        result = run_command(command_parts, input_file, output_file, capture=True)
        if result:
            output_box.insert(tk.END, result + "\n")
        output_box.see(tk.END)

    threading.Thread(target=run_and_display, daemon=True).start()

def on_key_up(event):
    global history_index
    if history and history_index > 0:
        history_index -= 1
        entry.delete(0, tk.END)
        entry.insert(0, history[history_index])

def on_key_down(event):
    global history_index
    if history and history_index < len(history) - 1:
        history_index += 1
        entry.delete(0, tk.END)
        entry.insert(0, history[history_index])
    else:
        entry.delete(0, tk.END)
        history_index = len(history)

# ------------------------------
# Build GUI Window
# ------------------------------

root = tk.Tk()
root.title("Custom Shell GUI")
root.geometry("700x500")

entry = tk.Entry(root, font=("Consolas", 12))
entry.pack(fill=tk.X, padx=10, pady=5)
entry.bind("<Return>", on_enter)
entry.bind("<Up>", on_key_up)
entry.bind("<Down>", on_key_down)
entry.bind("<Tab>", autocomplete)

output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Consolas", 12))
output_box.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

cpu_button = tk.Button(root, text="Show CPU Info", command=show_cpu_info)
cpu_button.pack(pady=5)

output_box.insert(tk.END, "Welcome to My Custom Shell GUI!\nType your command and press Enter.\n\n")
entry.focus()

root.mainloop()
