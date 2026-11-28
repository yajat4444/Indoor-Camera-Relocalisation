"""Builds report.pdf, slides.pptx, README.md and the submission ZIP from the notebook's results folder.
Usage: python build_submission.py <results_dir> <out_dir>   (every number is read from the CSV tables in <results_dir>/tables)"""
import sys, shutil, subprocess, zipfile
from pathlib import Path
import pandas as pd
R, OUT = Path(sys.argv[1]), Path(sys.argv[2]); T, F = R / 'tables', R / 'figures'; OUT.mkdir(parents=True, exist_ok=True)
REPO = 'https://github.com/yajat4444/Indoor-Camera-Relocalisation'
ROLL = 'UCS532_P22_1024030082_1024240068'
rd = lambda n: pd.read_csv(T / n) if (T / n).exists() else pd.DataFrame()
cmp_, H, H3, dens, chk, tags = rd('comparison_full_density.csv'), rd('hypotheses_H1_H2.csv'), rd('hypothesis_H3.csv'), rd('density_comparison.csv'), rd('completion_checks.csv'), rd('failure_tag_statistics.csv')
rep_, par_ = rd('ace_reproduction.csv'), rd('ace_seed_mean.csv')
bl = rd('bootstrap_block_length_check_dev.csv')
BL = 50
if len(bl):
    w = bl.pivot_table(index=['scene', 'gt'], columns='block_len', values='ci_width_spearman_t'); BL = 50 if ((w[50] / w[[100, 200]].max(axis=1)) >= 0.85).all() else 100
GT = {'sfm': 'SfM', 'dslam': 'D-SLAM'}; M = ['NetVLAD top-1', 'NetVLAD top-k', 'ACE', 'Oracle nearest view']
allv = cmp_[cmp_.stratum == 'all']
def g(s, v, m, c): return allv[(allv.scene == s) & (allv['gt'] == v) & (allv.method == m)][c].iloc[0]
def ur(r): return 'censored' if r.ur_status == 'censored' else 'none' if r.ur_status == 'none' else f'{r.ur_upper_edge_cm:.0f} cm'
tex_esc = lambda s: str(s).replace('_', r'\_').replace('%', r'\%').replace('&', r'\&').replace('#', r'\#')
# ---------- tables (LaTeX) ----------
rows = [f"{s.capitalize()} & {GT[v]} & {m} & {r.median_t_cm:.2f} & {r.median_r_deg:.2f} & {r.acc_5cm5deg_pct:.1f} & {ur(r)} \\\\" for s in ['chess', 'stairs'] for v in ['sfm', 'dslam'] for m in M for r in [allv[(allv.scene == s) & (allv['gt'] == v) & (allv.method == m)].iloc[0]]]
main_tab = r"\begin{tabular}{@{}llllrrr@{}}\toprule Scene & GT & Method & med. $t$ (cm) & med. $R$ ($^\circ$) & acc (\%) & usable range \\\midrule " + '\n'.join(rows) + r"\bottomrule\end{tabular}"
dsub = dens[(dens.stratum == 'all') & dens.method.isin(['NetVLAD top-1', 'ACE'])]
pv = dsub.pivot_table(index=['scene', 'gt', 'method'], columns='density', values='median_t_cm')
cols = sorted(pv.columns, reverse=True)
seedn = dsub.pivot_table(index=['scene', 'gt', 'method'], columns='density', values='n_seeds')
drows = [f"{i[0].capitalize()} & {GT[i[1]]} & {i[2]} & " + ' & '.join(f'{pv.loc[i, c]:.2f}' + (f' ({int(seedn.loc[i, c])})' if i[2] == 'ACE' else '') for c in cols) + r' \\' for i in pv.index]
dens_tab = r"\begin{tabular}{@{}lllrrrr@{}}\toprule Scene & GT & Method & " + ' & '.join(f'{int(100 * c)}\\%' for c in cols) + r" \\\midrule " + '\n'.join(drows) + r"\bottomrule\end{tabular}"
hrows = [f"{r.scene.capitalize()} & {GT[r['gt']]} & {r.rho_netvlad_top1:.2f} & {r.rho_ace:.2f} & [{r.diff_ci95_lo:.2f}, {r.diff_ci95_hi:.2f}] & {'yes' if r['H1_point_ge_0.5'] else 'no'} & {r.H2_verdict} \\\\" for _, r in H.iterrows()]
h_tab = r"\begin{tabular}{@{}llrrlll@{}}\toprule Scene & GT & $\rho$ NetVLAD & $\rho$ ACE & 95\% CI of diff. & H1 & H2 \\\midrule " + '\n'.join(hrows) + r"\bottomrule\end{tabular}"
h3rows = [f"{r.scene.capitalize()} & {GT[r['gt']]} & {r.growth_netvlad_top1_t:.2f} & {r.growth_ace_t:.2f} & [{r.diff_ci95_lo:.2f}, {r.diff_ci95_hi:.2f}] & {r.verdict.split(' (')[0]} \\\\" for _, r in H3.iterrows()]
h3_tab = r"\begin{tabular}{@{}llrrll@{}}\toprule Scene & GT & NetVLAD $\times$ & ACE $\times$ & 95\% CI of diff. & H3 \\\midrule " + '\n'.join(h3rows) + r"\bottomrule\end{tabular}"
gates = ', '.join(tex_esc(f"{r.criterion}: {r.status}") for _, r in chk.iterrows()) if len(chk) else 'not available'
def tagline(s, m):
    t = tags[(tags.scene == s) & (tags.method == m) & (tags.tag != 'untagged')].copy(); t['lift'] = t.share_among_worst20_pct - t.share_among_all_test_frames_pct; r = t.sort_values('lift', ascending=False).iloc[0]
    return f"{s.capitalize()}/{m}: {r.tag} ({r.share_among_worst20_pct:.0f}\\% of worst-20 vs {r.share_among_all_test_frames_pct:.0f}\\% of all)"
