# AI Service

Python AI service for stream reading, person detection, abnormal behavior rule detection, and backend event reporting.

## Requirements

- Python 3.14 verified locally
- YOLOv8n is used for person detection when `models/yolov8n.pt` is available
- OpenCV HOG is kept as a fallback detector

## Quick Start

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## Endpoints

- Health check: `GET http://127.0.0.1:9000/health`
- Image person detection: `POST http://127.0.0.1:9000/api/person-detection/image`
  - Form field: `image`
  - Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`
- Video person detection: `POST http://127.0.0.1:9000/api/person-detection/video`
  - Form field: `video`
  - Optional form fields: `frameInterval`, `maxFrames`
  - Supported formats: `.mp4`, `.avi`, `.mov`, `.mkv`

## Response Example

```json
{
  "code": 200,
  "message": "person detection completed",
  "data": {
    "personCount": 1,
    "detections": [
      {
        "type": "PERSON_DETECTION",
        "trackId": "person-1",
        "bbox": {
          "x1": 100,
          "y1": 80,
          "x2": 260,
          "y2": 420
        },
        "centerPoint": {
          "x": 180,
          "y": 250
        },
        "footPoint": {
          "x": 180,
          "y": 420
        },
        "confidence": 0.82
      }
    ],
    "annotatedImageUrl": "/outputs/example_person_detected.jpg"
  }
}
```

## Notes

- This `requirements.txt` belongs only to the AI service directory.
- Running `pip install -r requirements.txt` from the repository root will fail because the root directory does not contain that file.
- The current person detector prefers YOLOv8n from `models/yolov8n.pt` and falls back to OpenCV HOG if YOLO or the model file is unavailable.
