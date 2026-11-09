"""Keep untrusted exported cell text from becoming spreadsheet formulas."""
import csv


def safe_csv_bytes(frame):
    def literal(value):
        if isinstance(value, str) and (value.lstrip().startswith(('=', '+', '-', '@', '＝', '＋', '－', '＠')) or value.startswith(('\t', '\r', '\n'))):
            return '\t' + value
        return value
    safe = frame.map(literal)
    safe.columns = [literal(c) for c in safe.columns]
    return safe.to_csv(index=False, quoting=csv.QUOTE_ALL).encode('utf-8-sig')