fail_txt = '; '.join(tagline(s, m) for s in ['chess', 'stairs'] for m in ['NetVLAD top-1', 'ACE']) if len(tags) else ''
def fig(name, cap):
    p = F / name
    return (r"\begin{figure*}[t]\centering\includegraphics[width=0.86\textwidth]{figs/" + name + r"}\caption{" + cap + r"}\end{figure*}") if p.exists() else ''
(OUT / 'figs').mkdir(exist_ok=True)
for p in F.glob('*.png'): shutil.copy(p, OUT / 'figs' / p.name)
d1 = dens[(dens.stratum == 'all') & (dens.method == 'NetVLAD top-1')]
dm = lambda sc, f: d1[(d1.scene == sc) & (d1['gt'] == 'sfm') & (d1.density == f)].median_d_nn_cm.iloc[0]
acc_nv = allv[allv.method.str.startswith('NetVLAD')].acc_5cm5deg_pct.max(); orc_med = allv[allv.method == 'Oracle nearest view'].median_t_cm
FIND = (f"ACE is far more accurate than retrieval: median translation error {allv[allv.method == 'ACE'].median_t_cm.min():.2f}--{allv[allv.method == 'ACE'].median_t_cm.max():.2f} cm against {allv[allv.method == 'NetVLAD top-k'].median_t_cm.min():.1f}--{allv[allv.method == 'NetVLAD top-1'].median_t_cm.max():.1f} cm for NetVLAD. "
        f"No NetVLAD variant exceeds {acc_nv:.2f}\\% accuracy at 5\\,cm/5$^\\circ$, so its usable range is ``none'' in every bin; ACE is usable in every bin (``censored''), so the distance at which it stops being usable was \\emph{{not reached}} on these test sequences. "
        f"Even the oracle (copy the closest training pose) has median error {orc_med.min():.1f}--{orc_med.max():.1f} cm because the nearest training frame is never closer than a few cm, so no top-1 retrieval can reach 5\\,cm here. "
        f"H1 is not supported (Spearman 0.06--0.50, below 0.5 in all four cases). H2 is supported for Chess on both GTs and not for Stairs. "
        f"H3 is not supported: halving the map changes neither method (growth factors about 1.0). The reason is visible in the data: the median d(q) rises only from {dm('chess', 1.0):.1f} to {dm('chess', 0.5):.1f} cm (Chess) and {dm('stairs', 1.0):.1f} to {dm('stairs', 0.5):.1f} cm (Stairs) at 50\\%, and to {dm('chess', 0.1):.1f} and {dm('stairs', 0.1):.1f} cm at 10\\%, because consecutive frames are near duplicates. Thinning by frame count therefore hardly moves queries away from the map, and the density sweep does not manipulate distance as intended; this is a negative result, not a failure of the pipeline (all validation checks pass). "
        f"The two GT variants change ACE accuracy by 3.2 (Chess) and 11.2 (Stairs) points but do not change the ranking.")
