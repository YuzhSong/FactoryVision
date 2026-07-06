class PersonDetector:
    def load_model(self):
        raise NotImplementedError("YOLO model loading will be implemented in a later stage.")

    def detect(self, frame):
        raise NotImplementedError("Person detection will be implemented in a later stage.")
