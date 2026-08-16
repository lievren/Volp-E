#!/usr/bin/env python3
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SVG = Path("assets/face.svg")
OUT_HTML = ROOT / "face" / "index.html"


def clean_svg(svg: str) -> str:
    svg = re.sub(r"^\ufeff?\s*<\?xml[^>]*>\s*", "", svg, flags=re.I)
    svg = re.sub(r"<!-- Created with Inkscape[^>]*-->\s*", "", svg, flags=re.I)
    svg = re.sub(
        r'<g\s+inkscape:label="croquis"[\s\S]*?</g><g\s+inkscape:groupmode="layer"\s+id="layer4"',
        '<g inkscape:groupmode="layer" id="layer4"',
        svg,
        count=1,
    )
    match = re.search(r"<svg\b[^>]*>", svg, flags=re.I)
    if match:
        original_tag = match.group(0)
        namespaces = re.findall(r'\s(xmlns(?::[\w-]+)?="[^"]*")', original_tag)
        safe_tag = (
            '<svg id="volpe-svg" viewBox="0 0 800 480" '
            'preserveAspectRatio="xMidYMid meet" '
            + " ".join(dict.fromkeys(namespaces))
            + ">"
        )
        svg = svg[: match.start()] + safe_tag + svg[match.end() :]
    return svg


def html(svg: str) -> str:
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
  <meta name="theme-color" content="#050301">
  <title>Volp-E Face</title>
  <style>
    :root {{
      color-scheme: dark;
      --face-x: 0px;
      --face-y: 0px;
      --face-scale: 1;
      --look-x: 0px;
      --look-y: 0px;
    }}

    html,
    body {{
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background: #050301;
      cursor: none;
      touch-action: none;
      user-select: none;
      -webkit-user-select: none;
      -webkit-tap-highlight-color: transparent;
    }}

    body {{
      display: grid;
      place-items: center;
    }}

    .stage {{
      position: fixed;
      inset: 0;
      display: grid;
      place-items: center;
      background: #050301;
    }}

    .stage::after {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at var(--tap-x, 50%) var(--tap-y, 50%), rgba(255, 210, 120, .16), transparent 18rem),
        linear-gradient(rgba(255,255,255,.03) 50%, transparent 50%);
      background-size: auto, 100% 3px;
      opacity: var(--flash, 0);
      mix-blend-mode: screen;
      transition: opacity 240ms ease;
    }}

    #volpe-svg,
    main.stage > svg {{
      display: none !important;
    }}

    #standby-canvas {{
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100dvh;
      opacity: 0;
      z-index: 3;
      pointer-events: none;
      transition: opacity 900ms ease;
    }}

    .fallback-face {{
      position: fixed;
      inset: 0;
      display: grid;
      place-items: center;
      background: #050301;
      z-index: 2;
      transform: translate3d(var(--face-x), var(--face-y), 0) scale(var(--face-scale));
      transition: transform 360ms ease, filter 360ms ease, opacity 360ms ease;
    }}

    .fallback-eyes {{
      width: min(76vw, 640px);
      display: grid;
      grid-template-columns: .72fr 1.42fr;
      align-items: center;
      gap: min(7vw, 54px);
    }}

    .fallback-eye {{
      position: relative;
      aspect-ratio: 1.65;
      border: 2px solid rgba(91, 163, 255, .78);
      border-radius: 50%;
      background: radial-gradient(circle at 54% 52%, #111 0 9%, #f18139 10% 28%, #dffbff 30% 100%);
      box-shadow: 0 0 16px rgba(91, 163, 255, .35), inset 0 0 18px rgba(21, 72, 140, .38);
      overflow: hidden;
      animation: fallback-breathe 2.6s ease-in-out infinite;
    }}

    .fallback-eye::after {{
      content: "";
      position: absolute;
      left: 50%;
      top: 50%;
      width: 12%;
      aspect-ratio: 1;
      border-radius: 50%;
      background: #050301;
      transform: translate(calc(-50% + var(--look-x) * 1.4), calc(-50% + var(--look-y) * 1.1));
      box-shadow: 0 0 6px rgba(0, 0, 0, .7);
    }}

    .fallback-eye:first-child {{
      transform: scale(.72);
      background: radial-gradient(circle at 54% 54%, #111 0 7%, #e8defd 8% 18%, #07111e 20% 100%);
    }}

    .fallback-eye:last-child {{
      border-radius: 54% 76% 58% 62%;
    }}

    [data-mode="sleepy"] .fallback-face {{
      filter: saturate(.86) brightness(.72);
      opacity: .84;
    }}

    [data-mode="alert"] .fallback-face {{
      filter: saturate(1.28) brightness(1.16) drop-shadow(0 0 10px rgba(190, 30, 20, .24));
    }}

    @keyframes fallback-breathe {{
      0%, 100% {{ filter: brightness(.9); }}
      50% {{ filter: brightness(1.16); }}
    }}

    [data-mode="standby"] .fallback-face {{
      opacity: 0;
    }}

    [data-mode="standby"] #standby-canvas {{
      opacity: 1;
    }}

    [data-mode="sleepy"] #volpe-svg,
    [data-mode="sleepy"] main.stage > svg {{
      filter: saturate(1.02) contrast(1.02) brightness(.92);
    }}

    [data-mode="alert"] #volpe-svg,
    [data-mode="alert"] main.stage > svg {{
      filter: saturate(1.35) contrast(1.18) brightness(1.18) drop-shadow(0 0 10px rgba(190, 30, 20, .24));
    }}

    .thought-text {{
      position: fixed;
      left: 50%;
      bottom: clamp(6px, 3.8vh, 24px);
      width: min(88vw, 680px);
      min-height: 1.35em;
      transform: translateX(-50%) translateY(6px);
      color: rgba(230, 248, 255, .92);
      font: 500 clamp(15px, 3.2vw, 24px)/1.2 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      text-align: center;
      letter-spacing: .02em;
      text-shadow: 0 0 10px rgba(92, 190, 255, .42), 0 1px 2px rgba(0, 0, 0, .92);
      opacity: 0;
      pointer-events: none;
      transition: opacity 420ms ease, transform 420ms ease;
      z-index: 5;
    }}

    .thought-text.is-visible {{
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }}

    [data-mode="standby"] .thought-text {{
      opacity: 0;
    }}
  </style>
