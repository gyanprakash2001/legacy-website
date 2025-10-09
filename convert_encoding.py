import os

def convert_to_utf8(filename, input_encoding='utf-16'):
    # 1. Define the temporary output filename
    output_filename = filename + '.utf8'
    print(f"Attempting to convert {filename} from {input_encoding} to utf-8...")

    try:
        # 2. Read the file using the problematic encoding (e.g., utf-16)
        with open(filename, 'r', encoding=input_encoding) as infile:
            content = infile.read()

        # 3. Write the content to a new file using the correct UTF-8 encoding
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            outfile.write(content)

        # 4. Rename the files to complete the switch
        os.replace(output_filename, filename)
        print("Conversion successful. File is now UTF-8.")

    except UnicodeDecodeError:
        print(f"Error: Could not decode the file using '{input_encoding}'. Try 'latin-1'.")
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")

# Run the function
convert_to_utf8('data.json')