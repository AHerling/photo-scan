"""QRunnable wrapper for processing/photos.py — milestone 4.

Runs the OpenCV detection/crop in a QThreadPool so the UI never blocks on a
1200 DPI TIFF, and reports results back over Qt signals.
"""
