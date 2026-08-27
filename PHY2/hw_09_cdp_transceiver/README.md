# PHY2 - Stage 09: CDP Modular BPSK Transceiver

## Objective
Establish the complete modular BPSK Transceiver matching the architectural flowgraph pattern of the CDP hardware transceiver (`hardware versions/Phy layer/CDP transeciever.grc`), equipped with Differential Encoding / Decoding to permanently resolve $180^\circ$ carrier ambiguity.

## Flowgraph Architecture
```
TX SECTION:
[ Vector Source ] ──> [ Stream to Tagged Stream ] ──> [ CRC32 Generator ] ──┬──> [ Tagged Stream Mux (Input 2) ]
                                                                             ├──> [ Protocol Formatter ] ──> [ Tagged Stream Mux (Input 1) ]
[ Preamble Source ] ──> [ Stream to Tagged Stream ] ─────────────────────────┴──> [ Tagged Stream Mux (Input 0) ]
                                                                                           ↓
                                                                     [ Constellation Modulator (Diff=True) ]
                                                                                           ↓
                                                                            [ Channel / RF Loopback ]
RX SECTION:
[ Analog AGC ] ──> [ FLL Band-Edge ] ──> [ RRC Filter ] ──> [ Symbol Sync ] ──> [ Costas Loop ]
                                                                                           ↓
                                                                             [ Constellation Decoder ]
                                                                                           ↓
                                                                             [ Differential Decoder ]
                                                                                           ↓
                                                                           [ Correlate Access Code TS ]
                                                                                           ↓
                                                                              [ Repack Bits (1 -> 8) ]
                                                                                           ↓
                                                                               [ CRC32 Checker ]
                                                                                           ↓
                                                                               [ Vector Sink / PDU ]
```

## Verification
Run the automated test runner:
```bash
python3 run_test.py
```
Expected Result: 100% data integrity verified across clean channel, clock drift, and positive/negative carrier offsets.
