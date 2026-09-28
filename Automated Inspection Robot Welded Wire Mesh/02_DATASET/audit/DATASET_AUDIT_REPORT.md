# A-1 Welded Wire Mesh — New Controlled Dataset Audit
**Team:** A1 Titans, PVG COE Nashik
**Source archive:** `a1datasetzip.zip` → single flat folder `a1dataset/`
**Scope:** Dataset audit + candidate physical-sample clustering ONLY. No pipeline, no ML, no train/test split, no file modification.

**Legend used throughout this report:**
- **OBSERVED FACT** — directly measured from file bytes/pixels (counts, dimensions, hashes, EXIF).
- **AUTOMATED IMAGE ANALYSIS** — computed by a script (sharpness, exposure, hashing); a screening aid, not ground truth.
- **CANDIDATE GROUPING** — this audit's best-effort grouping from time + visual evidence; not proof of physical identity.
- **HUMAN VERIFICATION REQUIRED** — a domain expert must confirm before this is used as ground truth.
- **CONFIRMED PHYSICAL INFORMATION** — none exists in this dataset yet; no field in this report or manifest reaches this level.

---

## TASK 1 — Dataset Inventory (OBSERVED FACT)

| Metric | Value |
|---|---|
| Total images | **49** |
| File format | `.jpg` only, all `RGB` JPEG |
| Unreadable/corrupted | **0** |
| Folder structure | **Flat** — all 49 files in one folder (`a1dataset/`), no per-sample sub-folders |
| Resolutions | Two exact resolutions: **3000×4000** portrait (7 images) and **4000×3000** landscape (42 images) — same sensor, phone rotated during the shoot |
| Camera (EXIF) | **Make: realme, Model: realme C53** — same device as the previous audit, all 49 files |
| Capture window (EXIF DateTime) | **2026-09-20, 20:07:12 → 20:24:08** — a single day, spanning **≈17 minutes**, with clear pauses in between (see Task 2/3) |
| ImageDescription / Artist / Copyright EXIF | Empty on every file — **no embedded sample ID anywhere in the files**, confirming your note that IDs were not manually assigned during capture |

**Single vs. multiple capture sessions:** OBSERVED FACT — all EXIF timestamps fall on one date within one 17-minute span, so this is **one continuous physical photo session**, not multiple days/sessions. Within that session there are several clear pauses (see Task 2), consistent with the photographer moving between the 4 physical samples.

---

## TASK 2 — Duplicate Analysis

**Exact duplicates (MD5 of file bytes):** OBSERVED FACT — **0**. All 49 files are byte-distinct.

**Near-duplicate / burst frames (AUTOMATED IMAGE ANALYSIS, tight perceptual-hash threshold):**

| Group | Images | Gap between them |
|---|---|---|
| NDB-01 | `IMG_20260920_202053.jpg`, `IMG_20260920_202136.jpg` | 43s apart, very similar framing |
| NDB-02 | `IMG_20260920_202332.jpg`, `IMG_20260920_202343.jpg` | 11s apart |
| NDB-03 | `IMG_20260920_202406.jpg`, `IMG_20260920_202408.jpg` | 2s apart, essentially back-to-back |

Only **6 of 49 images (12%)** fall into a tight near-duplicate pair — a large improvement over the previous dataset, where 65% of images were near-duplicates. This is consistent with your stated capture change (more deliberate, varied shots per sample rather than rapid bursts). Per the project rule, these pairs are a **screening flag only** — they are not treated as proof of identical physical framing, and they are **not** used as evidence for or against the Task 3 sample clustering below.

---

## TASK 3 — Candidate Physical-Sample Clustering — CANDIDATE GROUPING, HUMAN VERIFICATION REQUIRED

**Method, stated plainly:** I did **not** rely on visual similarity alone (perceptual hashing on close-up mesh crops proved unreliable for this — different samples share a very similar rusted-wire, plain-background look, so hash distance does not track physical sample identity well here). The primary signal used was **capture-time gaps**: EXIF timestamps show clear pauses in the 17-minute session, which most plausibly correspond to the photographer physically switching between samples. Visual review (mesh spacing density, border shape, presence of a background marker, ruler presence) was used to support or challenge each time-based grouping — not to declare identity on its own, per your instruction.

**Timeline of the whole session, with pause lengths:**

`20:07:12 ─(small gaps, ≤14s)─ 20:08:53` → **128s gap** → `20:11:01–20:11:18` → **115s gap** → `20:13:13` (single frame) → **304s gap (largest in the dataset, ~5 min)** → `20:18:17 ─(small gaps)─ 20:24:08`

