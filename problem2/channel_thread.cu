/**********************************************************************
 * Gaussian Blur Image Processing with CUDA
 * Applies a 3x3 Gaussian blur with channel-specific threads
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
    if (x < 0) return -x;
    if (x >= max) return 2 * max - x - 2;
    return x;
}

/* --- CUDA kernel for applying 3x3 Gaussian blur ------------------- */
__global__ void applyGaussianBlur(const uchar3 *input_image, uchar3 *output_image,
                                int image_width, int image_height, 
                                size_t memory_pitch, int row_stride)
{
    // Shared memory for storing image tile with halo pixels
    __shared__ uchar3 shared_tile[(BLOCK_SIZE+2)*(BLOCK_SIZE+2)];

    // Calculate global pixel coordinates and channel
    int global_x = blockIdx.x * blockDim.x + threadIdx.x;
    int global_y = blockIdx.y * blockDim.y + threadIdx.y;
    int channel = threadIdx.z;  // 0=R, 1=G, 2=B

    // Calculate local coordinates within shared memory (including halo)
    int local_x = threadIdx.x + 1;
    int local_y = threadIdx.y + 1;

    // Fill shared memory tile using mirrored boundary pixels
    // Only need to load once per pixel (all threads in block cooperate)
    if (channel == 0) {  // Only first channel thread loads the pixel
        for (int dy = -1; dy <= 1; ++dy) {
            for (int dx = -1; dx <= 1; ++dx) {
                int src_x = mirror(global_x + dx, image_width);
                int src_y = mirror(global_y + dy, image_height);

                int tile_x = local_x + dx;
                int tile_y = local_y + dy;

                if (tile_x >= 0 && tile_x < BLOCK_SIZE + 2 && tile_y >= 0 && tile_y < BLOCK_SIZE + 2) {
                    shared_tile[tile_y * (BLOCK_SIZE + 2) + tile_x] = input_image[src_y * row_stride + src_x];
                }
            }
        }
    }
    __syncthreads();
    
    // Apply Gaussian blur if within image bounds
    if (global_x < image_width && global_y < image_height) 
    {
        int channel_sum = 0;
        
        // Apply 3x3 kernel weights to surrounding pixels for this channel
        for (int kernel_y = -1; kernel_y <= 1; ++kernel_y) {
            for (int kernel_x = -1; kernel_x <= 1; ++kernel_x) {
                uchar3 pixel = shared_tile[(local_y + kernel_y) * (BLOCK_SIZE + 2) + (local_x + kernel_x)];
                int weight = gaussian_kernel_weights[(kernel_y+1)*3 + (kernel_x+1)];
                
                // Each thread only processes its assigned channel
                if (channel == 0) channel_sum += weight * pixel.x;
                else if (channel == 1) channel_sum += weight * pixel.y;
                else if (channel == 2) channel_sum += weight * pixel.z;
            }
        }
        
        // Normalize result for this channel
        const int normalization_factor = 18;
        const int rounding_offset = 9;
        unsigned char result = static_cast<unsigned char>((channel_sum + rounding_offset) / normalization_factor);
        
        // Store result using thread cooperation (no atomics needed)
        __shared__ uchar3 temp_results[BLOCK_SIZE][BLOCK_SIZE];
        
        // Each thread stores its channel result to shared memory
        if (channel == 0) temp_results[threadIdx.y][threadIdx.x].x = result;
        else if (channel == 1) temp_results[threadIdx.y][threadIdx.x].y = result;
        else if (channel == 2) temp_results[threadIdx.y][threadIdx.x].z = result;
        
        __syncthreads();
        
        // First channel thread writes the complete pixel
        if (channel == 0) {
            output_image[global_y * row_stride + global_x] = temp_results[threadIdx.y][threadIdx.x];
        }
    }
}

/* --------------------------- Main Program --------------------------- */
#define CUDA_CHECK(err) \
    if (err != cudaSuccess) { \
        std::cerr << "[CUDA ERROR] " << cudaGetErrorString(err) \
                  << " at " << __FILE__ << ":" << __LINE__ << std::endl; \
        exit(EXIT_FAILURE); \
    }

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
    CUDA_CHECK(cudaMalloc(&device_input_image, image_height * memory_pitch));
    CUDA_CHECK(cudaMalloc(&device_output_image, image_height * memory_pitch));
    CUDA_CHECK(cudaMemcpy(device_input_image, input_image.ptr(), image_height * memory_pitch, cudaMemcpyHostToDevice));

    std::cout << "[DEBUG] Copied device data to GPU" << std::endl;

    // Setup CUDA grid and block dimensions
    dim3 thread_block(BLOCK_SIZE, BLOCK_SIZE, 3);
    dim3 grid_dimensions((image_width + BLOCK_SIZE-1)/BLOCK_SIZE, (image_height + BLOCK_SIZE-1)/BLOCK_SIZE);

    std::cout << "[DEBUG] Launching kernel with block (" << thread_block.x << ", " << thread_block.y
              << ", " << thread_block.z << ") and grid (" << grid_dimensions.x << ", " << grid_dimensions.y << ")" << std::endl;

    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);

    cudaEventRecord(start);

    // Apply Gaussian blur
    applyGaussianBlur<<<grid_dimensions, thread_block>>>(device_input_image, device_output_image, 
                                                       image_width, image_height, memory_pitch, image_width);

    // Check kernel launch error
    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) {
        std::cerr << "[LAUNCH ERROR] " << cudaGetErrorString(err) << std::endl;
        exit(EXIT_FAILURE);
    }

    // Now check runtime errors
    err = cudaDeviceSynchronize();
    if (err != cudaSuccess) {
        std::cerr << "[RUNTIME ERROR] " << cudaGetErrorString(err) << std::endl;
        exit(EXIT_FAILURE);
    }

    std::cout << "[DEBUG] Kernel completed" << std::endl;

    // Copy result back to host and save
    cv::Mat output_image(input_image.size(), input_image.type());
    CUDA_CHECK(cudaMemcpy(output_image.ptr(), device_output_image, image_height * memory_pitch, cudaMemcpyDeviceToHost));

    std::cout << "[DEBUG] Copied device data back to host" << std::endl;

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
        fprintf(f, "CHANNEL_THREAD,%s,%d,%f\n", argv[3], BLOCK_SIZE, milliseconds);
        fclose(f);
    } else {
        fprintf(stderr, "Failed to write to results.csv\n");
    }

    // Cleanup
    cudaFree(device_input_image); 
    cudaFree(device_output_image);
    return 0;
}