# PHY2 - Stage 08: Full BPSK Packet Engine with Protocol Formatter & CRC32

## Objective
Implement end-to-end tagged stream packet framing, CRC32 generation, protocol header formatting, stream multiplexing, access code correlation, bit repacking, and CRC32 verification.

## Flowgraph Architecture
```
TX PIPELINE:
[ Vector Source (Payload) ]
       ↓
[ Stream to Tagged Stream ] (packet_len=payload_size)
       ↓
[ CRC32 Generator ] (Appends 4-byte IEEE 802.3 CRC32)
   ├───> [ Protocol Formatter ] (Builds header with Access Code + Packet Length) ──> [ Mux Input 1 ]
   └───> [ CRC32 Tagged Stream ] ───────────────────────────────────────────────────> [ Mux Input 2 ]
[ Preamble Source (0x55) ] ────────────────────────────────────────────────────────> [ Mux Input 0 ]
                                                                                           ↓
                                                                           [ Tagged Stream Mux ]
                                                                                           ↓
                                                                          [ Constellation Modulator ]
                                                                                           ↓
                                                                                [ Channel Model ]
RX PIPELINE:
[ Analog AGC ] ──> [ FLL Band-Edge ] ──> [ RRC Matched Filter ] ──> [ Symbol Sync ] ──> [ Costas Loop ]
                                                                                           ↓
                                                                             [ Constellation Decoder ]
                                                                                           ↓
                                                                        [ Correlate Access Code TS ]
                                                                                           ↓
                                                                              [ Repack Bits (1 -> 8) ]
                                                                                           ↓
                                                                               [ CRC32 Checker ]
                                                                                           ↓
                                                                               [ Vector / PDU Sink ]
```

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: All received packets pass 32-bit CRC validation with 100% payload integrity.
