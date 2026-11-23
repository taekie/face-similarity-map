"""Reproducible analysis of the supplied, already aligned composite-face grid."""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch
from facenet_pytorch import InceptionResnetV1
from sklearn.cluster import AgglomerativeClustering
from sklearn.manifold import trustworthiness
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_distances
from umap import UMAP

ROOT = Path(__file__).resolve().parent
LABELS = [
    ["Uzbek", "Welsh", "West African", "Vietnamese", "Chinese", "Hungarian", "Japanese", "Korean", "Puerto Rican"],
    ["Thai", "African American", "Afghan", "Central African", "Burmese", "Cambodian", "English", "Ethiopian", "Filipino"],
    ["Finnish", "French", "German", "Greek", "Indian", "Iranian", "Irish", "Israeli", "Italian"],
    ["Mexican", "Latvian/Lithuanian", "Mongolian", "Peruvian", "Polish", "Romanian", "Russian", "Samoan", "South African"],
    ["South Indian", "Spaniard", "Swedish", "Swiss", "Taiwanese"],
]
# Labels are transcribed from the supplied image, not inferred from faces.
# Preserve source wording; only the missing space in CentralAfrican is normalized.
X_EDGES = [0, 138, 277, 415, 554, 692, 831, 970, 1108, 1248]
Y_START = [0, 227, 454, 678, 902]
COLORS = ["#2563a6", "#c66a2a", "#31816b", "#9b64a7", "#bb4e64", "#7c8735", "#498f9e", "#8e6d53", "#d4a12c", "#6577b8", "#b45c92", "#52a6a0", "#a67b36", "#6d9b48", "#c27d75"]


def thumbnail(im):
    buffer = io.BytesIO()
    im.save(buffer, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def crop_grid(source, out):
    im = Image.open(source).convert("RGB")
    if im.size != (1248, 1129):
        raise ValueError("This grid manifest expects the supplied 1248 x 1129 image.")
    (out / "faces").mkdir(exist_ok=True)
    (out / "label-strips").mkdir(exist_ok=True)
    records, faces = [], []
    for row, labels in enumerate(LABELS):
        y = Y_START[row]
        for col, label in enumerate(labels):
            x0, x1 = X_EDGES[col:col + 2]
            # Every face gets the same square field of view: no detector, no mask,
            # no stretching. This excludes all text and the lower neck area.
            side = 138
            cx = (x0 + x1) / 2
            box = [round(cx - side / 2), y + 22, round(cx - side / 2) + side, y + 22 + side]
            face = im.crop(box).resize((160, 160), Image.Resampling.BILINEAR)
            i = len(records)
            slug = label.lower().replace("/", "-").replace(" ", "-")
            filename = f"{i + 1:02d}-{slug}.png"
            face.save(out / "faces" / filename)
            im.crop((x0, y + 192, x1, min(y + 226, im.height))).save(out / "label-strips" / filename)
            records.append(dict(id=i, label=label, row=row + 1, column=col + 1,
                                crop_box=box, face_file="faces/" + filename,
                                label_source="manual transcription of supplied image",
                                image=thumbnail(face)))
            faces.append(face)
    # A contact sheet makes every crop and label reviewable before inference.
    sheet = Image.new("RGB", (9 * 154, 5 * 190), "#f5f4ef")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
    for rec, face in zip(records, faces):
        x, y = (rec["column"] - 1) * 154, (rec["row"] - 1) * 190
        sheet.paste(face.resize((138, 138)), (x + 8, y + 5))
        label = rec["label"]
        if draw.textlength(label, font=font) > 150:
            label = label.replace("/", "/\n").replace("African American", "African\nAmerican")
        draw.multiline_text((x + 77, y + 149), label, fill="#222222", font=font, anchor="ma", align="center")
    sheet.save(out / "crop-contact-sheet.png")
    (out / "crop-manifest.json").write_text(json.dumps([{k: v for k, v in r.items() if k != "image"} for r in records], indent=2))
    return records, faces


def embeddings(faces, out):
    torch.set_num_threads(4)
    torch.manual_seed(42)
    # Matches facenet-pytorch fixed_image_standardization; do not use ImageNet normalization.
    tensor = torch.stack([torch.from_numpy(np.array(f).copy()).permute(2, 0, 1).float() for f in faces])
    tensor = (tensor - 127.5) / 128.0
    print("Loading InceptionResnetV1 / VGGFace2 weights...", flush=True)
    model = InceptionResnetV1(pretrained="vggface2").eval()
    with torch.inference_mode():
        vectors = torch.cat([model(batch) for batch in tensor.split(16)]).cpu().numpy()
    assert vectors.shape == (41, 512)
    assert np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5)
    np.save(out / "embeddings.npy", vectors)
    return vectors