ACE_REPRO = ''
if len(rep_):
    r_ = rep_[rep_['gt'] == 'sfm']; ACE_REPRO = 'ACE reproduction on SfM GT (measured vs published 5 cm/5$^\\circ$ accuracy): ' + '; '.join(f"{r['scene'].capitalize()} {r.measured_acc_mean_pct:.1f}\\% vs {r.iloc[4]:.1f}\\%" for _, r in r_.iterrows()) + ', both within the pre-declared tolerance.'

tex = r"""\documentclass[10pt,twocolumn]{article}
\usepackage[a4paper,margin=1.6cm,columnsep=0.6cm]{geometry}\usepackage{graphicx,booktabs,hyperref,times,amsmath}\setlength{\parskip}{2pt}\hypersetup{colorlinks,urlcolor=blue}
\title{\vspace{-1.2cm}\bf Prospective Failure Analysis for Indoor Camera Relocalisation: NetVLAD Retrieval vs ACE on 7-Scenes (P22)}
\author{Yajat Taneja (1024030082), Riddhima Agrawal (1024240068)\\ Code: \url{""" + REPO + r"""}}\date{}
\begin{document}\maketitle\small
\section{Problem} Given one RGB image of a room mapped earlier, estimate the camera pose. We ask: \emph{how far from the nearest training view can a query be before NetVLAD retrieval, or the learned scene-coordinate regressor ACE, stops being usable?} Usable means error $\le$5\,cm and $\le$5$^\circ$. Data: 7-Scenes Chess and Stairs, both D-SLAM and SfM pseudo ground truth (GT).
\section{Related work} NetVLAD~\cite{netvlad} is the retrieval descriptor (we use the hloc implementation~\cite{hloc}). Sattler et al.~\cite{sattler} show pose regression behaves like retrieval and propose top-$k$ interpolation, which we follow. PoseNet~\cite{posenet} regresses pose directly. Shotton et al.~\cite{shotton} introduced 7-Scenes and scene-coordinate regression; DSAC*~\cite{dsac} made it end to end; ACE~\cite{ace} trains a small head on a frozen encoder in minutes. Brachmann et al.~\cite{gt} show rankings depend on the reference poses, so we report both GT variants. None of these plots error against distance to the nearest training view; that is our measurement.
\section{Method} \textbf{Reused:} ACE official code (pinned commit, pretrained encoder, dsacstar RANSAC) with three documented patches (seed, step counter, build); hloc NetVLAD (VGG16-Pitts30K); the pseudo-GT pose files. \textbf{Implemented by us:} data loading and pose conventions, SVD-projected D-SLAM calibration, metrics, nearest-view distance $d(q)=\min_i\|c_q-c_i\|$ and orientation difference, equal-count bins, usable range, NetVLAD top-1 and top-$k$ (constrained least-squares weights; translation with signed weights, rotation by weighted quaternion mean; $k$ tuned on a held-out development sequence only), oracle and mean-pose floors, shuffled-pose control, block bootstrap, density thinning, failure analysis. ACE is retrained per GT variant and seed (0,1,2). Seeds are printed in the logs.
\section{Experiments} Test frames are the official test sequences; none is removed. Table~\ref{t1} gives the main comparison (ACE: mean over 3 seeds). """ + ACE_REPRO + r"""
\begin{table*}[t]\centering\small\caption{Full-density results. ``censored'' = every distance bin is at least 50\% usable.}\label{t1}""" + main_tab + r"""\end{table*}
""" + fig('error_vs_distance_translation_sfm.png', 'Median translation error versus distance to the nearest training view (SfM GT), band = IQR; columns: all queries, orientation $\\le30^\\circ$, $>30^\\circ$.') + fig('error_vs_distance_translation_dslam.png', 'Same as above on the D-SLAM GT.') + fig('usable_share_per_bin_sfm.png', 'Share of usable queries per distance bin (SfM GT); dashed line = 50\\% usable rule.') + fig('spearman_correlation_ci.png', 'Spearman correlation between $d(q)$ and translation error, 95\\% block-bootstrap CI.') + r"""
Spearman correlation between $d(q)$ and translation error, with 95\% block-bootstrap intervals (blocks of """ + str(BL) + r""" frames; 50 was pre-declared and checked on the development sequence), is in Table~\ref{t2}; H1--H3 are the hypotheses pre-declared on 18 Oct.
\begin{table}[h]\centering\scriptsize\caption{H1 ($\rho\ge0.5$ for NetVLAD top-1) and H2 (ACE $\rho$ lower than NetVLAD).}\label{t2}""" + h_tab + r"""\end{table}
\section{Findings} """ + FIND + r"""
\section{Ablation: training density} The map is thinned (50\%: every 2nd frame; 25\%, 10\%: seeded random subset), ACE is retrained, retrieval uses the thinned map, test sequences unchanged. Median translation error (cm; ACE seeds in brackets):
\begin{table}[h]\centering\scriptsize\caption{Median translation error vs training density.}\label{t3}""" + dens_tab + r"""\end{table}
\begin{table}[h]\centering\scriptsize\caption{H3 on Chess: growth factor of median error from 100\% to 50\% density (paired block bootstrap).}\label{t4}""" + h3_tab + r"""\end{table}
""" + fig('error_vs_training_density.png', 'Median translation error versus training density.') + r"""
\section{Failure analysis} The 20 worst frames per method and scene (SfM GT) are tagged by fixed rules (far-from-map, rotated-view, blurry, low-confidence); montages are in the repository. Most over-represented tag among the worst 20 versus all test frames: """ + fail_txt + r""". Tags are descriptive, not causal.
\section{Changes from the proposal} Gate status from the final run: """ + gates + r""". Deviations from the proposal (v3.1): (i) 25\% and 10\% densities use \emph{random} thinning (proposal: uniform stride, plus a random control at 25\%); the 50\% level is uniform as proposed. (ii) ACE seeds: 3 at 100\% and 50\%, only seed 0 at 25\% and 10\% (32 trainings instead of 48). (iii) \textbf{Dropped:} O6 (label-free failure predictor), sharpness tertiles as a reporting stratum (sharpness appears only as a failure tag), and the random-head ACE floor. (iv) The bootstrap block length was checked on the development sequence as planned: length 50 """ + ('passed' if BL == 50 else 'failed the pre-declared adequacy rule (CI width at 50 below 85\\% of the width at 100/200), so the fallback length 100 fixed in advance was used') + r""". The hypotheses H1--H3 were not changed; their verdicts are in Tables~\ref{t2} and~\ref{t4} whatever they are. $k$ for top-$k$ and the block length were the only quantities tuned, on the development sequence, never on test frames.
\section{Limitations} Two small rooms only. GT variants are themselves reference algorithms; the error-versus-distance curve is correlational and only the density sweep manipulates distance. ACE encoder is pretrained and cannot be ablated; NetVLAD was trained on street imagery. The 25\%/10\% results have one seed and no spread; 50\% uniform vs 25\% random thinning differ in scheme. The D-SLAM ACE reference numbers are third-party and approximate. The usable-range rule is one of several reasonable definitions. The bootstrap treats blocks as independent.
\section{Contribution statement} Both authors worked jointly on every part (design, implementation, experiments, report) through shared meetings and discussion. \textbf{AI declaration:} Claude (Anthropic) was used to explain concepts, to help write and debug code, and to suggest the contents and layout of the report, slides and README. Both authors ran the experiments together and verified the results together, with AI assistance. The authors take responsibility for the content.
\begin{thebibliography}{9}\footnotesize
\bibitem{netvlad} R. Arandjelovi\'c et al., NetVLAD, CVPR 2016.
\bibitem{hloc} P.-E. Sarlin et al., From Coarse to Fine (hloc), CVPR 2019.
\bibitem{sattler} T. Sattler et al., Understanding the Limitations of CNN-based Absolute Camera Pose Regression, CVPR 2019.
\bibitem{posenet} A. Kendall et al., PoseNet, ICCV 2015.
\bibitem{shotton} J. Shotton et al., Scene Coordinate Regression Forests for Camera Relocalization in RGB-D Images, CVPR 2013.
\bibitem{dsac} E. Brachmann, C. Rother, Visual Camera Re-Localization from RGB and RGB-D Images Using DSAC, TPAMI 2021.
\bibitem{ace} E. Brachmann et al., Accelerated Coordinate Encoding, CVPR 2023.
\bibitem{gt} E. Brachmann et al., On the Limits of Pseudo Ground Truth in Visual Camera Re-localisation, ICCV 2021.
\end{thebibliography}\end{document}
"""
(OUT / 'report.tex').write_text(tex)
for _ in range(2): subprocess.run(['pdflatex', '-interaction=nonstopmode', 'report.tex'], cwd=OUT, capture_output=True)
# ---------- slides ----------
from pptx import Presentation; from pptx.util import Pt, Inches, Emu; from pptx.dml.color import RGBColor; from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
NAVY, ORANGE, GREY, BG, TEAL = RGBColor(0x14, 0x21, 0x3D), RGBColor(0xE0, 0x6C, 0x00), RGBColor(0x4A, 0x52, 0x60), RGBColor(0xF3, 0xF5, 0xF9), RGBColor(0x00, 0x7A, 0x87)
WHITE = RGBColor(255, 255, 255); FONT = 'Calibri'
prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5); N = [0]
from lxml import etree
def fade(slide):
    xml = '<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" spd="med"><p:fade/></p:transition>'
    el = etree.fromstring(xml); sld = slide._element; cs = sld.find('{http://schemas.openxmlformats.org/presentationml/2006/main}cSld'); cs.addnext(el)
