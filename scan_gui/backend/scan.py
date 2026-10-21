"""Scan execution — milestone 3.

ScanJob will wrap `scanimage` in a QProcess: stream progress from stderr into
a signal, support cancel() via kill(), and keep the raw TIFF naming/numbering
logic that lived in scan.sh.
"""
