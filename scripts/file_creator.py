def create_large_file(file_path, size_gb):
    size_bytes = size_gb * 1024 * 1024 * 1024  # Convert GB to bytes
    chunk_size = 1024 * 1024  # 1 MB chunk size

    with open(file_path, 'wb') as file:
        for _ in range(size_bytes // chunk_size):
            file.write(b'\0' * chunk_size)

        # Write the remaining bytes (if any)
        remaining_bytes = size_bytes % chunk_size
        file.write(b'\0' * remaining_bytes)

if __name__ == "__main__":
    file_path = "test_file.bin"  # Change this to the desired file path
    size_gb = 10  # Change this to the desired file size in GB

    create_large_file(file_path, size_gb)
    print(f"File '{file_path}' created with size {size_gb} GB.")
