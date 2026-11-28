#!/usr/bin/env bash
# Reproduces every table and figure. Needs a CUDA GPU (ACE), internet (NetVLAD weights, ACE/hloc repos, pose files) and chess.zip + stairs.zip of 7-Scenes.
# Usage: bash run_all.sh /path/to/folder_with_chess.zip_and_stairs.zip
set -euo pipefail
export P22_ZIPS="${1:-./7scenes}"; export P22_WORK="${P22_WORK:-./p22_work}"
pip install -q -r requirements.txt
jupyter nbconvert --to notebook --execute P22_Indoor_Camera_Relocalisation.ipynb --output executed.ipynb --ExecutePreprocessor.timeout=-1
cp -r "$P22_WORK"/results/* results/ 2>/dev/null || true
echo "Done. Tables/figures/logs are in ./results"
