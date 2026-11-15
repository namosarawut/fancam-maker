# Handoff Context — "Fancam Maker" web app

> Paste this whole file to the AI that will continue the work. The bundle `fancam-handoff.zip` (sent with this file) holds the prepared model, runtime files and reference Python scripts.

---

## 1. Who / what

- **User:** Namo, a mobile developer (Flutter/Dart, iOS). Speaks Thai. **The app UI must be in Thai.** Explanations to the user should be in Thai.
- **Goal:** a **web app** where the user can make a *fancam* from a concert video **by themselves**:
  1. load a horizontal concert video,
  2. click the one person to follow (e.g. the lead singer),
  3. the app tracks that person automatically through the whole video,
  4. it renders a **vertical 9:16 video** where a virtual camera **follows the person smoothly, like a camera operator walking with a handheld camera**, zoomed tight,
  5. export an MP4 (with the original audio).

## 2. What the user expects (acceptance criteria)

| Item | Expected |
|---|---|
| Look | Like a person holding a camera and following the singer: **continuous, smooth panning**, no hard cuts, optional slight handheld shake |
| Zoom | **Tight**: the person fills the frame head-to-feet, body ≈ **80% of the frame height** (the user sent a reference screenshot framed exactly like this) |
| Subject | Only the chosen person. Must not jump to other band members |
| Output | 9:16, 1080×1920 (720×1280 acceptable), full length, original audio, MP4 |
| Control | The user can fix wrong tracking by clicking the right person at any time in the video |

**Not acceptable (already tried, user rejected):** fixed crops that switch every few seconds with hard cuts (that is what Descript produced).

## 3. The test video (user's real case)

- `9นาฬิกา.mp4`: 1280×720, 30 fps, 104.27 s, H.264 + AAC, ~49.5 MB. Phone footage of a stage show; the camera itself pans and zooms.
- **Target:** lead singer, young man, dark messy hair, **oversized orange/rust-brown T-shirt, loose light-blue jeans**, holds a microphone.
- **Distractors:** guitarist in a red shirt, guitarists in dark patterned shirts, drummer, staff in neon-green shirt near the end.
- **Hard lighting:** purple/blue LED wall, white beams, red wash. Colors shift a lot.
- Known trouble spots (from offline tracking):
  - **36–40 s and 59–65 s:** singer at / beyond the left edge of the source frame (out of frame ~59–65 s). The camera should hold at the edge and not jump to someone else.
  - **44–48 s and 72–78 s:** tracker likely switched to another person. Needs a manual fix (anchor click) or better re-ID.
  - **≥ 98 s:** the source footage is a wide shot, the singer is tiny (~100 px tall). A tight crop there would be very blurry, so cap the zoom (minimum crop height ≈ 22–40% of source height).

## 4. What was tried and what was learned

1. **HSV color-histogram matching vs. the reference screenshot (Python, YOLOv8s):** failed. Stage lighting makes the colors unreliable; Bhattacharyya distances were 0.5–1.0 for everyone. Color alone cannot identify the person. It still helps **as one signal combined with motion continuity**.
2. **YOLOv8s + BoT-SORT multi-object tracking (Python, every 2nd frame, imgsz 960):** worked well. Produced 50 track IDs. The singer was tracks **2 (0–35 s), 120 (36–59 s), 184 (65–104 s)**, picked by eye from a contact sheet. Tracks fragment and occasionally switch IDs, so **a human pick + correction step is needed**. This is the core idea for the web app: auto-detect + track, user picks/fixes.
3. **Descript MCP (Agent Underlord):** cannot keyframe crop position/zoom smoothly. It only made fixed 2-second segments with hard cuts. The user rejected the look. Do not go back to Descript for this.
4. **Offline render design (Python, not run to completion; the user stopped it):** smooth the per-frame center with a Gaussian (σ ≈ 9–15 frames at 30 fps), smooth the box height with a median filter (31 samples) and then a Gaussian (σ ≈ 25 frames). Crop height = clamp(bbox_h × 1.2, 300 px, 720 px), width = height × 9/16, clamp inside the frame. `cv2.warpAffine` with Lanczos to 1080×1920, pipe to ffmpeg, mux the original audio. Script: `scripts/render.py`. The same math should be ported to JS.

## 5. Web app spec (what to build)

### 5.1 Tech choices (already decided and prepared)

- **Single static page** (`index.html` + own asset files). No backend; everything runs in the browser.
- **Person detector:** YOLOv8n exported to **ONNX**, input `images` float32 `[1,3,416,416]` (RGB, 0–1, letterboxed), output `output0` `[1,84,3549]`. File: `models/yolov8n.onnx` (12.7 MB). Re-create with:
  `python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='onnx', imgsz=416, simplify=True, opset=17)"`
