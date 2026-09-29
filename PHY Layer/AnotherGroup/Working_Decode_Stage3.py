import os
from collections import Counter

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

decoded_payloads = []

for chunk in chunks:
    # Ignore empty or severely truncated chunks that don't have at least 1 byte
    if len(chunk) < 8: 
        continue
        
    decoded_chars = []
    
    # Process the entire length of the chunk dynamically
    for i in range(0, len(chunk) - 7, 8):
        char_val = int(chunk[i:i + 8], 2)
        if 32 <= char_val <= 126:
            decoded_chars.append(chr(char_val))
            
    text = "".join(decoded_chars)
    
    if text:
        decoded_payloads.append(text)

print("\n--- Live Decoded Payload ---")
if decoded_payloads:
    # Count all occurrences of each decoded string
    payload_counts = Counter(decoded_payloads)
    
    # Get the most common one
    most_common_payload = payload_counts.most_common(1)[0][0]
    
    print(most_common_payload)
else:
    print("No valid payloads decoded. Check SDR lock.")
print("-----------------------------\n")
