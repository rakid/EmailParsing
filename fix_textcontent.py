import re
import sys


def fix_textcontent(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern pour trouver TextContent avec le paramètre type
    pattern = r'TextContent\s*\(\s*type\s*=\s*["\'].*?["\']\s*,\s*'

    # Remplacer par TextContent(
    new_content = re.sub(pattern, "TextContent(", content)

    # Sauvegarder les modifications si nécessaire
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed TextContent in {file_path}")
    else:
        print(f"No changes needed in {file_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        fix_textcontent(file_path)
    else:
        print("Please provide a file path as argument")
