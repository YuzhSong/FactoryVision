# Video Stream

## Purpose

Defines raw stream ingest, AI processed output, stream lifecycle, and low-latency frontend playback.

## Requirements

### Requirement: Process camera stream

AIService SHALL transform a configured raw camera stream into an annotated processed stream.

#### Scenario: Start detection stream

- **GIVEN** a configured camera and reachable raw RTMP stream
- **WHEN** Frontend starts processing through Backend
- **THEN** AIService SHALL pull the raw stream, annotate the latest frames, and push processed RTMP to SRS
- **AND** status SHALL expose running state, options, timing, drops, reconnects, and last error

### Requirement: Stop stale output after input loss

AIService SHALL stop indefinite stale-frame processing when its input cannot recover.

#### Scenario: Source cannot reconnect

- **GIVEN** the input stream closes
- **WHEN** retries are exhausted
- **THEN** AIService SHALL stop the stream task and clear the latest frame
- **AND** SHALL NOT continue processing or outputting an old frame indefinitely

### Requirement: Low-latency browser playback

Frontend SHALL prefer low-latency playback and SHALL release obsolete player resources.

#### Scenario: Play processed stream

- **GIVEN** SRS is publishing the processed stream
- **WHEN** the monitor opens
- **THEN** Frontend SHALL prefer WebRTC
- **AND** MAY fall back to HTTP-FLV
- **AND** SHALL destroy old playback resources on camera switch or page close