def analyze(records, vectors, out):
    distances = cosine_distances(vectors).clip(0, 2)
    np.fill_diagonal(distances, 0)
    np.save(out / "cosine-distances.npy", distances)
    write_csv(out / "cosine-distances.csv", [dict(label=r["label"], **{q["label"]: float(distances[i, j]) for j, q in enumerate(records)}) for i, r in enumerate(records)])
    scores, clusters = {}, {}
    for k in range(2, 16):
        assignment = AgglomerativeClustering(n_clusters=k, metric="precomputed", linkage="average").fit_predict(distances)
        clusters[str(k)] = assignment.tolist()
        scores[str(k)] = float(silhouette_score(distances, assignment, metric="precomputed"))
    best_k = max(scores, key=scores.get)
    layouts, quality = {}, {}
    for neighbors, seed in [(10, 42), (5, 42), (15, 42), (10, 7), (10, 123)]:
        key = f"n{neighbors}-seed{seed}"
        print(f"UMAP {key}...", flush=True)
        coords = UMAP(n_components=2, n_neighbors=neighbors, min_dist=0.15,
                      metric="cosine", random_state=seed, n_jobs=1).fit_transform(vectors)
        layouts[key] = coords.tolist()
        lowd = np.linalg.norm(coords[:, None] - coords[None, :], axis=2)
        np.fill_diagonal(lowd, np.inf)
        highd = distances.copy()
        np.fill_diagonal(highd, np.inf)
        recall = np.mean([len(set(np.argsort(highd[i])[:5]) & set(np.argsort(lowd[i])[:5])) / 5 for i in range(len(records))])
        quality[key] = dict(trustworthiness_5=float(trustworthiness(vectors, coords, n_neighbors=5, metric="cosine")), neighbor_recall_5=float(recall))
    for i, record in enumerate(records):
        record["neighbors"] = [dict(id=int(j), cosine_distance=float(distances[i, j]), cosine_similarity=float(1 - distances[i, j])) for j in np.argsort(distances[i]) if j != i][:5]
    payload = dict(records=records, layouts=layouts, clusters=clusters, scores=scores,
                   best_k=int(best_k), default_k=10, max_k=15, quality=quality, colors=COLORS)
    (out / "analysis.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    coords = np.array(layouts["n10-seed42"])
    write_csv(out / "coordinates-and-clusters.csv", [dict(id=i + 1, label=r["label"], umap_x=float(coords[i, 0]), umap_y=float(coords[i, 1]), **{f"cluster_k{k}": clusters[str(k)][i] + 1 for k in range(2, 16)}, nearest_label=records[r["neighbors"][0]["id"]]["label"], nearest_cosine_similarity=r["neighbors"][0]["cosine_similarity"]) for i, r in enumerate(records)])
    return payload


def static_plot(data, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.offsetbox import AnnotationBbox, OffsetImage
    import subprocess
    # Reuse the exact D3 simulation used in the interactive viewer.
    script = """
const fs = require('fs');
const d3 = require('./d3.v7.min.js');
eval(fs.readFileSync('./force-layout.js', 'utf8'));
console.log(JSON.stringify(faceLayout(JSON.parse(fs.readFileSync(0,'utf8')),48,true,true)));
"""
    computed = json.loads(subprocess.run(["node", "-e", script], cwd=ROOT,
        input=json.dumps(data["layouts"]["n10-seed42"]), text=True,
        capture_output=True, check=True).stdout)
    (out / "force-layout.json").write_text(json.dumps(computed, indent=2))
    anchors, pos = np.array(computed["anchors"]), np.array(computed["pos"])
    anchors[:, 1] *= -1
    pos[:, 1] *= -1
    fig, ax = plt.subplots(figsize=(16, 9), facecolor="#f6f5f1")
    ax.set_facecolor("#f6f5f1")
    display_k = data.get("default_k", 10)
    assignments = data["clusters"][str(display_k)]
    from scipy.spatial import ConvexHull
    from matplotlib.patches import Polygon
    angles = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    circle = np.column_stack([np.cos(angles), np.sin(angles)]) * 48
    for cluster in range(display_k):
        points = pos[np.array(assignments) == cluster]
        expanded = (points[:, None, :] + circle[None, :, :]).reshape(-1, 2)
        hull = expanded[ConvexHull(expanded).vertices]
        ax.add_patch(Polygon(hull, facecolor=COLORS[cluster], edgecolor=COLORS[cluster], alpha=.10, linewidth=1, zorder=0))
    for i, r in enumerate(data["records"]):
        color = COLORS[assignments[i]]
        face = Image.open(out / r["face_file"]).resize((64, 64))
        box = AnnotationBbox(OffsetImage(np.asarray(face), zoom=.7), pos[i], frameon=True,
                             bboxprops=dict(edgecolor=color, linewidth=1.5, boxstyle="round,pad=.08"))
        ax.add_artist(box)
        ax.annotate(r["label"], pos[i], xytext=(0, -29), textcoords="offset points", ha="center", va="top", fontsize=7.5, color="#25282a")
    ax.set_xlim(min(anchors[:, 0].min(), pos[:, 0].min()) - 65, max(anchors[:, 0].max(), pos[:, 0].max()) + 65)
    ax.set_ylim(min(anchors[:, 1].min(), pos[:, 1].min()) - 70, max(anchors[:, 1].max(), pos[:, 1].max()) + 65)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.suptitle("Composite faces · FaceNet similarity map", x=.07, ha="left", y=.97, fontsize=24, color="#22262a")
    fig.text(.07, .92, f"41 supplied images  /  512D FaceNet → 2D UMAP  /  exploratory cosine clusters: k={display_k}", fontsize=11, color="#62676a")
    fig.subplots_adjust(top=.86, bottom=.14, left=.05, right=.97)
    fig.text(.07, .045, "Images start at UMAP coordinates; anchored D3 forces prevent overlap. Colors come from clustering in 512D.", fontsize=9, color="#62676a")
    fig.text(.07, .025, "Source labels are transcribed metadata. These composites do not establish national or ethnic facial types. UMAP distances are approximate.", fontsize=9, color="#62676a")
    fig.savefig(out / "facenet-umap.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("/Users/taekie/Downloads/world faces.jpeg"))
    parser.add_argument("--reuse-embeddings", action="store_true")
    args = parser.parse_args()
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    records, faces = crop_grid(args.source, out)
    print(f"Cropped {len(records)} faces; contact sheet saved.", flush=True)
    vectors = np.load(out / "embeddings.npy") if args.reuse_embeddings else embeddings(faces, out)
    data = analyze(records, vectors, out)
    from build_viewer import build_viewer
    build_viewer(data, out)
    static_plot(data, out)
    manifest = dict(source=str(args.source), source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
                    samples=len(records), embedding_shape=list(vectors.shape), model="facenet-pytorch InceptionResnetV1, VGGFace2",
                    preprocessing="fixed 138px square crop, row y+22; bilinear resize to 160px; (pixel-127.5)/128; no MTCNN",
                    clustering="average-linkage agglomerative, cosine distance in original L2-normalized 512D embeddings",
                    silhouette_scores=data["scores"], exploratory_best_k=data["best_k"], default_cluster_k=10, max_cluster_k=15, quality=data["quality"])
    (out / "run-metadata.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
