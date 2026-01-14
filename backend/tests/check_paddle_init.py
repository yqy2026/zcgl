import paddleocr

print(f"PaddleOCR Path: {paddleocr.__file__}")
print(f"PaddleOCR Dir: {dir(paddleocr)}")

try:
    from paddleocr import PPStructureV3 as PPStructure
    print("Import PPStructureV3: Success")
except ImportError:
    try:
        from paddleocr import PPStructure
        print("Import PPStructure (legacy): Success")
    except ImportError:
        try:
            from paddleocr.ppstructure import PPStructure
            print("Import paddleocr.ppstructure: Success")
        except ImportError as e:
            print(f"All Imports Failed: {e}")
            PPStructure = None
