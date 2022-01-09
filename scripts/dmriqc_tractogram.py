#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import shutil

from dipy.io.utils import is_header_compatible
import numpy as np

from dmriqcpy.io.report import Report
from dmriqcpy.io.utils import (add_online_arg, add_overwrite_arg,
                               assert_inputs_exist, assert_outputs_exist)
from dmriqcpy.analysis.stats import stats_tractogram
from dmriqcpy.viz.graph import graph_tractogram
from dmriqcpy.viz.screenshot import screenshot_tracking
from dmriqcpy.viz.utils import analyse_qa, dataframe_to_html


DESCRIPTION = """
Compute the tractogram report in HTML format.
"""


def _build_arg_parser():
    p = argparse.ArgumentParser(description=DESCRIPTION,
                                formatter_class=argparse.RawTextHelpFormatter)

    p.add_argument('output_report',
                   help='HTML report')

    p.add_argument('--tractograms', nargs='+',
                   help='Tractograms in format supported by Nibabel')

    p.add_argument('--t1s', nargs='+',
                   help='T1 images in Nifti format')

    p.add_argument('--bundle', action='store_true',
                   help='If bundle is set it will use the barycentre of '
                        'the bundle as origin for the T1 image.')

    add_online_arg(p)
    add_overwrite_arg(p)

    return p


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    if not len(args.tractograms) == len(args.t1s):
        parser.error("Not the same number of images in input.")

    all_images = np.concatenate([args.tractograms, args.t1s])
    assert_inputs_exist(parser, all_images)
    assert_outputs_exist(parser, args, [args.output_report, "data", "libs"])

    for idx, trk in enumerate(args.tractograms):
        if not is_header_compatible(trk, args.t1s[idx]):
            parser.error('Inputs {} do not have'
                         ' a compatible header.'.format(trk, vargs.t1s[idx]))

    if os.path.exists("data"):
        shutil.rmtree("data")
    os.makedirs("data")

    if os.path.exists("libs"):
        shutil.rmtree("libs")

    name = "Tracking"
    columns = ["Nb streamlines"]

    warning_dict = {}
    summary, stats, idx_wo_streamlines = stats_tractogram(columns, args.tractograms)
    warning_dict[name] = analyse_qa(summary, stats, ["Nb streamlines"])
    warning_list = np.concatenate([filenames for filenames in warning_dict[name].values()])
    warning_dict[name]['nb_warnings'] = len(np.unique(warning_list))

    graphs = []
    graph = graph_tractogram("Tracking", columns, summary, args.online)
    graphs.append(graph)

    summary_dict = {}
    stats_html = dataframe_to_html(stats)
    summary_dict[name] = stats_html

    metrics_dict = {}
    subjects_dict = {}

    valid_trks = []
    valid_t1s = []
    for j, i in enumerate(args.tractograms):
        if j not in idx_wo_streamlines:
            valid_trks.append(i)
            valid_t1s.append(args.t1s[j])

    for subj_metric, t1 in zip(valid_trks, valid_t1s):
        screenshot_path = screenshot_tracking(subj_metric, t1,
                                              args.bundle, "data")
        summary_html = dataframe_to_html(summary.loc[subj_metric])
        subjects_dict[subj_metric] = {}
        subjects_dict[subj_metric]['screenshot'] = screenshot_path
        subjects_dict[subj_metric]['stats'] = summary_html
    metrics_dict[name] = subjects_dict

    nb_subjects = len(args.tractograms)
    report = Report(args.output_report)
    report.generate(title="Quality Assurance tractograms",
                    nb_subjects=nb_subjects, summary_dict=summary_dict,
                    graph_array=graphs, metrics_dict=metrics_dict,
                    warning_dict=warning_dict,
                    online=args.online)


if __name__ == '__main__':
    main()
