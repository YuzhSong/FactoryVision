import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import cv2
from flask import Flask, jsonify, request, send_from_directory

from config import Config
from modules.person_detector import PersonDetector

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
OUTPUT_DIR = BASE_DIR / "data" / "outputs"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

person_detector = PersonDetector(confidence_threshold=0.5).load_model()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/health")
    def health_check():
        return jsonify(
            {
                "service": app.config["SERVICE_NAME"],
                "status": "ok",
                "stage": "person-detection-ready",
            }
        )

    @app.post("/api/person-detection/image")
    def detect_persons_in_image():
        uploaded_file = request.files.get("image")
        if not uploaded_file or not uploaded_file.filename:
            return api_error("image file is required", 400)

        extension = Path(uploaded_file.filename).suffix.lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            return api_error("unsupported image format", 400)

        image_id = uuid4().hex
        input_path = UPLOAD_DIR / f"{image_id}{extension}"
        output_filename = f"{image_id}_person_detected.jpg"
        output_path = OUTPUT_DIR / output_filename
        uploaded_file.save(input_path)

        frame = cv2.imread(str(input_path))
        if frame is None:
            return api_error("failed to read image", 400)

        detections = person_detector.detect(frame)
        annotated_frame = person_detector.draw_detections(frame, detections)
        cv2.imwrite(str(output_path), annotated_frame)

        return api_success(
            data={
                "imageId": image_id,
                "personCount": len(detections),
                "detections": detections,
                "annotatedImageUrl": f"/outputs/{output_filename}",
            },
            message="person detection completed",
        )

    @app.post("/api/person-detection/video")
    def detect_persons_in_video():
        uploaded_file = request.files.get("video")
        if not uploaded_file or not uploaded_file.filename:
            return api_error("video file is required", 400)

        extension = Path(uploaded_file.filename).suffix.lower()
        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            return api_error("unsupported video format", 400)

        frame_interval = parse_positive_int(request.form.get("frameInterval"), default=10)
        max_frames = parse_positive_int(request.form.get("maxFrames"), default=120)
        video_id = uuid4().hex
        input_path = UPLOAD_DIR / f"{video_id}{extension}"
        output_filename = f"{video_id}_person_detected.mp4"
        output_path = OUTPUT_DIR / output_filename
        uploaded_file.save(input_path)

        result = process_video(input_path, output_path, frame_interval, max_frames)
        if result.get("error"):
            return api_error(result["error"], 400)

        return api_success(
            data={
                "videoId": video_id,
                "frameInterval": frame_interval,
                "processedFrames": result["processedFrames"],
                "personFrameCount": result["personFrameCount"],
                "maxPersonCount": result["maxPersonCount"],
                "frames": result["frames"],
                "annotatedVideoUrl": f"/outputs/{output_filename}",
            },
            message="video person detection completed",
        )

    @app.get("/outputs/<path:filename>")
    def get_output_file(filename):
        return send_from_directory(OUTPUT_DIR, filename)

    return app


def process_video(input_path, output_path, frame_interval, max_frames):
    capture = cv2.VideoCapture(str(input_path))
    if not capture.isOpened():
        return {"error": "failed to open video"}

    fps = capture.get(cv2.CAP_PROP_FPS) or 25
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        capture.release()
        return {"error": "invalid video size"}

    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    frames = []
    frame_index = 0
    processed_frames = 0
    person_frame_count = 0
    max_person_count = 0
    latest_detections = []

    while processed_frames < max_frames:
        success, frame = capture.read()
        if not success:
            break

        should_detect = frame_index % frame_interval == 0
        if should_detect:
            latest_detections = person_detector.detect(frame)
            person_count = len(latest_detections)
            if person_count > 0:
                person_frame_count += 1
            max_person_count = max(max_person_count, person_count)
            frames.append(
                {
                    "frameIndex": frame_index,
                    "personCount": person_count,
                    "detections": latest_detections,
                }
            )
            processed_frames += 1

        annotated_frame = person_detector.draw_detections(frame, latest_detections)
        writer.write(annotated_frame)
        frame_index += 1

    capture.release()
    writer.release()

    return {
        "processedFrames": processed_frames,
        "personFrameCount": person_frame_count,
        "maxPersonCount": max_person_count,
        "frames": frames,
    }


def parse_positive_int(value, default):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def api_success(data=None, message="success"):
    return jsonify(
        {
            "code": 200,
            "message": message,
            "data": data or {},
            "timestamp": now_iso(),
        }
    )


def api_error(message, status_code):
    response = jsonify(
        {
            "code": status_code,
            "message": message,
            "data": {},
            "timestamp": now_iso(),
        }
    )
    response.status_code = status_code
    return response


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


app = create_app()


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
