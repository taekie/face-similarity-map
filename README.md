# Face Similarity Map

An interactive world map exploring visual similarities between 41 composite portraits.

**Live site:** https://taekie.github.io/face-similarity-map/

Select a portrait to see its nearest faces in a simple list without nested cards. Cosine similarities are displayed as rounded integer percentages (cosine × 100), which are scores rather than probabilities. Click outside to clear the selection. Options below the map control portrait size, 2–15 clusters (default 10), cluster hulls, and a directed nearest-neighbor graph. Reciprocal nearest neighbors use two separated arrows. Portraits stay the same screen size as the map zooms. The map starts at the top of the page and uses its full width, with only the title fixed at the upper left; nearest faces appear in a floating panel at its upper right only while a portrait is selected. Click outside or use the panel’s close button to clear the selection.

Cluster names summarize the regions in the supplied labels. `data/cluster-names.json` names all 28 distinct member sets found across k=2–15; a group retains its name when its members are unchanged. Color-matched hull labels avoid portraits and other names and are repositioned during zoom. These names do not infer ancestry.

Design by [@taekie](https://x.com/taekie).

## Build and deploy

The site is static and runs in the browser. Portraits, D3, map geometry, and analysis data are embedded in the HTML; favicon assets are separate local files.

```sh
python3 -m venv .venv
.venv/bin/pip install numpy
.venv/bin/python prepare_pages.py
```

Commit the regenerated `docs/` files and push to `main`. GitHub Pages publishes from `main` → `/docs`. No model download or inference is needed to rebuild the viewer from the committed analysis data.

`viewer.html` contains the UI template and selection state. `world-view.js` renders the map, collision layout, hulls, and similarity links. `build_viewer.py` assembles `output/index.html`; `prepare_pages.py` copies the public web assets into `docs/`.

## Analysis

1. Manually transcribe the original labels and crop the same 138×138 region from each portrait. No automatic face detection or landmark alignment is used.
2. Resize to 160×160 and normalize with `(pixel - 127.5) / 128`.
3. Extract L2-normalized 512-dimensional embeddings using `facenet-pytorch` InceptionResnetV1 pretrained on VGGFace2.
4. Compute cosine similarities and average-linkage agglomerative clusters for k=2–15.
5. Place portraits at representative coordinates mapped manually from the original labels. D3 collision forces reduce overlap; geographic positions are display anchors, not values inferred from the faces.

Nearest-neighbor relationships use the original 512-dimensional embeddings. Map distance, force-layout distance, and cluster hull area do not encode similarity. UMAP coordinates remain in the analysis data but are not shown in the current interface.

To repeat the image analysis with the original collage available locally:

```sh
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/python analyze.py --source '/path/to/world faces.jpeg'
.venv/bin/python prepare_pages.py
```

`output/embeddings.npy` has shape `(41, 512)`; `output/cosine-distances.npy` has shape `(41, 41)`. The original collage and model weights are not included.

## Images and interpretation

The composite portraits are attributed to The Postnational Monitor’s *World of Averages / World of Facial Averages* series, made using the FaceResearch.org averaging tool. They were not made by the FaceResearch research team. The compiler of this particular 41-portrait collage is unconfirmed. See `data/source-provenance.json` and [Lisa DeBruine’s clarification](https://feministphilosophers.wordpress.com/2011/02/06/the-average-face-of-women-across-the-world/#comment-30613).

These are selected composite images, not representative population samples. Original labels mix countries, regions, and groups. Similarities do not measure genetic distance or establish population ancestry. Coordinates and hulls do not indicate an individual’s origin or a group’s territory.

## Sources

- [The Postnational Monitor: World of Facial Averages](https://pmsol3.wordpress.com/2009/10/10/world-of-facial-averages-east-southeast-asia-pacific-islander/)
- [facenet-pytorch](https://github.com/timesler/facenet-pytorch)
- [Natural Earth map data](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson)
- D3 v7.9.0; its license is preserved in `D3-LICENSE`.
