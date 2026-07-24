"""CI script: validate coverage threshold from coverage.xml."""
import xml.etree.ElementTree as ET
import sys

try:
    tree = ET.parse("coverage.xml")
    root = tree.getroot()
    rate = float(root.attrib.get("line-rate", "0"))
    pct = int(rate * 100)
    print(f"Coverage: {pct}%")
    if pct < 35:
        print("Coverage below threshold of 35%")
        sys.exit(1)
    else:
        print("Coverage passes threshold (>=35%)")
except FileNotFoundError:
    print("coverage.xml not found, skipping coverage validation")