- **Runtime:** `onnxruntime-web@1.20.1`, **self-hosted** (not from a CDN, so it works under strict CSP): `ort/ort.min.js`, `ort/ort-wasm-simd-threaded.mjs`, `ort/ort-wasm-simd-threaded.wasm`. Get them with `npm pack onnxruntime-web@1.20.1`, from `package/dist/`.
  - `ort.env.wasm.wasmPaths = './ort/'`, `ort.env.wasm.numThreads = 1` (no SharedArrayBuffer without cross-origin isolation).
  - Try `executionProviders: ['webgpu','webgl','wasm']` with fallback. If an EP fails at session creation **or at the first run**, recreate with the next one.
  - TF.js export from Ultralytics failed in this environment (Python 3.13, missing `litert_torch`), so ONNX was chosen.
- **Export:** `canvas.captureStream(30)` + audio from `AudioContext.createMediaElementSource(video)` → `MediaStreamDestination` → `MediaRecorder` (real time). Mime preference: `video/mp4;codecs=avc1.640028,mp4a.40.2` → `video/mp4` → `video/webm;codecs=vp9,opus` → `video/webm`. Optional upgrade: WebCodecs + an MP4 muxer for faster-than-real-time, frame-exact export.

### 5.2 User flow and UI (Thai labels)

1. **เลือกวิดีโอ**: file input + drag-and-drop → `URL.createObjectURL`.
2. **วิเคราะห์วิดีโอ**: sample at **10 fps** (every 0.1 s): seek → await `seeked` → draw a letterboxed 416×416 frame → detect people. Also draw a 640×360 copy and compute an appearance histogram for each box. Show progress and ETA, with a cancel button. Cache results in memory (optionally IndexedDB keyed by file name+size).
3. **เลือกคนที่จะตาม**: video + overlay canvas with the boxes of the nearest sample. Clicking a box = **anchor** (this person, at this time). Clicking empty space = **manual anchor** (center point, height taken from the last known box) for frames where the detector missed the person. Show the tracked box in green, others in grey.
4. **Timeline bar** under the video: per sample, green = detected, amber = interpolated/lost, white ticks = anchors. Click/drag to seek. Buttons: "ไปช่วงที่หลุดถัดไป" (next lost section), "ลบจุดยึด" (remove anchor).
5. **ปรับกล้อง** (live preview canvas next to the source):
   - ขนาดคนในเฟรม (subject height % of frame): default **80%**, range 40–95
   - ความนุ่มของกล้อง (smoothing seconds): default **0.6 s**, range 0.1–2
   - กล้องสั่นแบบถือมือ (handheld shake): 0–10, default 2
   - สัดส่วน (aspect): 9:16 (default) / 4:5 / 1:1
   - ความละเอียด (resolution): 1080×1920 (default) / 720×1280
   - ซูมสูงสุด (max zoom / min crop height %): default 25% of source height
6. **ส่งออกวิดีโอ**: real-time render plus a progress bar; warn the user to keep the tab visible (background tabs throttle). Then offer a download of `fancam.mp4` (or `.webm`) and show the result in a `<video>` element.

### 5.3 Algorithms

**Detection decode (YOLOv8 ONNX)**
- Letterbox: `scale = 416 / max(W,H)`, draw the scaled video centered, pad with gray (114). Keep `padX`, `padY`.
- Output `[84, N]`, N = 3549: rows 0–3 = cx, cy, w, h (input px); row 4 = person score (class 0). Keep score > 0.25, NMS IoU 0.45 (write it in JS), max 30 boxes.
- Map back: `x = (cx − padX) / scale` and so on. Drop boxes shorter than ~30 px.

**Appearance feature (per box)**
- Torso region: x 20–80%, y 15–50% of the box. Legs region: x 25–75%, y 55–90%.
- HSV histogram per region: if s < 0.2 or v < 0.15 → 4 gray bins by v, else 12 hue bins × 2 saturation bins = 28 bins per region, 56 total, L1-normalized.
- Similarity = Bhattacharyya coefficient Σ√(p·q). Weight it lightly (lighting!).

**Tracking with anchors** (re-run whenever anchors change; it is fast, the data is in memory)
- `track[i]` per sample = box or null. Anchors force `track[a]`.
- Between consecutive anchors: a **forward pass** from the left anchor, then a **backward pass** from the right anchor that fills only the nulls left by the forward pass. Before the first anchor: a backward pass. After the last anchor: a forward pass.
- Step cost for a candidate d against the last accepted box L (height Lh), with `lost` = samples since the last accept:
  - `dc = dist(center_d, center_L) / Lh`, `hr = |ln(h_d / Lh)|`, `app = sim(refHist, hist_d)`
  - `score = 1.5·app − 1.0·dc − 0.8·hr`
  - accept if `dc < min(0.6 + 0.4·lost, 3)` and `app > (lost ? 0.65 : 0.55)` and `score > 0.2`; else `lost++` and keep `L`.
  - `refHist` = 0.8 × anchor histogram + 0.2 × running average of accepted boxes.