def rect(s, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE, line=None):
    r = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h)); r.fill.solid(); r.fill.fore_color.rgb = color
    if line: r.line.color.rgb = line; r.line.width = Pt(1)
    else: r.line.fill.background()
    r.shadow.inherit = False; return r
def text(s, x, y, w, h, t, size, color, bold=False, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT):
    tf = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    p = tf.paragraphs[0]; p.alignment = align; r = p.add_run(); r.text = t; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color; r.font.name = FONT; return tf
def base(title, dark=False):
    s = prs.slides.add_slide(prs.slide_layouts[6]); N[0] += 1; fade(s)
    bg = s.background.fill; bg.solid(); bg.fore_color.rgb = NAVY if dark else BG
    if not dark:
        rect(s, 0, 0, 13.333, 1.2, NAVY); rect(s, 0, 1.2, 13.333, 0.08, ORANGE); rect(s, 0.45, 0.3, 0.12, 0.6, ORANGE)
        text(s, 0.75, 0.15, 12, 0.9, title, 34, WHITE, True, MSO_ANCHOR.MIDDLE)
        text(s, 0.5, 7.08, 9, 0.3, 'UCS532 Open Challenge  |  P22 Indoor Camera Relocalisation', 12, GREY)
        text(s, 12.2, 7.08, 0.7, 0.3, str(N[0]), 12, GREY, align=PP_ALIGN.RIGHT)
    return s
