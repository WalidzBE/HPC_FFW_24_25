import numpy as np

def gaussian_blur(matrix, mode='reflect'):
    """
    Applies 3x3 Gaussian blur to a matrix.
    
    Returns:
        Blurred matrix of the same shape.
    """
    kernel = np.array([
        [1, 2, 1],
        [3, 4, 3],
        [1, 2, 1]
    ])  # Sum = 18
    
    # Pad the matrix based on the border mode
    padded = np.pad(matrix, 1, mode=mode)
    blurred = np.zeros_like(matrix, dtype=np.float32)
    
    for y in range(matrix.shape[0]):
        for x in range(matrix.shape[1]):
            # Extract 3x3 neighborhood
            neighborhood = padded[y:y+3, x:x+3]
            # Apply kernel and normalize
            blurred[y, x] = (np.sum(neighborhood * kernel) + 9) // 18
    
    return blurred.astype(np.uint8)  # Convert back to integer

# Example Usage
input_matrix = np.array(
    np.array([
     148,153,158,255,128,
     149,0,0,212,0,255,
     149,255,127,168,
     167,204,120,0,145
]).reshape(4,5), dtype=np.uint8)

# Apply Gaussian blur
blurred_matrix = gaussian_blur(input_matrix, mode='reflect')
print("Original:\n", input_matrix)
print("Blurred:\n", blurred_matrix)