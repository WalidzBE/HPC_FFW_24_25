/**********************************************************************
 * Gaussian Blur Image Processing with CUDA
 * Applies a 3x3 Gaussian blur to RGB images
 *********************************************************************/
#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <iostream>

#ifndef BLOCK_SIZE
#define BLOCK_SIZE 32  // Default size for thread blocks
#endif

// Gaussian kernel weights stored in constant GPU memory
__constant__ int gaussian_kernel_weights[9] = {1, 2, 1, 
                                               3, 4, 3, 
                                               1, 2, 1};

// Mirror device to handle boundaries
__device__ int mirror(int x, int max) {
    if (x < 0) return -x;            // mirror -1 to 1
    if (x >= max) return 2 * max - x - 2; // mirror N to N-2
    return x;
}
    
/* --- CUDA kernel for applying 3x3 Gaussian blur ------------------- */
__global__ void applyGaussianBlur(const uchar3 *input_image, uchar3 *output_image,
                                 int image_width, int image_height, 
                                 size_t memory_pitch, int row_stride)
{
    // Shared memory for storing image tile with halo pixels
    __shared__ unsigned char shared_tile[(BLOCK_SIZE+2)*(BLOCK_SIZE+2)*3];

    // Calculate global pixel coordinates
    int global_x = blockIdx.x * blockDim.x + threadIdx.x;
    int global_y = blockIdx.y * blockDim.y + threadIdx.y;

    // Calculate local coordinates within shared memory (including halo)
    int local_x = threadIdx.x + 1;
    int local_y = threadIdx.y + 1;

    // Fill shared memory tile using mirrored boundary pixels
    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            int src_x = mirror(global_x + dx, image_width);
            int src_y = mirror(global_y + dy, image_height);

            int tile_x = local_x + dx;
            int tile_y = local_y + dy;

            if (tile_x >= 0 && tile_x < BLOCK_SIZE + 2 && tile_y >= 0 && tile_y < BLOCK_SIZE + 2) {
                *(uchar3*)&shared_tile[(tile_y * (BLOCK_SIZE + 2) + tile_x) * 3] =
                    input_image[src_y * row_stride + src_x];
            }
        }
    }

    // Ensure all threads have finished copying their portion of the image into shared memory and halo Pixels are visible to all other threads before the computation begins
    __syncthreads();
    
    // Apply Gaussian blur if within image bounds
    if (global_x < image_width && global_y < image_height) 
    {
        // Initialize sum for RGB channels
        int3 channel_sums = {0, 0, 0};
        
        // Apply 3x3 kernel weights to surrounding pixels
        for (int kernel_y = -1; kernel_y <= 1; ++kernel_y)
        {
            for (int kernel_x = -1; kernel_x <= 1; ++kernel_x) 
            {
                uchar3 pixel = *(uchar3*)&shared_tile[((local_y+kernel_y)*(BLOCK_SIZE+2)+local_x+kernel_x)*3];
                int weight = gaussian_kernel_weights[(kernel_y+1)*3 + (kernel_x+1)];
                channel_sums.x += weight * pixel.x;
                channel_sums.y += weight * pixel.y;
                channel_sums.z += weight * pixel.z;
            }
        }
        
        // Normalize and store result
        uchar3 result_pixel;
        const int normalization_factor = 18;
        const int rounding_offset = 9;
        result_pixel.x = static_cast<unsigned char>((channel_sums.x + rounding_offset) / normalization_factor);
        result_pixel.y = static_cast<unsigned char>((channel_sums.y + rounding_offset) / normalization_factor);
        result_pixel.z = static_cast<unsigned char>((channel_sums.z + rounding_offset) / normalization_factor);
        output_image[global_y*row_stride + global_x] = result_pixel;
    }
}

/* --------------------------- Main Program --------------------------- */
int main(int argc, char **argv)
{
    // Check command line arguments
    if (argc != 4) 
    {
        std::cerr << "Usage: program_name input_image.png output_image.png log_label\n";
        return 1;
    }


    // Load input image
    cv::Mat input_image = cv::imread(argv[1], cv::IMREAD_COLOR);
    if (input_image.empty()) 
    {
        std::cerr << "Error: Could not load input image\n"; 
        return 1;
    }

    // Get image dimensions
    int image_width = input_image.cols;
    int image_height = input_image.rows;
    size_t memory_pitch = static_cast<size_t>(image_width) * sizeof(uchar3);

    // Allocate GPU memory
    uchar3 *device_input_image, *device_output_image;
    cudaMalloc(&device_input_image, image_height * memory_pitch);
    cudaMalloc(&device_output_image, image_height * memory_pitch);
    cudaMemcpy(device_input_image, input_image.ptr(), image_height * memory_pitch, cudaMemcpyHostToDevice);

    // Setup CUDA grid and block dimensions
    dim3 thread_block(BLOCK_SIZE, BLOCK_SIZE);
    dim3 grid_dimensions((image_width + BLOCK_SIZE-1)/BLOCK_SIZE, (image_height + BLOCK_SIZE-1)/BLOCK_SIZE);


    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    cudaEventRecord(start);

    // Apply Gaussian blur
    applyGaussianBlur<<<grid_dimensions, thread_block>>>(device_input_image, device_output_image, 
                                                       image_width, image_height, memory_pitch, image_width);

    // Copy result back to host and save
    cv::Mat output_image(input_image.size(), input_image.type());
    cudaMemcpy(output_image.ptr(), device_output_image, image_height * memory_pitch, cudaMemcpyDeviceToHost);

    // Check output file extension before saving
    std::string out_file = argv[2];
    std::string ext = out_file.substr(out_file.find_last_of('.') + 1);
    std::vector<std::string> supported_ext = {"png", "jpg", "jpeg", "bmp", "tiff", "tif"};

    if (out_file == "null") {
        std::cout << "Output file is 'null', skipping save." << std::endl;
    }
    else if (std::find(supported_ext.begin(), supported_ext.end(), ext) == supported_ext.end()) {
        std::cerr << "Error: Unsupported output file extension: " << ext << std::endl;
        std::cerr << "Supported extensions: png, jpg, jpeg, bmp, tiff, tif" << std::endl;
    }
    else {
        cv::imwrite(out_file, output_image);
    }
    cudaEventRecord(stop);

    cudaEventSynchronize(stop);
    float milliseconds = 0;
    cudaEventElapsedTime(&milliseconds, start, stop);

    printf("Block size: %d x %d | Time: %f ms\n", BLOCK_SIZE, BLOCK_SIZE, milliseconds);


    // Append to CSV
    FILE* f = fopen("results.csv", "a");
    if (f != NULL) {
        fprintf(f, "BASIC,%s,%d,%f\n", argv[3], BLOCK_SIZE, milliseconds);
        fclose(f);
    } else {
        fprintf(stderr, "Failed to write to results.csv\n");
    }

    // Cleanup
    cudaFree(device_input_image); 
    cudaFree(device_output_image);
    return 0;
}