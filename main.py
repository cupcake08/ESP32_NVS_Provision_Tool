#!/usr/bin/env python3

# Author: Ankit Bhankharia + AI

import argparse
import subprocess
import sys
import shlex # Used for safer display of commands
import os
import secrets
import csv
from typing import Optional

KEY_SIZE_BYTES = 16

PYTHON = "python3"

ESP_CMD = [PYTHON, "-m", "esptool"]

files_to_create = ["device.pem.crt", "private.pem.key", "nvs.csv"]


def execute_command(command_list, verbose=False):
    """
    Executes a command list using subprocess.run.

    Args:
        command_list (list): A list containing the command and its arguments.
        verbose (bool): If True, prints the command being executed.

    Returns:
        int: The exit code of the executed command.
    """
    if not command_list:
        print("Error: No command provided.", file=sys.stderr)
        return 1 # Indicate error

    if verbose:
        # Use shlex.join for a safer representation suitable for shell copy-paste (Python 3.8+)
        # For older Python, a simple ' '.join might suffice but is less robust with quotes/spaces
        try:
            # shlex.join is preferred if available (Python 3.8+)
            print(f"[*] Executing: {shlex.join(command_list)}")
        except AttributeError:
             # Fallback for older Python versions
             print(f"[*] Executing: {' '.join(command_list)}")


    try:
        # subprocess.run executes the command
        # - command_list: ensures arguments are passed correctly, avoids shell injection
        # - capture_output=True: captures stdout and stderr
        # - text=True: decodes stdout/stderr as text (utf-8 by default)
        # - check=False: we will check the return code manually
        result = subprocess.run(
            command_list,
            capture_output=True,
            text=True,
            check=False # Don't raise exception on non-zero exit, handle manually
        )

        # Print stdout if it exists
        if result.stdout:
            print("\n--- Standard Output ---")
            print(result.stdout.strip())

        # Print stderr if it exists
        if result.stderr:
            print("\n--- Standard Error ---", file=sys.stderr)
            print(result.stderr.strip(), file=sys.stderr)

        if verbose:
             print(f"\n[*] Command finished with exit code: {result.returncode}")

        return result.returncode

    except FileNotFoundError:
        print(f"Error: Command not found: '{command_list[0]}'", file=sys.stderr)
        return 1 # Indicate error (often 127 for command not found)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return 1 # Indicate general error
    
def generate_aes_key(key_length_bytes: int) -> bytes:
    """
    Generates a cryptographically secure random key of the specified length.

    Args:
        key_length_bytes: The desired key length in bytes (e.g., 16, 24, 32).

    Returns:
        A bytes object containing the random key.
    """
    # secrets.token_bytes uses os.urandom() or equivalent secure source
    return secrets.token_bytes(key_length_bytes)

def put_hardware_version(filepath: str, version: str):
    try:
        with open(filepath, mode='r+', newline='', encoding='utf-8') as csvfile:

            reader = csv.reader(csvfile)

            for row in reader:
                if row[0] == "hv":
                    print("Hardware version key already exists!")
                    return

            row_to_append = ["hv", "data", "string", version]

            # Create a csv writer object
            # quoting=csv.QUOTE_MINIMAL is standard; quotes only fields containing
            # the delimiter, quotechar, or any characters in lineterminator.
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)

            # Write the actual data row
            writer.writerow(row_to_append)

    except IOError as e:
        # Handle potential file system errors (permissions, etc.)
        print(f"Error: Could not write to CSV file '{filepath}'. Reason: {e}", file=sys.stderr)
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