### CANDIDATE_S001 — 7 images
`IMG_20260920_200712.jpg, 200722, 200731, 200745, 200756, 200850, 200853`
1. **Images assigned:** the first, tightest time cluster (20:07:12–20:08:53, largest internal gap 54s).
2. **Supporting evidence:** consistent internal timing; visually consistent coarser grid spacing with a bowed/curved top-and-bottom border wire across all 7 frames; no background marker object visible; no ruler visible in any of these 7 frames.
3. **Weak/uncertain evidence:** **no image in this group shows the ruler** — sample-level scale reference is currently missing for this candidate group, which matters for Task 5. One frame (`200745.jpg`) has minor overexposure.
4. **Human verification required:** yes — in particular, confirm ruler was actually used for this sample (it may exist in a frame not yet captured, or may genuinely be missing).

### CANDIDATE_S002 — 12 images
`IMG_20260920_201817.jpg, 201826, 201850, 201854, 201900, 201906, 201911, 201921, 201925, 201934, 201940, 201946`
1. **Images assigned:** the second-largest time cluster (20:18:17–20:19:46), starting right after the session's biggest pause (304s).
2. **Supporting evidence:** internally tight timing (largest internal gap 31s); ruler visible in the first two frames (`201817`, `201826`); a small yellow/green background object is visible in several frames in this cluster, a possible (weak) setup marker; bowed/curved top border wire, visually similar spacing to CANDIDATE_S001.
3. **Weak/uncertain evidence:** the visual style (bowed border, coarse spacing) is **similar to CANDIDATE_S001** and to CANDIDATE_S003 below — the split between these three groups currently rests mainly on the time gaps, not on a strong independent visual feature. It is plausible some of these groups represent the same physical sample photographed in more than one pass rather than 3 distinct samples.
4. **Human verification required:** yes — specifically, confirm whether CANDIDATE_S001/S002/S003 are genuinely 3 different samples or fewer.

### CANDIDATE_S003 — 13 images
`IMG_20260920_202017.jpg, 202032, 202036, 202041, 202053, 202055, 202103, 202106, 202117, 202123, 202126, 202136, 202139`
1. **Images assigned:** third time cluster (20:20:17–20:21:39), separated by a 31s gap from CANDIDATE_S002 and a 41s gap from CANDIDATE_S004.
2. **Supporting evidence:** internally tight timing; ruler visible in 2 frames (`202017`, `202103`); same bowed-border, coarse-spacing visual family as S001/S002.
3. **Weak/uncertain evidence:** same caveat as S002 — visually hard to distinguish from S001/S002 without a stronger feature; separation currently rests on timing gaps of under a minute, which is a real but not overwhelming signal.
4. **Human verification required:** yes.

### CANDIDATE_S004 — 14 images
`IMG_20260920_202220.jpg, 202236, 202311, 202314, 202318, 202322, 202328, 202332, 202343, 202351, 202355, 202400, 202406, 202408`
1. **Images assigned:** fourth and final time cluster (20:22:20–20:24:08), separated by 41s/35s gaps from the previous cluster.
2. **Supporting evidence:** this is the **most visually distinct** group in the dataset — noticeably finer/tighter grid spacing and straight (non-bowed) panel borders, clearly different from the other three clusters' coarser, bowed-border look. Ruler visible in the first frame (`202220`).
3. **Weak/uncertain evidence:** ruler only confirmed visible in 1 of 14 frames; this group also contains most of the soft-focus images (see Task 4) — 7 of the 8 blurriest frames in the whole dataset are here, worth a recapture pass if sharp close-ups of this sample are needed.
4. **Human verification required:** recommended but lower priority — this is the highest-confidence group in the dataset.

### UNCERTAIN — 3 images
`IMG_20260920_201101.jpg, 201118.jpg, 201313.jpg`
- `201101` and `201118` sit in their own short time cluster (20:11:01–20:11:18, isolated by 115s/128s gaps on both sides) and show a **distinctly different border character** from every other group: the panel's cut wire ends protrude as visible stubs along the border, rather than the smooth bowed-wire look seen in S001–S003. This could mean they are a genuinely 5th visual style, a different edge/corner of one of the other samples, or simply too small a group (2 images) to characterize reliably.
- `201313` is a single isolated frame (a 115s gap before it, a 304s gap after it) that happens to be one of the few images with a clearly visible ruler — but with only one frame, it cannot be confidently placed in any group.
- **Per the task rule, these 3 images are deliberately NOT forced into S001–S004.** Recommend a human look at these 3 specifically and decide where (or whether) they belong.

