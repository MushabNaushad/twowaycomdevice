#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_samples.py
===================
Generates valid test files across 4 distinct media types:
1. sample_memo.txt      (Text)
2. sample_photo.png     (Image)
3. sample_voice.wav     (Audio)
4. sample_document.pdf  (PDF Document)
"""

import os, struct, math, wave

SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sample_data'))
os.makedirs(SAMPLE_DIR, exist_ok=True)

# 1. Text Memo
memo_text = """========================================
RADIO COMMUNICATION LOG & MEMO
Node ID: 1 -> Node ID: 2
Date: 2026-08-24
Topic: In-Band Transport Protocol Verification
========================================
All packets are now serialized with the 18-byte
in-band binary transport header. Selective-Repeat
ARQ is active with window scaling.

Checklist:
[x] 8-Byte Application Header
[x] In-Band 18-Byte Transport Protocol Header
[x] Hot-Folder Daemon Interface
[x] Multi-Media Verification (PDF, Image, Audio, Text)

End of transmission.
"""
with open(os.path.join(SAMPLE_DIR, 'sample_memo.txt'), 'w', encoding='utf-8') as f:
    f.write(memo_text)

# 2. Valid Audio WAV File (8kHz mono tone/chirp, 2 seconds)
wav_path = os.path.join(SAMPLE_DIR, 'sample_voice.wav')
with wave.open(wav_path, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2) # 16-bit
    wf.setframerate(8000)
    samples = []
    for i in range(16000): # 2 seconds
        t = i / 8000.0
        env = math.sin(math.pi * t / 2.0)
        val = int(env * 16000.0 * math.sin(2.0 * math.pi * (440.0 + 200.0 * t) * t))
        samples.append(val)
    raw_audio = struct.pack('<' + str(len(samples)) + 'h', *samples)
    wf.writeframes(raw_audio)

# 3. Valid Test PNG Image (120x120 RGBA badge)
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (160, 120), color=(20, 28, 45))
    d = ImageDraw.Draw(img)
    d.rectangle([5, 5, 155, 115], outline=(80, 160, 255), width=3)
    d.text((25, 40), 'CDP RADIO', fill=(255, 215, 0))
    d.text((35, 65), 'NODE 1 -> 2', fill=(100, 240, 150))
    img.save(os.path.join(SAMPLE_DIR, 'sample_photo.png'), format='PNG')
except Exception:
    # Fallback raw PNG binary
    png_bytes = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
        0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00, 0x20,
        0x08, 0x02, 0x00, 0x00, 0x00, 0xFC, 0x18, 0xED, 0xA3, 0x00, 0x00, 0x00,
        0x19, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x63, 0xF8, 0xCF, 0xC0, 0xC0,
        0xC0, 0x00, 0x03, 0x03, 0x03, 0x00, 0x00, 0x05, 0x00, 0x01, 0x0D, 0x0A,
        0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42,
        0x60, 0x82
    ])
    with open(os.path.join(SAMPLE_DIR, 'sample_photo.png'), 'wb') as f:
        f.write(png_bytes)

# 4. Valid PDF Document
pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 170 >>
stream
BT
/F1 18 Tf
50 720 Td
(CDP RADIO TRANSPORT PROTOCOL REPORT) Tj
/F1 12 Tf
0 -30 Td
(Document Type: Standard PDF over In-Band Transport Protocol) Tj
0 -20 Td
(Transmission State: 100% Reliable Delivery Confirmed) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000465 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
546
%%EOF
"""
with open(os.path.join(SAMPLE_DIR, 'sample_document.pdf'), 'wb') as f:
    f.write(pdf_content)

if __name__ == '__main__':
    print("Generated sample dataset in:", SAMPLE_DIR)
    for fn in sorted(os.listdir(SAMPLE_DIR)):
        fp = os.path.join(SAMPLE_DIR, fn)
        print(f"  {fn:<24} : {os.path.getsize(fp):>7} bytes")
