# P22 Indoor Camera Relocalisation: NetVLAD vs ACE on 7-Scenes (Chess, Stairs)
UCS532 Open Challenge. Authors: Yajat Taneja (1024030082), Riddhima Agrawal (1024240068).

**Problem.** Where is the camera, from one RGB image? We measure error against distance to the nearest training view for NetVLAD retrieval (top-1, top-k) and ACE, on both ground-truth variants, and thin the training map (100/50/25/10 %).

**Data.** Microsoft 7-Scenes, scenes Chess and Stairs, official train/test sequences (https://www.microsoft.com/en-us/research/project/rgb-d-dataset-7-scenes/). Non-commercial licence; data is not in this repo. SfM pseudo-GT poses: https://github.com/tsattler/visloc_pseudo_gt_limitations.

**Reproduce.** `bash run_all.sh /path/to/folder_with_chess.zip_and_stairs.zip` (needs a CUDA GPU and internet). The notebook `P22_Indoor_Camera_Relocalisation.ipynb` is the single pipeline; seeds are printed in its logs. Dependencies: `requirements.txt`. Results go to `results/`.

**Hardware / runtime.** Kaggle, NVIDIA T4 GPU, about 4-5 hours for the full run (all ACE trainings are cached and resumable).

## Results (test sequences, full density; ACE = mean of 3 seeds)

| scene   | gt    | method              |   median_t_cm |   median_r_deg |   acc_5cm5deg_pct | ur_status   |
|:--------|:------|:--------------------|--------------:|---------------:|------------------:|:------------|
| chess   | dslam | NetVLAD top-1       |         24.99 |          12.54 |              0    | none        |
| chess   | dslam | NetVLAD top-k       |         20.1  |           9.44 |              0.15 | none        |
| chess   | dslam | ACE                 |          1.91 |           0.69 |             96.77 | censored    |
| chess   | dslam | Oracle nearest view |         10.94 |          22.78 |              0    | none        |
| chess   | sfm   | NetVLAD top-1       |         25.68 |          12.53 |              0    | none        |
| chess   | sfm   | NetVLAD top-k       |         20.78 |           9.3  |              0.1  | none        |
| chess   | sfm   | ACE                 |          0.58 |           0.18 |            100    | censored    |
| chess   | sfm   | Oracle nearest view |         11.3  |          23.33 |              0    | none        |
| stairs  | dslam | NetVLAD top-1       |         27.25 |          15.02 |              0    | none        |
| stairs  | dslam | NetVLAD top-k       |         25.76 |          14.62 |              0    | none        |
| stairs  | dslam | ACE                 |          3.83 |           1.1  |             70.4  | censored    |
| stairs  | dslam | Oracle nearest view |         13.84 |          28.99 |              0    | none        |
| stairs  | sfm   | NetVLAD top-1       |         27.82 |          14.99 |              0    | none        |
| stairs  | sfm   | NetVLAD top-k       |         25.84 |          14.05 |              0    | none        |
| stairs  | sfm   | ACE                 |          2.79 |           0.79 |             81.6  | censored    |
| stairs  | sfm   | Oracle nearest view |         16.75 |          21.24 |              0    | none        |

Density ablation, hypotheses and failure analysis: see `report.pdf` and `results/tables`.

## Credits
ACE (Brachmann et al., CVPR 2023, https://github.com/nianticlabs/ace, pinned commit, with three small patches saved in `results/`), hloc NetVLAD (https://github.com/cvg/Hierarchical-Localization), pseudo-GT poses (Brachmann et al., ICCV 2021), 7-Scenes (Shotton et al., CVPR 2013), NetVLAD (Arandjelovic et al., CVPR 2016), top-k interpolation after Sattler et al., CVPR 2019. Pose/metric/retrieval/analysis code is ours.

## Declarations
Contribution: both authors worked jointly on all parts through shared meetings and discussion. AI declaration: Claude (Anthropic) was used to explain concepts, to help write and debug code, and to suggest the contents and layout of the report, slides and README. Both authors ran the experiments together and verified the results together, with AI assistance.

Kaggle notebook and results in:- https://www.kaggle.com/code/yajat4444/notebook44f876b1db