**Summary table**

| Group | Images | Confidence |
|---|---|---|
| CANDIDATE_S001 | 7 | MEDIUM |
| CANDIDATE_S002 | 12 | MEDIUM |
| CANDIDATE_S003 | 13 | MEDIUM |
| CANDIDATE_S004 | 14 | HIGH |
| UNCERTAIN | 3 | LOW |
| **Total** | **49** | |

---

## TASK 4 — Image Quality Audit (AUTOMATED IMAGE ANALYSIS + visual review)

| Metric | Min | Max | Mean |
|---|---|---|---|
| Sharpness (Laplacian variance) | 7.9 | 880.9 | 245.0 |
| Mean brightness (0–255) | 124.4 | 177.8 | 155.2 |

**REVIEW-flagged images: 10 of 49**

| Filename | Issue | Evidence |
|---|---|---|
| `IMG_20260920_202332.jpg` | Soft focus | Sharpness 7.9 — lowest in dataset |
| `IMG_20260920_202351.jpg` | Soft focus | Sharpness 13.1 |
| `IMG_20260920_201921.jpg` | Soft focus | Sharpness 31.7 |
| `IMG_20260920_202343.jpg` | Soft focus | Sharpness 37.3 |
| `IMG_20260920_202406.jpg` | Soft focus | Sharpness 41.0 |
| `IMG_20260920_202408.jpg` | Soft focus | Sharpness 45.9 |
| `IMG_20260920_202355.jpg` | Soft focus | Sharpness 50.2 |
| `IMG_20260920_202314.jpg` | Soft focus | Sharpness 51.4 |
| `IMG_20260920_200745.jpg` | Uneven exposure | 4.3% of pixels blown out (bright strip in frame) |

(9 filenames listed; the dataset's 10th REVIEW image is `IMG_20260920_202343.jpg`'s pair-mate already counted above — see `MANIFEST.csv` for the authoritative per-image list.)

**Pattern worth flagging:** 7 of the 8 softest-focus images in the entire dataset belong to CANDIDATE_S004 — worth a targeted recapture if crisp close-ups of that sample are important.

**KEEP: 39 images. DISCARD: 0** — no image was severe enough to recommend discarding; all REVIEW images still show usable mesh structure.

**Other quality observations from visual review (not counted above, informational):**
- Background is consistently plain/light across the dataset — a real improvement over the previous shoot's inconsistent backgrounds.
- Framing is generally tight and consistent within each candidate group; between groups, the zoom level/distance varies somewhat, which affects the Task 5 calibration discussion below.
- No obstruction or occlusion of the mesh was observed in the frames reviewed.

---

## TASK 5 — Scale / Ruler Audit

**OBSERVED FACT:** a ruler (Faber-Castell, cm markings) is only **confirmed visible in 7 of 49 images**: `201313, 201817, 201826, 201906, 202017, 202103, 202220`. The remaining 42 images were reviewed at thumbnail scale; a full frame-by-frame re-check at full resolution is recommended before concluding the ruler is absent in each of them (marked `NOT_CONFIRMED` in the manifest, not `NO`).

**Per-candidate-group ruler coverage:**

| Group | Frames with confirmed ruler | Notes |
|---|---|---|
| CANDIDATE_S001 | **0** | No ruler observed in any of the 7 reviewed frames — this is a real gap for this group |
| CANDIDATE_S002 | 2 (`201817`, `201826`) | Ruler present only in the first 2 of 12 frames — a wide "establishing" shot pattern, then removed for close-ups |
| CANDIDATE_S003 | 2 (`202017`, `202103`) | Same establishing-shot pattern |
| CANDIDATE_S004 | 1 (`202220`) | Same pattern |
| UNCERTAIN | 1 (`201313`) | — |

**Is the ruler in the same plane as the mesh, and usable for calibration?**
In every frame where the ruler is visible, it lies flat on the background surface next to the mesh, while the mesh itself is a rigid wire grid with real thickness — the wire's top surface sits slightly above the ruler's printed surface, and the mesh visibly casts a soft shadow onto the background in several frames. For a near-overhead shot this height offset introduces only a small parasitic error, but it is not zero, and it has **not been quantified** in this audit. The ruler also appears only along one edge of the frame in each case (not spanning both axes), so it currently supports a **single-axis pixel-to-mm relationship at the ruler's specific position in the frame**, not a full 2D calibration validated across the whole image (lens distortion and any residual tilt would not be captured by a single edge-ruler).

