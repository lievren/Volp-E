#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path

from PIL import Image


DEFAULT_SOURCE_ROOT = (
    r"C:\Users\renau\OneDrive\Documents\Projets 3D\PROJET Volp-E\Visage\V1.11"
    r"\Nouveau Visage -fixe-\Visage fixe v2"
)

ASSETS = {
    "brows_neutral": ("Visage Neutre", "Sourcils Neutre.png"),
    "eyes_neutral": ("Visage Neutre", "Regard Neutre.png"),
    "mouth_neutral": ("Visage Neutre", "Bouche Neutre.png"),
    "eyes_blink": ("Clignement", "Clignement.png"),
    "brows_curious": ("Humeur Sourcils", "Sourcils Curieux.png"),
    "brows_sleepy": ("Humeur Sourcils", "Sourclis Endormi.png"),
    "brows_sad": ("Humeur Sourcils", "Sourcils Triste.png"),
    "brows_happy": ("Humeur Sourcils", "Sourcils Content.png"),
    "mouth_curious": ("Humeurs Bouche", "Bouche Curieux.png"),
    "mouth_sleepy": ("Humeurs Bouche", "Bouche Endormi.png"),
    "mouth_sad": ("Humeurs Bouche", "Bouche Triste.png"),
    "mouth_happy": ("Humeurs Bouche", "Bouche Content.png"),
    "mouth_open1": ("Bouche Ouvert 1", "Bouche ouvert 1.png"),
    "mouth_open2": ("Bouche Ouvert 2", "Bouche Ouvert 2.png"),
    "mouth_open3": ("Bouche Ouvert 3", "Bouche Ouvert 3.png"),
    "eyes_right1": ("Regards", "Regard Droite 1.png"),
    "eyes_right2": ("Regards", "Regard Droite 2.png"),
    "eyes_right3": ("Regards", "Regard Droite 3.png"),
    "eyes_right4": ("Regards", "Regard Droite 4.png"),
    "eyes_left1": ("Regards", "Regard Gauche 1.png"),
    "eyes_left2": ("Regards", "Regard Gauche 2.png"),
    "eyes_left3": ("Regards", "Regard Gauche 3.png"),
    "eyes_left4": ("Regards", "Regard Gauche 4.png"),
    "eyes_up": ("Regards", "Regard Haut.png"),
    "eyes_down": ("Regards", "Regard Bas.png"),
    "eyes_up_right": ("Regards", "Regard Haut Droite.png"),
    "eyes_up_left": ("Regards", "Regard Haut Gauche.png"),
    "eyes_down_right": ("Regards", "Regard Bas Droite.png"),
    "eyes_down_left": ("Regards", "Regard Bas Gauche.png"),
}


def make_transparent_white(image):
    rgba = image.convert("RGBA")
    pixels = bytearray(rgba.tobytes())
    for offset in range(0, len(pixels), 4):
        r, g, b, alpha = pixels[offset:offset + 4]
        if alpha and r >= 245 and g >= 245 and b >= 245:
            pixels[offset + 3] = 0
    return Image.frombytes("RGBA", rgba.size, bytes(pixels))


def main():
    parser = argparse.ArgumentParser(description="Build Volp-E v2 layered face assets.")
    parser.add_argument("--source-root", default=DEFAULT_SOURCE_ROOT)
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parents[1] / "face" / "assets"),
    )
    args = parser.parse_args()

    source_root = Path(args.source_root)
    output_root = Path(args.output_root)
    png_root = output_root / "face-v2-png"
    layer_root = output_root / "face-v2-layers"
    png_root.mkdir(parents=True, exist_ok=True)
    layer_root.mkdir(parents=True, exist_ok=True)

    manifest = {"version": 1, "layers": {}}
    missing = []
    for key, parts in ASSETS.items():
        src = source_root.joinpath(*parts)
        if not src.exists():
            missing.append(str(src))
            continue

        png_name = f"{key}.png"
        raw_name = f"{key}.rgba"
        dst_png = png_root / png_name
        dst_raw = layer_root / raw_name
        shutil.copy2(src, dst_png)

        image = make_transparent_white(Image.open(src))
        dst_raw.write_bytes(image.tobytes())
        manifest["layers"][key] = {
            "file": raw_name,
            "png": f"../face-v2-png/{png_name}",
            "width": image.width,
            "height": image.height,
            "source": str(src),
        }

    (layer_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if missing:
        print("[Volp-E assets] Missing files:")
        for item in missing:
            print(f"  - {item}")
        raise SystemExit(1)
    print(f"[Volp-E assets] Built {len(manifest['layers'])} face v2 layers in {layer_root}")


if __name__ == "__main__":
    main()