def put_aes_key(filepath: str):
    try:
        with open(filepath, mode='r+', newline='', encoding='utf-8') as csvfile:

            reader = csv.reader(csvfile)

            for row in reader:
                if row[0] == "aes_key":
                    print("AES key already exists!")
                    return
                
            # put the aes key into nvs file
            aes_key = generate_aes_key(KEY_SIZE_BYTES).hex()
            print(f"AES Key: {aes_key}")

            row_to_append = ["aes_key", "data", "string", aes_key]

            # Create a csv writer object
            # quoting=csv.QUOTE_MINIMAL is standard; quotes only fields containing
            # the delimiter, quotechar, or any characters in lineterminator.
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)

            # Write the actual data row
            writer.writerow(row_to_append)

    except IOError as e:
        # Handle potential file system errors (permissions, etc.)
        print(f"Error: Could not write to CSV file '{filepath}'. Reason: {e}", file=sys.stderr)
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
    
def generate_cert_bin(device_mac: str, version: str) -> int:
    try:
        mac = "".join(device_mac.strip().split(':'))
        mac_path = os.path.join("certs", mac)
        csv_path = os.path.join(mac_path ,"nvs.csv")

        print("csv: " + csv_path)

        if not os.path.exists(csv_path):
            raise FileNotFoundError("csv file not found")

        put_aes_key(csv_path)
        put_hardware_version(csv_path, version)
        
        cmd = [
            PYTHON, "cert_gen.py",
            "generate",
            csv_path,
            os.path.join(mac_path, "certs.bin"),
            "16384",
        ]

        print(f"Generating certificate for {mac_path}...")
        exit_code = execute_command(cmd,verbose=True)

        return exit_code
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Suggestion: Generate device folder first")
        print("Commands:")
        print("- (auto-detect) python main.py --port <port> -g")
        print("- (manual)      python main.py --mac <mac> -g")
        return 1
    
def flash_nvs(device_mac: str, port) -> int:
    try:
        mac = "".join(device_mac.strip().split(':'))
        bin_file = os.path.join("certs", mac,"certs.bin")

        if not os.path.exists(bin_file):
            raise FileNotFoundError(f"Binary file '{bin_file}' not found.")
        
        cmd = [
            *ESP_CMD,
            "--port", port,
            "--baud", "115200",
            "write_flash",
            "0x9000",
            bin_file,
        ]

        print(f"Flashing '{bin_file}' to offset 0x9000 on port {port}...")
        code = execute_command(cmd, verbose=True)
        return code
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    
def create_folder_and_files(device_mac: str, file_names: list[str],target_file_for_content: Optional[str] = None) -> bool:
    # --- 1. Create the folder ---
    mac = "".join(device_mac.strip().split(':'))
    folder_path = os.path.join("certs", mac)
    try:
        # os.makedirs creates the directory and any necessary parent directories.
        # exist_ok=True prevents an error if the directory already exists.
        os.makedirs(folder_path, exist_ok=True)
        print(f"Successfully ensured folder exists: '{folder_path}'")
    except OSError as e:
        # Handle errors like permission denied, invalid path components, etc.
        print(f"Error: Could not create folder '{folder_path}'. Reason: {e}", file=sys.stderr)
        return False
    except Exception as e:
        # Catch any other unexpected errors during folder creation
        print(f"An unexpected error occurred creating folder '{folder_path}': {e}", file=sys.stderr)
        return False

    # --- 2. Create the files inside the folder ---
    all_files_created = True
    for filename in file_names:
        # Construct the full path for the file using os.path.join
        # This ensures cross-platform compatibility (handles '/' vs '\')
        file_path = os.path.join(folder_path, filename)

        try:
            # Create an empty file by opening it in write mode ('w')
            # The 'with' statement ensures the file is properly closed even if errors occur.
            # Using 'pass' inside means we just want to create/truncate it.
            with open(file_path, 'w') as f:
                pass  # Just creating the file, no content needed
            print(f"  - Created empty file: '{file_path}'")
        except IOError as e:
            # Handle errors like invalid filename characters, permissions, etc.
            print(f"  - Error: Could not create file '{file_path}'. Reason: {e}", file=sys.stderr)
            all_files_created = False
            # Decide if you want to stop on the first error or try creating others
            # break # Uncomment this line to stop immediately on the first file error
        except Exception as e:
            # Catch any other unexpected errors during file creation
             print(f"  - An unexpected error occurred creating file '{file_path}': {e}", file=sys.stderr)
             all_files_created = False
             # break # Uncomment this line to stop immediately on the first file error

    
    if target_file_for_content and target_file_for_content not in file_names:
        print(f"Warning: Target file '{target_file_for_content}' for content was specified but is not in the list of files to create.", file=sys.stderr)

    if target_file_for_content:
        

        file_path = os.path.join(folder_path, target_file_for_content)

        with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:

            priv_key_path = os.path.join(folder_path, "private.pem.key")
            cert_path = os.path.join(folder_path, "device.pem.crt")

            rows_to_append = [
                ["key","type","encoding","value"],
                ["certs","namespace","",""],
                ["priv_key","file","string", priv_key_path],
                ["certificate","file","string", cert_path],
            ]

            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)

            writer.writerows(rows_to_append)

        print("Written 'nvs.csv'")
    
    return all_files_created

