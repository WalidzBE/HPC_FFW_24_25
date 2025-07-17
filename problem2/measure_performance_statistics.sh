#!/bin/bash

# Setup directories
INPUT_DIR="./input/performance"
BASE_OUTPUT_DIR="$(pwd)/output/performance"

# Hardcoded CU file
CU_FILE="channel_thread.cu"
EXECUTABLE="$(basename "$CU_FILE" .cu)"

# CU-file-specific output directory
CU_OUTPUT_DIR="$BASE_OUTPUT_DIR/$EXECUTABLE"
NSYS_DIR="$CU_OUTPUT_DIR"

# Create output directories
mkdir -p "$CU_OUTPUT_DIR"
mkdir -p "$NSYS_DIR"

# Process each image in the input directory
for image_path in "$INPUT_DIR"/*.jpg; do
    if [ ! -f "$image_path" ]; then
        continue
    fi
    
    filename=$(basename "$image_path")
    echo -e "\nProcessing image: $filename"
    
    # Create image-specific output directory inside CU_OUTPUT_DIR
    image_output_dir="$CU_OUTPUT_DIR/${filename%.*}"
    mkdir -p "$image_output_dir"

    for block_size in 4 8 16 32; do
        echo -e "\nCompiling with BLOCK_SIZE=$block_size ..."
        nvcc -DBLOCK_SIZE=$block_size -O3 -std=c++17 -Xcompiler -fopenmp \
        -I/usr/include/opencv4 \
        -L/usr/lib/x86_64-linux-gnu \
        -lopencv_core -lopencv_imgcodecs -lopencv_highgui -lopencv_imgproc \
        -o "$EXECUTABLE" "$CU_FILE"

        echo -e "\nRun with block size $block_size"
        
        # Create block size specific output directory inside image_output_dir
        block_size_output_dir="$image_output_dir/block_size$block_size"
        mkdir -p "$block_size_output_dir"
        
        # NSYS profile path inside CU_OUTPUT_DIR
        nsys_profile="$NSYS_DIR/${filename%.*}_block_size${block_size}"
        results="$NSYS_DIR/results/"
        mkdir -p "${results}"

        # Run 5 times
        for run_id in {1..5}; do
            echo "Running with nsys profiling... (Run $run_id)"
            nsys profile \
                --trace=cuda \
                --cuda-memory-usage=true \
                -o "${nsys_profile}_run${run_id}" \
                --force-overwrite true \
                ./"$EXECUTABLE" "$image_path" "null" "$filename"

            # Process the profile to extract metrics
            echo "Extracting performance metrics for run $run_id..."
            nsys stats -f csv -o "${results}/${filename%.*}_block_size${block_size}_run${run_id}" -r gputrace,gpumemsizesum "${nsys_profile}_run${run_id}.nsys-rep"

            echo "Profile saved to: ${nsys_profile}_run${run_id}.qdrep"
        done
    done
done

echo -e "\nAll runs completed."