- Also accept a **"wrong person" fix**: when the user clicks a box at time t, it becomes an anchor and everything around it is recomputed.

**Virtual camera path**
- Per sample: `cx, cy, h` from `track`; nulls → linear interpolation between known samples, hold at the ends.
- Height: median filter (9 samples), then Gaussian with σ = 2 × smoothing.
- Center: Gaussian σ = smoothing seconds × 10 samples (offline, centered, so there is no lag).
- At render time t: interpolate linearly between samples.
- `cropH = clamp(h / (subjectPct/100), srcH × minCropPct, srcH)`, `cropW = cropH × aspect`. If `cropW > srcW`, shrink both. Clamp the crop rectangle inside the source.
- Handheld shake (amplitude `k = shake/10`): `dx, dy = k × 0.012 × cropH × n(t)` with `n(t) = 0.5·sin(1.3t+p1) + 0.3·sin(2.7t+p2) + 0.2·sin(5.1t+p3)` (separate random phases for x and y); rotation `k × 0.6° × n(t)`. Add a ~3% overscan when shake > 0 so no black corners show.
- Draw: `ctx.setTransform(1,0,0,1,0,0); fill black; translate(outW/2, outH/2); rotate(r); scale(outH/cropH); translate(−cx−dx, −cy−dy); drawImage(video, 0, 0)`.
- Use `requestVideoFrameCallback` when available (frame-accurate), else `requestAnimationFrame`.

### 5.4 Hosting constraints (if published as a claude.ai artifact)

- CSP: scripts only inline / own files / a few CDNs (cdnjs, jsdelivr, unpkg). `fetch` to other hosts is blocked, so **the model and ORT files must be the artifact's own files** loaded by relative path. Publish with `publish_files` (files ≤ 20 MiB each, ≤ 64 MiB per call). The ORT `.wasm` is 11 MB and the model 12.7 MB, both fine.
- Downloads started by `<a download>` are blocked in the sandbox. Declare the `downloads` capability **after** the first publish (`declare_capabilities {downloads: true}`), then `const dl = await claude.use("downloads"); await dl.save({filename:'fancam.mp4', data: blob})`. Allowed extensions include mp4/webm. Handle `null` (hide the button and show the `<video>` instead) and the `declined` / `rate_limited` errors.
- `alert/confirm/prompt` do not work: build in-page dialogs.
- Unknown: whether the CSP allows WebAssembly compilation. If wasm fails, the WebGL/WebGPU EP must work; test this first.
- If hosted elsewhere (GitHub Pages, Netlify, or local `python -m http.server`), none of these limits apply and a normal `<a download>` works.

### 5.5 Performance targets

- Analysis at 10 fps of a 104 s video = ~1040 inferences. YOLOv8n @416 on WebGL/WebGPU ≈ 20–60 ms each, plus seek ~30 ms → **~1–2 min**. Show an ETA.
- Export is real time (~104 s) with MediaRecorder.

## 6. Bundle contents (`fancam-handoff.zip`)

```
FANCAM_CONTEXT.md            ← this file
site/models/yolov8n.onnx     ← person detector (416, ONNX opset 17)
site/ort/ort.min.js          ← onnxruntime-web 1.20.1
site/ort/ort-wasm-simd-threaded.mjs
site/ort/ort-wasm-simd-threaded.wasm
scripts/detect.py            ← attempt 1: YOLO + color histogram (failed identification)
scripts/mot.py               ← attempt 2: YOLO + BoT-SORT tracking (worked)
scripts/render.py            ← offline smooth-crop renderer (reference math)
scripts/track.py             ← Viterbi association by color (failed, kept for reference)
```
`site/index.html` has **not been written yet**: that is the next task.

## 7. Next steps for the AI

1. Write `site/index.html` following §5. Thai UI, clean dark theme, mobile-friendly layout (the user is a mobile dev and may test on a phone).
2. Verify the model loads and decodes correctly: run one frame and draw the boxes. Check that the person class is row 4 and that the coordinates map back correctly.
3. Test with the user's video: pick the singer at ~2 s, check 44–48 s and 72–78 s, and add anchors if wrong.
4. Check the preview matches the reference framing (head to feet, ~80% height), then export and confirm the audio is in sync.
5. Publish (claude.ai artifact via `publish_files`, then declare `downloads`) or give the user the folder to host.

## 8. Optional quick path (no web app)

If the user just wants this one video done: run `scripts/mot.py` (needs `pip install ultralytics lap`), pick the singer's track IDs from a contact sheet (they were 2, 120 and 184), fix the 44–48 s and 72–78 s sections, then run `scripts/render.py 1.2` (outputs `fancam.mp4`, 1080×1920, original audio). Python paths inside the scripts point to `/home/claude/...`; adjust them.
