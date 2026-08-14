#!/usr/bin/env python3
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRAIN_URL = "http://127.0.0.1:8765/api/vision"
MODELS_DIR = ROOT / "models"
DEFAULT_MODEL = MODELS_DIR / "mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite"
FALLBACK_FACE_MODEL = MODELS_DIR / "mobilenet_ssd_v2_face_quant_postprocess_edgetpu.tflite"
FRAME_SIZE = (320, 240)
DETECT_EVERY_SECONDS = 0.16
MIN_SCORE = 0.30
PERSON_CLASS_ID = 0
ROTATE_180 = True
LATEST_FRAME = Path("/tmp/volpe-latest-frame.jpg")
LATEST_FRAME_EVERY_SECONDS = 2.0


def normalize_frame(frame):
    import cv2

    frame = cv2.resize(frame, FRAME_SIZE, interpolation=cv2.INTER_AREA)
    if ROTATE_180:
        frame = cv2.rotate(frame, cv2.ROTATE_180)
    return frame


def post_vision(face, x=0.0, y=0.0, size=0.0):
    query = urllib.parse.urlencode({
        "face": "1" if face else "0",
        "x": f"{x:.3f}",
        "y": f"{y:.3f}",
        "size": f"{size:.3f}",
    })
    try:
        urllib.request.urlopen(f"{BRAIN_URL}?{query}", timeout=0.1).close()
    except Exception:
        pass


def maybe_write_latest_frame(frame, last_write):
    now = time.monotonic()
    if now - last_write < LATEST_FRAME_EVERY_SECONDS:
        return last_write
    try:
        import cv2

        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(LATEST_FRAME), bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        return now
    except Exception:
        return last_write


def open_camera():
    import cv2

    capture = cv2.VideoCapture(0, cv2.CAP_V4L2)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_SIZE[0])
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_SIZE[1])
    capture.set(cv2.CAP_PROP_FPS, 8)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if capture.isOpened():
        def read_v4l2_frame():
            ok, frame = capture.read()
            if not ok:
                return None
            frame = normalize_frame(frame)
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        print("[Volp-E vision] V4L2 camera ready: /dev/video0", flush=True)
        return read_v4l2_frame

    try:
        from picamera2 import Picamera2

        camera = Picamera2()
        config = camera.create_preview_configuration(
            main={"size": FRAME_SIZE, "format": "RGB888"},
            buffer_count=2,
        )
        camera.configure(config)
        camera.start()
        time.sleep(1.0)

        def read_picamera_frame():
            return camera.capture_array()

        print("[Volp-E vision] Picamera2 camera ready", flush=True)
        return read_picamera_frame
    except Exception as exc:
        raise RuntimeError(f"No camera available through V4L2 or Picamera2: {exc}")


def make_coral_detector():
    if os.environ.get("VOLPE_DISABLE_CORAL") == "1":
        raise RuntimeError("Coral disabled by VOLPE_DISABLE_CORAL=1")
    model_override = os.environ.get("VOLPE_TFLITE_MODEL")
    if model_override:
        model_path = Path(model_override)
    else:
        model_path = DEFAULT_MODEL if DEFAULT_MODEL.exists() else FALLBACK_FACE_MODEL
    if not model_path.exists():
        raise RuntimeError(f"Missing EdgeTPU model: {model_path}")
    person_only = model_path.name != FALLBACK_FACE_MODEL.name

    from pycoral.adapters import common
    from pycoral.adapters import detect as coral_detect
    from pycoral.utils.edgetpu import make_interpreter

    interpreter = make_interpreter(str(model_path))
    interpreter.allocate_tensors()
    input_w, input_h = common.input_size(interpreter)
    import cv2

    print(f"[Volp-E vision] PyCoral detector ready: {model_path.name}", flush=True)

    def detect(frame):
        resized = cv2.resize(frame, (input_w, input_h), interpolation=cv2.INTER_LINEAR)
        common.set_input(interpreter, resized)
        interpreter.invoke()

        best = None
        for obj in coral_detect.get_objects(interpreter, MIN_SCORE):
            if person_only and obj.id != PERSON_CLASS_ID:
                continue
            bbox = obj.bbox
            xmin = bbox.xmin / input_w
            ymin = bbox.ymin / input_h
            xmax = bbox.xmax / input_w
            ymax = bbox.ymax / input_h
            area = max(0.0, xmax - xmin) * max(0.0, ymax - ymin)
            weight = obj.score * area
            if best is None or weight > best[0]:
                best = (weight, xmin, ymin, xmax, ymax)

        if best is None:
            return None

        _, xmin, ymin, xmax, ymax = best
        center_x = -(((xmin + xmax) / 2 - 0.5) * 2)
        center_y = ((ymin + ymax) / 2 - 0.5) * 2
        size = max(xmax - xmin, ymax - ymin)
        return center_x, center_y, size

    return detect


def make_haar_detector():
    import cv2

    cascade_dirs = [
        getattr(getattr(cv2, "data", None), "haarcascades", ""),
        "/usr/share/opencv4/haarcascades/",
        "/usr/share/opencv/haarcascades/",
    ]
    cascade_path = ""
    for cascade_dir in cascade_dirs:
        candidate = Path(cascade_dir) / "haarcascade_frontalface_default.xml"
        if candidate.exists():
            cascade_path = str(candidate)
            break
    if not cascade_path:
        raise RuntimeError("Cannot find haarcascade_frontalface_default.xml")

    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        raise RuntimeError(f"Cannot load Haar cascade: {cascade_path}")

    print("[Volp-E vision] CPU Haar detector ready", flush=True)

    def detect(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = detector.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=4,
            minSize=(42, 42),
        )
        if not len(faces):
            return None
        x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
        center_x = -(((x + w / 2) / FRAME_SIZE[0] - 0.5) * 2)
        center_y = ((y + h / 2) / FRAME_SIZE[1] - 0.5) * 2
        size = max(w / FRAME_SIZE[0], h / FRAME_SIZE[1])
        return center_x, center_y, size

    return detect


def main():
    detect = None
    for attempt in range(1, 5):
        try:
            detect = make_coral_detector()
            break
        except Exception as exc:
            print(f"[Volp-E vision] Coral attempt {attempt}/4 failed: {exc}", flush=True)
            time.sleep(1.5)

    if detect is None:
        if os.environ.get("VOLPE_ALLOW_CPU_FALLBACK") == "1":
            print("[Volp-E vision] Falling back to CPU detector", flush=True)
            detect = make_haar_detector()
        else:
            raise RuntimeError("Coral unavailable and CPU fallback is disabled")

    read_frame = open_camera()
    last_seen = 0.0
    last_result = None
    last_frame_write = 0.0

    while True:
        start = time.monotonic()
        frame = read_frame()
        if frame is None:
            post_vision(False)
            time.sleep(0.5)
            continue
        last_frame_write = maybe_write_latest_frame(frame, last_frame_write)

        result = detect(frame)
        if result is not None:
            last_result = result
            last_seen = time.monotonic()

        if last_result is not None and time.monotonic() - last_seen < 1.0:
            post_vision(True, *last_result)
        else:
            post_vision(False)

        elapsed = time.monotonic() - start
        time.sleep(max(0.02, DETECT_EVERY_SECONDS - elapsed))


if __name__ == "__main__":
    if "--check-coral" in sys.argv:
        detect = make_coral_detector()
        print("[Volp-E vision] Coral check ok", flush=True)
    else:
        main()
