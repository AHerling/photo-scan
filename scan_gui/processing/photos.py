"""Photograph detection and cropping — milestone 4.

A direct port of the embedded Python block from scan.sh: threshold the scan,
find photo-shaped contours, perspective-crop each one, save as sequential
JPGs. Pure functions (numpy/cv2 in, images out) so it stays unit-testable.
"""