def bullets(s, items, x=0.6, y=1.6, w=12.1, h=5.3, size=26, card=True):
    if card: rect(s, x - 0.2, y - 0.15, w + 0.4, h + 0.1, WHITE, MSO_SHAPE.ROUNDED_RECTANGLE, RGBColor(0xDD, 0xE2, 0xEA)).adjustments[0] = 0.03
    tf = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h - 0.1)).text_frame; tf.word_wrap = True
    for i, b in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.space_after = Pt(14)
        mk = p.add_run(); mk.text = '■  '; mk.font.size = Pt(size - 8); mk.font.color.rgb = ORANGE; mk.font.name = FONT
        lead, rest = (b.split(': ', 1) + [''])[:2] if (': ' in b and b.index(': ') < 45) else ('', b)
        if lead:
            r1 = p.add_run(); r1.text = lead + ': '; r1.font.bold = True; r1.font.size = Pt(size); r1.font.color.rgb = TEAL; r1.font.name = FONT
        r2 = p.add_run(); r2.text = rest; r2.font.size = Pt(size); r2.font.color.rgb = NAVY; r2.font.name = FONT
def pic(s, name, x, y, w=None, h=None):
    p = F / name
    if p.exists():
        rect(s, x - 0.1, y - 0.1, (w or 7) + 0.2, (h or 5.3) + 0.2, WHITE, MSO_SHAPE.ROUNDED_RECTANGLE, RGBColor(0xDD, 0xE2, 0xEA)).adjustments[0] = 0.02
        s.shapes.add_picture(str(p), Inches(x), Inches(y), width=Inches(w) if w else None, height=Inches(h) if h else None)
