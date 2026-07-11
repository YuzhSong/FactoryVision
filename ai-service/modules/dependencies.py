from importlib import import_module
import shutil

from ai_config import Config


DEPENDENCIES = {
    "opencv": "cv2",
    "numpy": "numpy",
    "torch": "torch",
    "ultralytics": "ultralytics",
    "insightface": "insightface",
    "onnxruntime": "onnxruntime",
    "Pillow": "PIL",
}


def check_dependencies():
    Config.ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for name, module_name in DEPENDENCIES.items():
        try:
            module = import_module(module_name)
            result = {
                "installed": True,
                "version": getattr(module, "__version__", "unknown"),
                "error": None,
            }
            if name == "torch":
                result["cudaAvailable"] = bool(module.cuda.is_available())
                result["cudaVersion"] = module.version.cuda
                result["deviceCount"] = module.cuda.device_count()
                result["deviceName"] = (
                    module.cuda.get_device_name(0)
                    if module.cuda.is_available()
                    else None
                )
            results[name] = result
        except Exception as exc:
            results[name] = {
                "installed": False,
                "version": None,
                "error": str(exc),
            }
    results["ffmpeg"] = {
        "installed": shutil.which(Config.STREAM_FFMPEG_PATH) is not None,
        "path": shutil.which(Config.STREAM_FFMPEG_PATH),
        "error": None if shutil.which(Config.STREAM_FFMPEG_PATH) else "ffmpeg executable not found",
    }
    return results