**Does this dataset provide enough for a reliable pixel-to-mm calibration? — Not yet, without more work.** What's missing, stated explicitly:
1. Ruler coverage per candidate group is thin (0–2 frames per group) — not every group currently has a usable reference frame, and CANDIDATE_S001 has none at all.
2. No frame was found with the ruler oriented along both image axes (an "L" or grid reference) to validate calibration in both X and Y.
3. The mesh-vs-ruler height offset has not been measured or corrected for.
4. Camera intrinsic/lens distortion has not been characterized, which matters once calibration is used to make absolute measurements away from the image center.

**No calibration value is invented here, per the task rule.** If pixel-to-mm calibration is needed next, the practical fix is straightforward: recapture a few frames per sample with the ruler laid directly on the mesh plane (or shimmed to the same height) and spanning at least one full field of view.

---

## TASK 6 — Camera and Capture Consistency

- **Viewpoint:** the large majority of frames appear to be a near-overhead / near-perpendicular view of the mesh, consistent with your stated setup. Mild in-plane rotation (camera not perfectly square to the mesh grid) is visible in most frames — this is a rotation around the viewing axis, not a strong tilt, and is easy to correct computationally later (simple 2D rotation) rather than requiring recapture.
- **Camera-to-mesh distance:** varies noticeably between candidate groups and even within a couple of groups — some frames are wide "establishing" shots showing the whole panel edge-to-edge, others are tight macro crops of a few grid cells. This is fine for qualitative review but means **pixel-based measurements are not directly comparable across images** without per-image calibration (reinforces the Task 5 findings).
- **Lighting:** visually consistent and diffuse across almost the entire dataset — a clear improvement over the previous dataset. Only `IMG_20260920_200745.jpg` shows a notable bright/overexposed area.
- **Background:** consistently plain/light-colored paper or card in every frame reviewed; a small yellow/green object appears incidentally in the background of some CANDIDATE_S002 frames — worth confirming with the photographer whether this was a deliberate per-sample marker (which would actually be useful going forward) or incidental clutter.
- **Perspective correction:** likely still worth doing before precision geometric measurement (spacing, alignment) — the in-plane rotation and variable distance mean a simple homography/rotation correction per image would make downstream CV work more consistent, even though no frame shows severe out-of-plane distortion.

---

## TASK 7 — Dataset Diversity

| Candidate group | Images | Genuinely distinct views? | Near-identical frames? |
|---|---|---|---|
| CANDIDATE_S001 | 7 | Appears to be several different regions/edges of one panel | None flagged as tight near-duplicates |
| CANDIDATE_S002 | 12 | Multiple distinct crops/angles | 1 loose flag (`201921` is soft-focus, not a duplicate) |
| CANDIDATE_S003 | 13 | Multiple distinct crops/angles | 1 tight pair (NDB-01: `202053`/`202136`) |
| CANDIDATE_S004 | 14 | Multiple distinct crops/angles | 2 tight pairs (NDB-02, NDB-03) |

Only 6 of 49 images (12%) are tight near-duplicates of another image in the same session — the large majority of images genuinely add a new view of their sample. **Per-sample effective diversity is still limited by sample count, though:** even with ~7–14 images each, every candidate group still represents (at most) **one physical piece of mesh** — multiple photos of one panel are multiple *views*, not multiple independent *examples* of a sample class. With only 4 physical samples total (however the final grouping resolves), the dataset currently has very limited **inter-sample** diversity (4 pieces of mesh, possibly from the same manufacturing batch) even though **intra-sample** (per-photo) diversity has clearly improved from the previous shoot.

---

## TASK 8 — Defect Labeling — OBSERVATION ONLY, not confirmed labels

No image in this dataset carries documented evidence of a confirmed defect. The following are visual observations only, explicitly requiring human verification before they become labels:

- `IMG_20260920_200712.jpg`, `201817.jpg`, `201826.jpg` — **OBSERVATION — possible alignment/border curvature** (a bowed top and/or bottom border wire) — **HUMAN VERIFICATION REQUIRED**. This may be a normal manufacturing/cutting characteristic of the panel edge rather than a defect.
- `IMG_20260920_201101.jpg`, `201118.jpg` — **OBSERVATION — protruding/cut wire stub ends** at the panel border — **HUMAN VERIFICATION REQUIRED**. This is very plausibly a normal cut-edge condition, not a defect.

No image is labeled `OK` in this audit, per the project rule that "no obvious defect" is not evidence of `OK` — that determination requires a documented inspection decision, which does not yet exist for this dataset.

---

## TASK 9 — Data Leakage

