#!/bin/bash

BASE_DIR="$(pwd)/input"
OUTPUT_DIR="$(pwd)/output"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"


CU_FILE="halo.cu"
EXECUTABLE="halo"

echo "Compiling"
nvcc -O3 -std=c++17 -Xcompiler -fopenmp \
-I/usr/include/opencv4 \
-L/usr/lib/x86_64-linux-gnu \
-lopencv_core -lopencv_imgcodecs -lopencv_highgui -lopencv_imgproc \
-o "$EXECUTABLE" "$CU_FILE"



# Find all .jpg files in BASE_DIR recursively
find "$BASE_DIR" -type f -iname "*.jpg" | while read -r filepath; do
    # Skip files already inside the output directory
    if [[ "$filepath" != *"/output/"* ]]; then
        # Get relative path from BASE_DIR
        relpath="${filepath#$BASE_DIR/}"

        # Compose output path
        outpath="$OUTPUT_DIR/$relpath"

        # Create output directory if it doesn't exist
        mkdir -p "$(dirname "$outpath")"

        echo "Processing: $filepath"
        echo "Output: $outpath"

        # Run the executable (assumed to be in current directory or in PATH)
        ./"$EXECUTABLE" "$filepath" "$outpath"
    fi
done

