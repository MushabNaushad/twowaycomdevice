import os

filename = "rx_output.txt"

if not os.path.exists(filename):
    print(f"Error: {filename} not found.")
    exit()

with open(filename, "rb") as f:
    raw_data = f.read()

bit_stream = "".join(f"{byte:08b}" for byte in raw_data)
sync_pattern = "01010011011110010110111001100011" # Binary for 'Sync'

# Check inverted phase
if bit_stream.find(sync_pattern) == -1:
    inverted = "".join('1' if b == '0' else '0' for b in bit_stream)
    if inverted.find(sync_pattern) != -1:
        bit_stream = inverted

# Split the entire stream by the Sync word
chunks = bit_stream.split(sync_pattern)

print("\n--- Live Decoded Payloads ---")
for chunk in chunks:
    if len(chunk) < 8: 
        continue
        
    decoded_chars = []
    # Group bits into characters for whatever is left in the chunk
    for i in range(0, len(chunk) - 7, 8):
        char_val = int(chunk[i:i + 8], 2)
        if 32 <= char_val <= 126:
            decoded_chars.append(chr(char_val))
            
    text = "".join(decoded_chars)
    if text:
        print(text)
print("-----------------------------\n")