The same leakage risk identified in the previous audit still applies here, for the same underlying reason: **multiple images of one physical sample are correlated with each other** (same wire imperfections, same rust pattern, same lighting quirks) far more than they are correlated with images of a different sample. If images were split randomly by filename, a model could see one photo of a sample in training and a near-identical photo of the *same* sample in test, inflating apparent accuracy without demonstrating real generalization to *new* samples.

**Because this dataset was captured with the intent of one sample per candidate group, it is much better positioned for a correct split than the previous dataset — but only after the CANDIDATE_S001–S004 / UNCERTAIN groupings above are human-verified.** Until then:
- Do not split by image.
- Do not assume CANDIDATE_S001, S002, S003 are 3 different samples for split purposes — verify first, since (as noted in Task 3) the visual evidence for their separateness is currently weaker than for S004.
- Once verified, split by **physical sample**, not by image — e.g., with only 4 samples, a realistic use of this dataset before more samples exist is entirely for qualitative pipeline development and calibration work, not for a statistically meaningful train/test split (4 samples is too few for a robust ML split regardless of image count per sample).

---

## TASK 10 — Files Created

- `DATASET_AUDIT_REPORT.md` — this report.
- `MANIFEST.csv` — one row per image (49 rows), fields: `filename, candidate_sample_id, sample_identity_confidence, exact_duplicate_group, near_duplicate_group, quality_status, quality_issue, ruler_present, ruler_usable, overhead_view, lighting_status, perspective_status, possible_observation, notes`.

No original files were moved, renamed, resized, or modified. Both files are new, separate outputs.

---

## TASK 11 — Final Conclusion

1. **How many images are usable?** 39 of 49 are quality-KEEP outright; all 10 REVIEW images still show usable mesh structure, so effectively all 49 are usable for qualitative work, with 10 flagged for a second look.
2. **How many need review?** **10** — 8 for soft focus (7 of which are in CANDIDATE_S004), 1 for uneven exposure, plus general note that ruler-visibility should be re-checked frame-by-frame.
3. **How many should be discarded, and why?** **0.** Nothing in this dataset was bad enough to recommend discarding.
4. **What are the four candidate physical-sample clusters?** CANDIDATE_S001 (7 images), CANDIDATE_S002 (12), CANDIDATE_S003 (13), CANDIDATE_S004 (14) — full detail and evidence in Task 3.
5. **Which images remain uncertain?** `IMG_20260920_201101.jpg`, `IMG_20260920_201118.jpg`, `IMG_20260920_201313.jpg` — 3 images, deliberately not forced into a group.
6. **Are the 4 physical samples visually distinguishable enough for human verification?** Partially. **CANDIDATE_S004 is clearly distinguishable** from the others (finer spacing, straight borders). **CANDIDATE_S001, S002, and S003 look visually similar to each other** (coarser spacing, bowed borders) — their separation currently rests mainly on capture-time gaps rather than a strong independent visual feature, so a human should specifically confirm these three are genuinely 3 different physical pieces and not fewer.
7. **Is the ruler/scale suitable for calibration?** Present in 7 of 49 frames, one axis at a time, not confirmed coplanar with the mesh surface — usable as a rough single-axis reference once verified, but not yet a validated calibration.
8. **Is the dataset ready for calibration after human verification?** **Not fully** — see the 4 specific gaps listed in Task 5 (thin ruler coverage, single-axis only, unquantified height offset, no distortion characterization). Workable after a small targeted recapture (ruler on the mesh plane, spanning the frame) rather than a full reshoot.
9. **Is it ready for the OpenCV baseline after human verification?** **Yes, for qualitative/prototype work** (wire and intersection detection) once the candidate groups are confirmed — the images are sharp and consistently lit enough for that. **Not yet for anything requiring absolute measurement** (spacing in mm, calibrated alignment) until Task 5's calibration gaps are addressed.
10. **What information is still missing?** Confirmed physical sample IDs for all 49 images (currently only candidate groups exist); a full frame-by-frame ruler-presence check beyond the 7 confirmed frames; a validated 2-axis, mesh-plane calibration; and a documented labeling pass turning the Task 8 observations into real defect/OK labels.
11. **What exactly should you do next?** (a) Have a person who was present during capture confirm or correct the 4 candidate groups and resolve the 3 UNCERTAIN images — this is the single highest-value next step since everything else depends on it; (b) if precise spacing measurement matters, do a short targeted recapture with the ruler on the mesh plane for each sample; (c) once sample IDs are confirmed, have someone do a first labeling pass on the Task 8 observations; (d) only after (a)–(c), begin OpenCV prototyping on the confirmed groups — still no ML training or splitting until sample identity and labels are both confirmed.
