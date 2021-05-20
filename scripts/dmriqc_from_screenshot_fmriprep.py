#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import glob
import numpy as np
import os
import pandas as pd
import shutil

from dmriqcpy.io.report import Report
from dmriqcpy.io.utils import add_overwrite_arg, assert_inputs_exist,\
                              assert_outputs_exist
from dmriqcpy.viz.graph import graph_pandas
from dmriqcpy.viz.utils import analyse_qa, dataframe_to_html
DESCRIPTION = """
Compute the screenshot report in HTML format for fmriPrep.
"""


def _build_arg_parser():
    p = argparse.ArgumentParser(description=DESCRIPTION,
                                formatter_class=argparse.RawTextHelpFormatter)

    p.add_argument('output_report',
                   help='HTML report')

    p.add_argument('in_fmriprep',
                   help='Output fmriPrep.')

    p.add_argument('--in_figures', nargs='+',
                   help='Name of the extension in fmriprep.')

    p.add_argument('--in_metrics', nargs='+',
                   help='Name of the metric in _desc-confounds_timeseries.tsv.')

    p.add_argument('--sym_link', action="store_true",
                   help='Use symlink instead of copy')

    add_overwrite_arg(p)

    return p

def split_filename_fmriprep(in_path):
    subject = in_path.split(os.path.sep)[1]
    session = in_path.split(os.path.sep)[-1].split('_')[1]
    task = in_path.split(os.path.sep)[-1].split('_')[2]
    run = in_path.split(os.path.sep)[-1].split('_')[3]

    if 'run' not in run:
        run = None

    return subject, session, task, run

def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    assert_inputs_exist(parser, args.in_fmriprep, are_directories=True)
    assert_outputs_exist(parser, args, [args.output_report, "data", "libs"])

    list_subjects = [name for name in os.listdir(args.in_fmriprep) if os.path.isdir(os.path.join(args.in_fmriprep,name)) and 'sub' in name]
    nb_subjects = len(list_subjects)

    if os.path.exists('data'):
        shutil.rmtree("data")
    os.makedirs("data")

    if os.path.exists("libs"):
        shutil.rmtree("libs")


    figures_dict = {}
    if args.in_figures:
        path_files = os.path.join(args.in_fmriprep, 'sub-*', 'figures', '*')
        for curr_metric in args.in_figures:
            figures_dict[curr_metric] = {}
            subject_dict = {}
            curr_files = glob.glob(path_files + curr_metric + '*.svg')
            for curr_file in curr_files:
                curr_subject, curr_session, curr_task, curr_run = split_filename_fmriprep(curr_file)
                basename = os.path.basename(curr_file)
                shutil.copyfile(curr_file, os.path.join('data', basename))
                name = '_'.join(filter(None, [curr_subject,
                                              curr_session,
                                              curr_task,
                                              curr_run]))
                subject_dict[name] = {'screenshot': os.path.join('data', basename)}
            figures_dict[curr_metric] = subject_dict

    if args.in_metrics:
        path_files = os.path.join(args.in_fmriprep,
                                  'sub-*',
                                  'ses*',
                                  'func','*')
        curr_files = glob.glob(path_files + 'desc-confounds_timeseries.tsv')

        subjects_dict = {}
        warning_dict = {}
        names = []
        all_values = []
        for curr_file in curr_files:
            curr_subject, curr_session, curr_task, curr_run = split_filename_fmriprep(curr_file)
            name = '_'.join(filter(None, [curr_subject,
                                          curr_session,
                                          curr_task,
                                          curr_run]))
            names.append(name)
            curr_panda = pd.read_csv(curr_file, sep='\t')
            sub_values = []
            for curr_metric in args.in_metrics:
                sub_values = []
                if curr_metric not in subjects_dict:
                    subjects_dict[curr_metric] = []

                sub_values.append(np.max(curr_panda[curr_metric]))
                sub_values.append(np.min(curr_panda[curr_metric]))
                sub_values.append(np.mean(curr_panda[curr_metric]))

                subjects_dict[curr_metric].append(sub_values)

        summary_dict = {}
        warning_dict = {}
        graphs = []
        for curr_metric in args.in_metrics:
            column_names = []
            column_names.append('Max ' + curr_metric)
            column_names.append('Min ' + curr_metric)
            column_names.append('Mean ' + curr_metric)
            stats_per_subjects = pd.DataFrame(subjects_dict[curr_metric],
                                              index=[names],
                                              columns=column_names)
            summary = pd.DataFrame([stats_per_subjects.mean(),
                                    stats_per_subjects.std(),
                                    stats_per_subjects.min(),
                                    stats_per_subjects.max()],
                                    index=['mean', 'std', 'min', 'max'],
                                    columns=column_names)

            stats_html = dataframe_to_html(stats_per_subjects)
            summary_dict[curr_metric] = stats_html

            warning_dict[curr_metric] = analyse_qa(stats_per_subjects, summary, column_names)
            warning_list = np.concatenate(
                        [filenames for filenames in warning_dict[curr_metric].values()])
            warning_dict[curr_metric]['nb_warnings'] = len(np.unique(warning_list))


            graph = graph_pandas(curr_metric, column_names,
                                          stats_per_subjects)
            graphs.append(graph)

            flat_graphs = [item for sublist in graphs for item in sublist]

    report = Report(args.output_report)
    report.generate(title="Quality Assurance fmriPrep",
                    nb_subjects=nb_subjects, metrics_dict=figures_dict,
                    summary_dict=summary_dict,
                    warning_dict=warning_dict,
                    graph_array=flat_graphs)

if __name__ == '__main__':
    main()