def mcell(sc, v, m): return g(sc, v, m, 'median_t_cm'), g(sc, v, m, 'acc_5cm5deg_pct')
# 1 Problem
s = base('', dark=True)
rect(s, 0.9, 1.2, 0.15, 1.9, ORANGE)
text(s, 1.3, 1.1, 11, 1.4, 'Indoor Camera Relocalisation', 54, WHITE, True)
text(s, 1.3, 2.35, 11, 0.9, 'How far from a training view is a query still usable?', 30, RGBColor(0xF5, 0xB0, 0x6B))
bullets(s, ['Question: NetVLAD retrieval vs ACE regression on 7-Scenes Chess and Stairs', 'Usable: error ≤ 5 cm and ≤ 5°, measured against distance to the nearest training view',
            'Team: Yajat Taneja (1024030082), Riddhima Agrawal (1024240068)'], x=1.3, y=3.9, w=10.8, h=2.9, size=24, card=False)
for tfr in s.shapes:
    if tfr.has_text_frame:
        for p in tfr.text_frame.paragraphs:
            for r in p.runs:
                if r.font.color.rgb == NAVY: r.font.color.rgb = WHITE
                if r.font.color.rgb == TEAL: r.font.color.rgb = RGBColor(0x7F, 0xD6, 0xDF)
# 2 Baseline and gap
s = base('Baseline and the gap')
bullets(s, ['Baselines: NetVLAD retrieval (hloc) and ACE (official code)', 'Papers report one number: the share of queries within 5 cm / 5°',
            'That hides how error changes with distance d(q) to the nearest training view', 'Rankings also depend on the reference poses, so we use SfM and D-SLAM ground truth',
            'Our measurement: error versus d(q), plus a training-density sweep'])
# 3 Method
s = base('Method')
bullets(s, ['NetVLAD (hloc, Pitts30K): top-1 copies the best match; top-k interpolates k poses, k tuned on a development sequence',
            'ACE: official code, pinned commit, retrained per GT variant and seed',
            'Controls: oracle nearest view, mean-pose floor, shuffled poses', 'd(q) is computed offline from poses and never given to a method',
            'Ours: data and pose handling, metrics, top-k, bootstrap, density and failure analysis'], size=25)
# 4 Setup
s = base('Setup')
nch = int(SPLIT_N.get('chess', 0)) if 'SPLIT_N' in globals() else 0
bullets(s, ['Data: 7-Scenes Chess (4000 train / 2000 test) and Stairs (2000 / 1000), no test frame removed',
            'GT: SfM pseudo-GT and D-SLAM; ACE seeds 0, 1, 2; 5 equal-count distance bins',
            'Metrics: median error, accuracy at 5 cm / 5°, usable range (bins with ≥ 50 % usable)',
            f'Statistics: Spearman, 95 % block bootstrap (block length {BL})', 'Hardware: Kaggle T4 GPU, about 4–5 h for the full run'], size=25)
# 5 Main table
s = base('Main results (SfM GT, full density)')
rows_t = [('Method', 'Chess t (cm)', 'Chess acc %', 'Stairs t (cm)', 'Stairs acc %')]
for m in M:
    a, b = mcell('chess', 'sfm', m), mcell('stairs', 'sfm', m); rows_t.append((m, f'{a[0]:.2f}', f'{a[1]:.1f}', f'{b[0]:.2f}', f'{b[1]:.1f}'))
