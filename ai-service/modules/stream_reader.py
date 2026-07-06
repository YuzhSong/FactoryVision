class StreamReader:
    def open_stream(self, stream_url: str):
        """Reserve stream connection logic for OpenCV or future media adapters."""
        raise NotImplementedError("Stream reading will be implemented in a later stage.")

    def read_frame(self):
        raise NotImplementedError("Frame reading will be implemented in a later stage.")

    def close_stream(self):
        raise NotImplementedError("Stream closing will be implemented in a later stage.")
