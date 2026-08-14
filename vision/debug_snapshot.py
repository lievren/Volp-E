#!/usr/bin/env python3
import sys
from pathlib import Path

import cv2
from pycoral.adapters import common
from pycoral.adapters import detect as coral_detect
from pycoral.utils.edgetpu import make_interpreter


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite"
OUT = Path("/tmp/volpe-vision-debug.jpg")
FRAME_SIZE = (320, 240)
MIN_SCORE = 0.20
ROTATE_180 = True


def main():
    if not MODEL.exists():
        raise SystemExit(f"Missing model: {MODEL}")

    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_SIZE[1])
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        raise SystemExit("Cannot open /dev/video0")

    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("Cannot read frame from /dev/video0")

    frame = cv2.resize(frame, FRAME_SIZE, interpolation=cv2.INTER_AREA)
    if ROTATE_180:
        frame = cv2.rotate(frame, cv2.ROTATE_180)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    interpreter = make_interpreter(str(MODEL))
    interpreter.allocate_tensors()
    input_w, input_h = common.input_size(interpreter)
    resized = cv2.resize(rgb, (input_w, input_h), interpolation=cv2.INTER_LINEAR)
    common.set_input(interpreter, resized)
    interpreter.invoke()

    objects = coral_detect.get_objects(interpreter, MIN_SCORE)
    print(f"objects: {len(objects)}")
    for obj in objects:
        bbox = obj.bbox
        x1 = int(bbox.xmin * FRAME_SIZE[0] / input_w)
        y1 = int(bbox.ymin * FRAME_SIZE[1] / input_h)
        x2 = int(bbox.xmax * FRAME_SIZE[0] / input_w)
        y2 = int(bbox.ymax * FRAME_SIZE[1] / input_h)
        print(f"id={obj.id} score={obj.score:.2f} box=({x1},{y1})-({x2},{y2})")
        color = (0, 255, 0) if obj.id == 0 else (0, 180, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            f"id {obj.id} {obj.score:.2f}",
            (max(0, x1), max(16, y1 - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    cv2.imwrite(str(OUT), frame)
    print(f"saved: {OUT}")


if __name__ == "__main__":
    sys.exit(main())
