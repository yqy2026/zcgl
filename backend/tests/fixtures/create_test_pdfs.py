"""
Create minimal PDF test files for edge case testing
"""

import os


def create_minimal_pdf(
    filepath,
    content=b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [3 0 R]\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n200\n%%EOF",
):
    """Create a minimal PDF file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(content)
    print(f"Created: {filepath}")


def create_zero_byte_pdf(filepath):
    """Create an empty PDF file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb"):
        pass  # Empty file
    print(f"Created: {filepath}")


def create_fake_txt_with_pdf_extension(filepath):
    """Create a text file with .pdf extension"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("This is not a PDF file.\nIt's just plain text.")
    print(f"Created: {filepath}")


if __name__ == "__main__":
    fixtures_dir = "tests/fixtures"

    # Create various test PDFs
    test_files = [
        ("protected.pdf", "Minimal PDF for password protection test"),
        ("large.pdf", "Minimal PDF for size limit test"),
        ("unsupported.pdf", "Minimal PDF for unsupported features test"),
        ("disk_full.pdf", "Minimal PDF for disk space test"),
    ]

    for filename, description in test_files:
        filepath = os.path.join(fixtures_dir, filename)
        create_minimal_pdf(filepath)
        print(f"  - {description}")

    # Zero byte PDF
    create_zero_byte_pdf(os.path.join(fixtures_dir, "empty.pdf"))

    # Fake PDF with .pdf extension
    create_fake_txt_with_pdf_extension(os.path.join(fixtures_dir, "fake.pdf"))

    print("\nAll test PDF files created successfully!")