def get_mac_address(port) -> str:
    cmd = [
        *ESP_CMD,
        "--port", port,
        "read_mac",
    ]

    p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE,text=True)

    p2 = subprocess.Popen(["grep", "MAC:"], stdin=p1.stdout,text=True,stdout=subprocess.PIPE)

    p1.stdout.close()

    p1.wait()

    if(p1.returncode == 0):
        stdout, stderr = p2.communicate(timeout=3000)
        p2.wait()
        if stdout:
            mac = stdout.split("MAC: ")[1].strip()
            return mac
        else:
            print("NO MAC Found!")
            return None
    
    return None

def main():
    """
    Parses command-line arguments (--port, --mac, -v) and prints them.
    """
    parser = argparse.ArgumentParser(
        description="A simple Python script to parse specific command-line arguments.",
        epilog="Example: python main.py --port COM20 --mac abcdefghi"
    )

    parser.add_argument(
        "-g", "--generate",
        action="store_true",
        help="Generate device folder"
    )

    # Define the --port argument
    parser.add_argument(
        "--port",
        type=str,                             # Expect an integer value
        help="Specify the target port number." # Help text shown with -h
    )

    # Define the --mac argument
    parser.add_argument(
        "--mac",
        type=str,                             # Expect a string value
        help="Specify the target MAC address." # Help text shown with -h
    )

    #Define the --hv argument
    parser.add_argument(
        "--hv",
        type=str,                             # Expect a string value
        help="Specify the target hardware version." # Help text shown with -h
    )

    # Parse the arguments provided from the command line
    args = parser.parse_args()

    # Print the parsed arguments
    print("--- Arguments ---")
    print(f"Port:    {args.port if args.port is not None else 'Not specified'}")
    print(f"MAC:     {args.mac if args.mac is not None else 'Not specified'}")
    print(f"Generate: {args.generate}")
    print("------------------------")

    if args.port and args.mac and args.hv:
        code = generate_cert_bin(device_mac=args.mac,version=args.hv)

        print()

        if(code == 0):
            flash_nvs(device_mac=args.mac, port=args.port)
    
    elif args.port and args.hv:
        mac = get_mac_address(args.port)
        if mac:
            print("MAC:", mac)
            code = generate_cert_bin(device_mac=mac,version=args.hv)
            if(code == 0):
                flash_nvs(device_mac=mac,port=args.port)
        else:
            print("Device Not Connected!")
    
    elif args.generate and args.mac:
        create_folder_and_files(args.mac, files_to_create, files_to_create[-1])

    elif args.generate and args.port:
        mac = get_mac_address(args.port)
        if mac:
            print("MAC:", mac)
            create_folder_and_files(mac, files_to_create, files_to_create[-1])
        else:
            print("Device Not Connected!")

    elif args.port:
        get_mac_address(args.port)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()