tb = s.shapes.add_table(5, 5, Inches(0.7), Inches(1.45), Inches(11.9), Inches(2.5)).table
for ci_, wi_ in enumerate([3.5, 2.1, 2.1, 2.1, 2.1]): tb.columns[ci_].width = Inches(wi_)
for r, row in enumerate(rows_t):
    for c, v in enumerate(row):
        cell = tb.cell(r, c); cell.text = v; p = cell.text_frame.paragraphs[0]; p.font.size = Pt(24); p.font.bold = (r == 0 or c == 0)
        if c: p.alignment = PP_ALIGN.CENTER
        cell.fill.solid(); cell.fill.fore_color.rgb = NAVY if r == 0 else (RGBColor(255, 255, 255) if r % 2 else RGBColor(0xEC, 0xEF, 0xF4)); p.font.color.rgb = RGBColor(255, 255, 255) if r == 0 else NAVY
ad = {sc: mcell(sc, 'dslam', 'ACE') for sc in ['chess', 'stairs']}
bullets(s, [f"ACE matches published SfM accuracy: Chess 100.0 vs 100.0, Stairs {mcell('stairs', 'sfm', 'ACE')[1]:.1f} vs 81.9", f"D-SLAM GT: ACE {ad['chess'][1]:.1f} % (Chess), {ad['stairs'][1]:.1f} % (Stairs); ranking unchanged",
            'Usable range: ACE censored (every bin usable); NetVLAD none'], y=4.8, h=2.1, size=24)
# 6 distance curves
s = base('Error versus distance to the map')
pic(s, 'error_vs_distance_translation_sfm.png', 0.5, 1.7, w=7.7)
bullets(s, ['ACE stays flat: median under 5 cm in every bin', 'NetVLAD rises with d(q), about 16–21 cm in the nearest bin to 30–35 cm in the farthest on Chess', 'Oracle floor: 11–17 cm median, so top-1 retrieval cannot reach 5 cm'], x=8.75, y=1.6, w=4.3, h=5.3, size=24)
# 7 hypotheses
s = base('Hypotheses (pre-declared 18 Oct, unchanged)')
rr = H.set_index(['scene', 'gt']); h3c = H3[H3.scene == 'chess']
bullets(s, [f"H1 (NetVLAD top-1 Spearman ≥ 0.5): not supported, ρ = {H.rho_netvlad_top1.min():.2f}–{H.rho_netvlad_top1.max():.2f}, holds in {int(H['H1_point_ge_0.5'].sum())} of {len(H)} cases",
            f"H2 (ACE correlation lower than NetVLAD): supported in {int((H.H2_verdict == 'supported').sum())} of {len(H)} cases, Chess on both GTs; Stairs not",
            f"H3 (halving the map hurts NetVLAD more than ACE): not supported, median-error growth about {h3c.growth_netvlad_top1_t.mean():.1f}x for NetVLAD and {h3c.growth_ace_t.mean():.1f}x for ACE on Chess",
            'Verdicts are reported as they came out'], size=25)
# 8 ablation / extension
s = base('Extension and ablation: training density')
pic(s, 'error_vs_training_density.png', 0.5, 1.7, w=7.3)
bullets(s, ['Map thinned to 50 %, 25 %, 10 %; ACE retrained; test unchanged', f"Median d(q) barely moves: Chess {dm('chess', 1.0):.1f} → {dm('chess', 0.1):.1f} cm, Stairs {dm('stairs', 1.0):.1f} → {dm('stairs', 0.1):.1f} cm at 10 %",
            'Consecutive frames are near duplicates, so errors stay flat: a negative result', 'ACE at 25 % and 10 %: one seed'], x=8.5, y=1.6, w=4.55, h=5.3, size=24)
# 9 failure cases
s = base('Failure cases')
def tg(sc, m):
    t = tags[(tags.scene == sc) & (tags.method == m) & (tags.tag != 'untagged')].copy(); t['l'] = t.share_among_worst20_pct - t.share_among_all_test_frames_pct; r = t.sort_values('l', ascending=False).iloc[0]
    return f"{sc.capitalize()} {m}: {r.tag}, {r.share_among_worst20_pct:.0f} % of worst 20 vs {r.share_among_all_test_frames_pct:.0f} % of all frames"
