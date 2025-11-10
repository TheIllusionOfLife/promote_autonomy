#!/bin/bash
# Generate PNG from SVG architecture diagram
# This script tries multiple methods to convert the SVG to high-resolution PNG

set -euo pipefail

SVG_FILE="architecture-diagram.svg"
PNG_FILE="architecture-diagram.png"
WIDTH=2400  # High resolution for crisp text

# Validate input file exists
if [[ ! -f "$SVG_FILE" ]]; then
    echo "❌ Error: SVG file not found at '$SVG_FILE'" >&2
    echo "Please run this script from the repository root directory." >&2
    exit 1
fi

echo "🎨 Converting architecture diagram to PNG..."

# Method 1: Try Inkscape (best quality)
if command -v inkscape &> /dev/null; then
    echo "✓ Using Inkscape for conversion..."
    inkscape "$SVG_FILE" --export-filename="$PNG_FILE" --export-width=$WIDTH
    echo "✅ PNG generated successfully: $PNG_FILE"
    exit 0
fi

# Method 2: Try rsvg-convert (good quality)
if command -v rsvg-convert &> /dev/null; then
    echo "✓ Using rsvg-convert for conversion..."
    rsvg-convert -w $WIDTH "$SVG_FILE" -o "$PNG_FILE"
    echo "✅ PNG generated successfully: $PNG_FILE"
    exit 0
fi

# Method 3: Try ImageMagick (acceptable quality)
if command -v convert &> /dev/null; then
    echo "✓ Using ImageMagick for conversion..."
    convert -background white -density 300 "$SVG_FILE" -resize ${WIDTH}x "$PNG_FILE"
    echo "✅ PNG generated successfully: $PNG_FILE"
    exit 0
fi

# Method 4: Try Cairo (acceptable quality)
if command -v cairosvg &> /dev/null; then
    echo "✓ Using CairoSVG for conversion..."
    cairosvg "$SVG_FILE" -o "$PNG_FILE" -W $WIDTH
    echo "✅ PNG generated successfully: $PNG_FILE"
    exit 0
fi

# No converters found
echo "❌ No SVG to PNG converter found!"
echo ""
echo "Please install one of the following:"
echo "  • Inkscape (recommended): sudo apt-get install inkscape"
echo "  • rsvg-convert: sudo apt-get install librsvg2-bin"
echo "  • ImageMagick: sudo apt-get install imagemagick"
echo "  • CairoSVG: pip install cairosvg"
echo ""
echo "Or use an online converter:"
echo "  • https://cloudconvert.com/svg-to-png"
echo "  • Upload: $SVG_FILE"
echo "  • Set width to: ${WIDTH}px"
echo "  • Download as: $PNG_FILE"
echo ""
exit 1