</head>
<body>
  <main class="stage" data-mode="normal" aria-label="Visage anime de Volp-E">
    <div class="fallback-face" aria-hidden="true">
      <div class="fallback-eyes">
        <div class="fallback-eye"></div>
        <div class="fallback-eye"></div>
      </div>
    </div>
    {svg}
    <canvas id="standby-canvas" aria-hidden="true"></canvas>
    <div id="thought-text" class="thought-text"></div>
  </main>

  <script>
    const BRAIN_URL = "http://127.0.0.1:8765";
    const stage = document.querySelector(".stage");
    const svg = document.querySelector("main.stage > svg");
    if (svg) {{
      svg.id = "volpe-svg";
      svg.setAttribute("viewBox", "0 0 800 480");
      svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
      svg.removeAttribute("width");
      svg.removeAttribute("height");
    }}

    const modes = ["normal", "sleepy", "alert", "standby"];
    const standbyCanvas = document.querySelector("#standby-canvas");
    const standbyCtx = standbyCanvas.getContext("2d", {{ alpha: true }});
    const thoughtText = document.querySelector("#thought-text");
    const rightEye = document.querySelector("#layer4");
    const leftEye = document.querySelector("#layer9");
    const rightIris = document.querySelector("#path17");
    const rightPupil = document.querySelector("#path20");
    const leftIris = document.querySelector("#ellipse20");
    const leftPupil = document.querySelector("#path18");
    const mouth = document.querySelector("#layer6");
    const cigarette = document.querySelector("#layer7");
    const smoke = document.querySelector("#layer8");

    let modeIndex = 0;
    let mode = "normal";
    let lookX = 0;
    let lookY = 0;
    let targetX = 0;
    let targetY = 0;
    let lastPick = 0;
    let remoteMode = null;
    let visionUntil = 0;
    let leftEyeWrap = null;
    let rightEyeWrap = null;
    let leftEyeBase = "";
    let rightEyeBase = "";
    let lastThoughtAt = 0;
    const baseTransforms = new Map();
    const standbyParticles = [];
    let standbyW = 0;
    let standbyH = 0;
    let standbyDpr = 1;

    function hideUnusedLayers() {{
      if (mouth) mouth.style.display = "none";
      if (cigarette) cigarette.style.display = "none";
      if (smoke) smoke.style.display = "none";
    }}

    function svgPointFromClient(x, y) {{
      const point = svg.createSVGPoint();
      point.x = x;
      point.y = y;
      return point.matrixTransform(svg.getScreenCTM().inverse());
    }}

    function renderedCenter(node) {{
      const box = node.getBBox();
      return {{
        x: box.x + box.width / 2,
        y: box.y + box.height / 2,
      }};
    }}

    function wrapLayer(node, id) {{
      const wrap = document.createElementNS("http://www.w3.org/2000/svg", "g");
      wrap.setAttribute("id", id);
      node.parentNode.insertBefore(wrap, node);
      wrap.appendChild(node);
      return wrap;
    }}

    function rememberBaseTransform(node) {{
      if (node && !baseTransforms.has(node)) {{
        baseTransforms.set(node, node.getAttribute("transform") || "");
      }}
    }}

    function setSvgTransform(node, transform) {{
      if (!node) return;
      const base = baseTransforms.get(node) || "";
      node.setAttribute("transform", `${{base}} ${{transform}}`.trim());
    }}

    function eyePlacement(targetX, targetY, current, scale) {{
      return `translate(${{targetX}} ${{targetY}}) scale(${{scale}}) translate(${{-current.x}} ${{-current.y}})`;
    }}

    function prepareAnimationTargets() {{
      hideUnusedLayers();
      stage.classList.add("is-ready");
      return true;
    }}

    function prepareSvgAnimationTargets() {{
      [rightEye, leftEye, rightIris, rightPupil, leftIris, leftPupil].filter(Boolean).forEach((node) => {{
        rememberBaseTransform(node);
        node.style.transformBox = "fill-box";
        node.style.transformOrigin = "center";
        node.style.willChange = "transform, opacity, filter";
      }});

      hideUnusedLayers();
      if (!svg || !leftEye || !rightEye) return false;

      if (!leftEyeWrap) leftEyeWrap = wrapLayer(leftEye, "left-eye-layout");
      if (!rightEyeWrap) rightEyeWrap = wrapLayer(rightEye, "right-eye-layout");

      const leftCurrent = renderedCenter(leftEye);
      const rightCurrent = renderedCenter(rightEye);
      if (
        !Number.isFinite(leftCurrent.x) || !Number.isFinite(leftCurrent.y) ||
        !Number.isFinite(rightCurrent.x) || !Number.isFinite(rightCurrent.y)
      ) return false;
      leftEyeBase = eyePlacement(210, 256, leftCurrent, 3.6);
      rightEyeBase = eyePlacement(530, 232, rightCurrent, 3.13);
      leftEyeWrap.setAttribute("transform", leftEyeBase);
      rightEyeWrap.setAttribute("transform", rightEyeBase);
      return true;
    }}

    function setMode(nextMode) {{
      if (!modes.includes(nextMode)) return;
      mode = nextMode;
      modeIndex = modes.indexOf(nextMode);
      stage.dataset.mode = mode;
      hideUnusedLayers();
      document.documentElement.style.setProperty("--flash", ".8");
      setTimeout(() => document.documentElement.style.setProperty("--flash", "0"), 140);
    }}

    function resizeStandbyCanvas() {{
      standbyDpr = Math.min(devicePixelRatio || 1, 1.5);
      standbyW = innerWidth;
      standbyH = innerHeight;
      standbyCanvas.width = Math.max(1, Math.floor(standbyW * standbyDpr));
      standbyCanvas.height = Math.max(1, Math.floor(standbyH * standbyDpr));
      standbyCanvas.style.width = `${{standbyW}}px`;
      standbyCanvas.style.height = `${{standbyH}}px`;
      standbyCtx.setTransform(standbyDpr, 0, 0, standbyDpr, 0, 0);
    }}

    function seedStandbyParticles() {{
      standbyParticles.length = 0;
      const count = 360;
      for (let i = 0; i < count; i++) {{
        const band = i / count;
        standbyParticles.push({{
          band,
          phase: Math.random() * Math.PI * 2,
          drift: Math.random() * Math.PI * 2,
          speed: .55 + Math.random() * .9,
          size: .55 + Math.random() * 1.35,
          warmth: Math.random(),
        }});
      }}
    }}

    function drawStandby(now) {{
      if (!standbyCtx || !standbyW || !standbyH) return;
      const t = now / 1000;
      standbyCtx.clearRect(0, 0, standbyW, standbyH);
      standbyCtx.fillStyle = "#050301";
      standbyCtx.fillRect(0, 0, standbyW, standbyH);

      const cx = standbyW * .52;
      const cy = standbyH * .49;
      const scale = Math.min(standbyW, standbyH);
      const glow = standbyCtx.createRadialGradient(cx, cy, 0, cx, cy, scale * .63);
      glow.addColorStop(0, "rgba(255, 224, 150, .13)");
      glow.addColorStop(.34, "rgba(78, 106, 170, .09)");
      glow.addColorStop(1, "rgba(5, 3, 1, 0)");
      standbyCtx.fillStyle = glow;
      standbyCtx.fillRect(0, 0, standbyW, standbyH);

      standbyCtx.globalCompositeOperation = "lighter";
      for (const p of standbyParticles) {{
        const angle = p.band * Math.PI * 2 + Math.sin(t * .12 + p.phase) * .55;
        const swirl = t * p.speed + p.phase;
        const radius = scale * (.12 + p.band * .285) * (1 + Math.sin(swirl * .48) * .18);
        const squash = .47 + Math.sin(t * .18) * .05;
        const curl = Math.sin(angle * 3.0 + t * .75 + p.drift) * scale * .0375;
        const x = cx + Math.cos(angle + t * .16) * radius + curl;
        const y = cy + Math.sin(angle - t * .11) * radius * squash + Math.cos(swirl) * scale * .027;
        const core = Math.max(0, 1 - Math.abs(p.band - .43) * 2.3);
        const alpha = .13 + core * .42 + Math.sin(swirl * 1.7) * .08;
        const hue = p.warmth > .62 ? "255, 221, 134" : p.warmth > .32 ? "105, 132, 205" : "230, 236, 255";
        standbyCtx.fillStyle = `rgba(${{hue}}, ${{Math.max(.04, alpha)}})`;
        standbyCtx.beginPath();
        standbyCtx.arc(x, y, p.size, 0, Math.PI * 2);
        standbyCtx.fill();
      }}

      standbyCtx.globalCompositeOperation = "source-over";
      standbyCtx.strokeStyle = "rgba(255, 225, 150, .42)";
      standbyCtx.lineWidth = 1.2;
      standbyCtx.beginPath();
      for (let i = 0; i < 90; i++) {{
        const a = i / 89 * Math.PI * 1.25 + t * .19;
        const r = scale * (.255 + Math.sin(i * .15 + t) * .018);
        const x = cx + Math.cos(a) * r;
        const y = cy + Math.sin(a) * r * .38;
        if (i === 0) standbyCtx.moveTo(x, y);
        else standbyCtx.lineTo(x, y);
      }}
      standbyCtx.stroke();
    }}

    function cycleMode(event) {{
      const point = event.changedTouches ? event.changedTouches[0] : event;
      document.documentElement.style.setProperty("--tap-x", `${{point.clientX || innerWidth / 2}}px`);
      document.documentElement.style.setProperty("--tap-y", `${{point.clientY || innerHeight / 2}}px`);
      setMode(modes[(modeIndex + 1) % modes.length]);
      remoteMode = null;
    }}

    function cleanThought(raw) {{
      const text = String(raw || "").replace(/\\s+/g, " ").trim();
      if (!text) return "";
      return text.length > 86 ? `${{text.slice(0, 83)}}...` : text;
    }}

    function updateThought(thought) {{
      if (!thoughtText || !thought) return;
      const seenAt = Number(thought.last_at) || 0;
      const age = seenAt ? Date.now() / 1000 - seenAt : Infinity;
      const text = cleanThought(thought.speech || thought.description);
      if (!text || age > 45 || mode === "standby") {{
        thoughtText.classList.remove("is-visible");
        return;
      }}
      if (seenAt !== lastThoughtAt || thoughtText.textContent !== text) {{
        lastThoughtAt = seenAt;
        thoughtText.textContent = text;
      }}
      thoughtText.classList.add("is-visible");
    }}

    function pickLook(now) {{
      if (now < visionUntil) return;
      const interval = mode === "alert" ? 260 : mode === "sleepy" ? 2000 : 1000;
      if (now - lastPick < interval) return;
      lastPick = now;
      const rangeX = mode === "alert" ? 7.2 : mode === "sleepy" ? 2.2 : 4.8;
      const rangeY = mode === "alert" ? 4.3 : mode === "sleepy" ? 1.1 : 3.1;
      targetX = (Math.random() * 2 - 1) * rangeX;
      targetY = (Math.random() * 2 - 1) * rangeY;
    }}

    function animate(now) {{
      drawStandby(now);
      pickLook(now);
      const stiffness = mode === "alert" ? .28 : mode === "sleepy" ? .05 : .12;
      lookX += (targetX - lookX) * stiffness;
      lookY += (targetY - lookY) * stiffness;

      const t = now / 1000;
      const blink = mode !== "alert" && Math.sin(t * (mode === "sleepy" ? 1.35 : .62)) > .985;
      const drowsy = mode === "sleepy" ? Math.max(0, Math.sin(t * 1.1)) : 0;
      const leftOpen = blink ? .16 : mode === "sleepy" ? Math.max(.24, 1 - drowsy * .7) : 1;
      const rightOpen = blink ? .18 : mode === "sleepy" ? Math.max(.3, 1 - drowsy * .56) : 1;

      setSvgTransform(leftIris, `translate(${{lookX * .45}} ${{lookY * .34}}) scale(1 ${{leftOpen}})`);
      setSvgTransform(leftPupil, `translate(${{lookX * .78}} ${{lookY * .58}}) scale(${{mode === "alert" ? 1.55 : 1}} ${{leftOpen}})`);
      setSvgTransform(rightIris, `translate(${{lookX * 1.25}} ${{lookY * 1.1}}) scale(1 ${{rightOpen}})`);
      setSvgTransform(rightPupil, `translate(${{lookX * 1.75}} ${{lookY * 1.55}}) scale(${{mode === "alert" ? 1.28 : mode === "sleepy" ? .72 : 1}} ${{rightOpen}})`);

      if (leftEyeWrap) leftEyeWrap.setAttribute("transform", `translate(${{mode === "alert" ? Math.sin(t * 34) * .45 : 0}} 0) ${{leftEyeBase}}`);
      if (rightEyeWrap) rightEyeWrap.setAttribute("transform", `translate(${{mode === "alert" ? Math.sin(t * 37) * .32 : 0}} ${{mode === "alert" ? Math.cos(t * 31) * .24 : 0}}) ${{rightEyeBase}}`);

      const faceX = mode === "alert" ? Math.sin(t * 43) * 1.8 : mode === "sleepy" ? 0 : Math.sin(t * .9) * .35;
      const faceY = mode === "alert" ? Math.cos(t * 39) * 1.2 : mode === "sleepy" ? Math.sin(t * .7) * 1.5 : Math.cos(t * .75) * .22;
      document.documentElement.style.setProperty("--face-x", `${{faceX}}px`);
      document.documentElement.style.setProperty("--face-y", `${{faceY}}px`);
      document.documentElement.style.setProperty("--face-scale", mode === "alert" ? "1.015" : "1");
      document.documentElement.style.setProperty("--look-x", `${{lookX}}px`);
      document.documentElement.style.setProperty("--look-y", `${{lookY}}px`);

      requestAnimationFrame(animate);
    }}

    async function pollBrain() {{
      try {{
        const response = await fetch(`${{BRAIN_URL}}/api/state`, {{ cache: "no-store" }});
        if (response.ok) {{
          const state = await response.json();
          if (state.mode && state.mode !== remoteMode) {{
            remoteMode = state.mode;
            setMode(state.mode);
          }}
          if (state.vision && state.vision.face) {{
            targetX = Math.max(-1, Math.min(1, Number(state.vision.x) || 0)) * 12;
            targetY = Math.max(-1, Math.min(1, Number(state.vision.y) || 0)) * 7;
            visionUntil = performance.now() + 900;
          }}
          updateThought(state.thought);
        }}
      }} catch {{}}
      setTimeout(pollBrain, 500);
    }}

    addEventListener("pointerup", cycleMode, {{ passive: true }});
    addEventListener("resize", () => {{
      resizeStandbyCanvas();
      seedStandbyParticles();
    }});
    function startFace() {{
      resizeStandbyCanvas();
      seedStandbyParticles();
      if (!prepareAnimationTargets()) {{
        setTimeout(startFace, 250);
        return;
      }}
      setMode("normal");
      stage.classList.add("is-ready");
      requestAnimationFrame(animate);
    }}
    requestAnimationFrame(startFace);
    pollBrain();
  </script>
</body>
</html>
"""


def main() -> None:
    if not SOURCE_SVG.exists():
        raise SystemExit(
            "Missing source SVG. Put it at assets/face.svg or update SOURCE_SVG "
            "for your local workspace."
        )
    source = SOURCE_SVG.read_text(encoding="utf-8")
    OUT_HTML.write_text(html(clean_svg(source)), encoding="utf-8")
    print(f"Wrote {OUT_HTML}")


if __name__ == "__main__":
    main()