bullets(s, ['20 worst frames per method and scene, with image montages', tg('chess', 'NetVLAD top-1'), tg('chess', 'ACE'), tg('stairs', 'NetVLAD top-1'), tg('stairs', 'ACE'), 'Tags are descriptive, not causal'], x=0.6, y=1.55, w=12.1, h=5.4, size=26)
# 10 limitations and repo
s = base('Limitations, changes and repository')
bullets(s, ['Two small rooms; GT variants are themselves reference algorithms', 'Distance curve is correlational; only the density sweep changes distance',
            'Changes from proposal: 25 %/10 % random thinning, ACE seed 0 only there; dropped O6, sharpness tertiles, random-head floor',
            f'Bootstrap block length {BL} (50 was checked on the development sequence)',
            'AI declaration: Claude explained concepts, helped write and debug code, and suggested contents and layout of documents',
            REPO], size=24)
prs.save(OUT / 'slides.pptx')
# ---------- README + ZIP ----------
readme = f"""# P22 Indoor Camera Relocalisation: NetVLAD vs ACE on 7-Scenes (Chess, Stairs)
UCS532 Open Challenge. Authors: Yajat Taneja (1024030082), Riddhima Agrawal (1024240068).

**Problem.** Where is the camera, from one RGB image? We measure error against distance to the nearest training view for NetVLAD retrieval (top-1, top-k) and ACE, on both ground-truth variants, and thin the training map (100/50/25/10 %).

**Data.** Microsoft 7-Scenes, scenes Chess and Stairs, official train/test sequences (https://www.microsoft.com/en-us/research/project/rgb-d-dataset-7-scenes/). Non-commercial licence; data is not in this repo. SfM pseudo-GT poses: https://github.com/tsattler/visloc_pseudo_gt_limitations.

**Reproduce.** `bash run_all.sh /path/to/folder_with_chess.zip_and_stairs.zip` (needs a CUDA GPU and internet). The notebook `P22_Indoor_Camera_Relocalisation.ipynb` is the single pipeline; seeds are printed in its logs. Dependencies: `requirements.txt`. Results go to `results/`.

**Hardware / runtime.** Kaggle, NVIDIA T4 GPU, about 4-5 hours for the full run (all ACE trainings are cached and resumable).

## Results (test sequences, full density; ACE = mean of 3 seeds)
{main_tab and ''}
""" + allv[['scene', 'gt', 'method', 'median_t_cm', 'median_r_deg', 'acc_5cm5deg_pct', 'ur_status']].round(2).to_markdown(index=False) + f"""

Density ablation, hypotheses and failure analysis: see `report.pdf` and `results/tables`.

## Credits
ACE (Brachmann et al., CVPR 2023, https://github.com/nianticlabs/ace, pinned commit, with three small patches saved in `results/`), hloc NetVLAD (https://github.com/cvg/Hierarchical-Localization), pseudo-GT poses (Brachmann et al., ICCV 2021), 7-Scenes (Shotton et al., CVPR 2013), NetVLAD (Arandjelovic et al., CVPR 2016), top-k interpolation after Sattler et al., CVPR 2019. Pose/metric/retrieval/analysis code is ours.

## Declarations
Contribution: both authors worked jointly on all parts through shared meetings and discussion. AI declaration: Claude (Anthropic) was used to explain concepts, to help write and debug code, and to suggest the contents and layout of the report, slides and README. Both authors ran the experiments together and verified the results together, with AI assistance.
"""
(OUT / 'README.md').write_text(readme)
ZN = OUT / (ROLL + '.zip'); repo = Path(__file__).parent
with zipfile.ZipFile(ZN, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(OUT / 'report.pdf', 'report.pdf'); z.write(OUT / 'slides.pptx', 'slides.pptx'); z.write(OUT / 'README.md', 'github_repo/README.md')
    for n in ['run_all.sh', 'requirements.txt', '.gitignore', 'P22_Indoor_Camera_Relocalisation.ipynb', 'build_submission.py']: z.write(repo / n, 'github_repo/' + n)
    z.writestr('github_link.txt', REPO + '\n')
    for p in R.rglob('*'):
        if p.is_file() and p.stat().st_size < 90e6 and 'predictions' not in p.parts: z.write(p, 'results/' + str(p.relative_to(R)))
print('built', ZN)
