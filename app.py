# -*- coding: utf-8 -*-
from flask import Flask, render_template
import pandas as pd
import re
import glob
import os
app = Flask(__name__)


def _parse_data(file_path):
    parse_regex = re.compile('(.*)=(.*)')
    df = pd.read_table(file_path, sep=' ', header=None)
    result_d = {}
    for ix, row in df.iterrows():
        row_data = {}
        for column, value in row.iteritems():
            match = parse_regex.search(value)
            if match:
                key = match.groups()[0]
                if key == 'maxmemory_in_GiB':
                    value = float(match.groups()[1])
                else:
                    value = match.groups()[1]
                row_data[key] = value
        result_d[ix] = row_data
    return pd.DataFrame.from_dict(result_d, orient='index')


def parse_time(x):
    if '-' in x:
        dd, x = x.split('-')
    else:
        dd = "0"

    hh, mm, ss = x.split(':')
    dd, hh, mm, ss = int(dd), int(hh), int(mm), int(ss)
    return dd*24*60*60 + hh*60*60 + mm*60 + ss


def fill_columns(original_columns):
    """Nr of columns vary with the nr of processors used"""
    nr_cols = len(original_columns)
    cols = ['TIME', 'GB_LIMIT', 'GB_USED', 'GB_MAX_USED',
            'GB_SWAP_USED', 'PAGE_IN', 'PAGE_OUT']

    nr_procs = nr_cols - len(cols)
    proc_columns = ['PROC{}'.format(i+1) for i in range(nr_procs)]
    cols += proc_columns
    return cols, proc_columns


def parse_detailed_jobinfo(dir_path):
    result_d = {}
    for file in glob.glob(dir_path + '/*.stats'):
        jobid = os.path.basename(file).split('_')[1].split('.')[0]

        data = pd.read_table(file, delim_whitespace=True, skiprows=1,
                             header=None, index_col=0)
        data.columns, proc_columns = fill_columns(data.columns)
        avg_cpu = data[proc_columns].mean().sum()
        std_cpu = data[proc_columns].sum(axis=1).std()
        max_cpu = data[proc_columns].sum(axis=1).max()
        result_d[jobid] = {'avg_cpu': avg_cpu, 'std_cpu': std_cpu,
                           'max_cpu': max_cpu}

    return pd.DataFrame.from_dict(result_d, orient='index')


@app.route("/maxmemory")
def maxmemory():
    df = _parse_data('data/sarek_run_1/finishedjobinfo.ssv')
    data = df[['jobid', 'maxmemory_in_GiB']].to_json(orient='values')
    return render_template('maxmemory.html', data=data)


@app.route("/")
def bubble():
    cpu_stats_df = parse_detailed_jobinfo('data/sarek_run_1/extended_info')
    df = _parse_data('data/sarek_run_1/finishedjobinfo.ssv')
    # data = df[['jobid', 'maxmemory_in_GiB']].to_json(orient='values')
    data_df = df[['jobid', 'maxmemory_in_GiB']].copy()
    data_df.rename(columns={'maxmemory_in_GiB': 'y'}, inplace=True)
    data_df['x'] = df['procs'].astype(float) * 16.0
    data_df['z'] = df['runtime'].apply(parse_time)

    mem_bubble_data = data_df.to_json(orient='records')

    data_df.index = data_df['jobid']
    data_df['x'] = data_df['y']
    data_df['y'] = cpu_stats_df['avg_cpu']

    cpu_mem_bubble_data = data_df.to_json(orient='records')
    df.index = df['jobid']
    data_df['y'] = cpu_stats_df['avg_cpu'].divide(df['procs'].astype(float))
    data_df['x'] = 100*data_df['x'].divide(df['procs'].astype(float)*16)
    data_df['jobname'] = df['jobname']

    cpu_mem_rel_bubble_data = data_df.to_json(orient='records')
    return render_template('bubble.html', mem_bubble_data=mem_bubble_data,
                           cpu_mem_bubble_data=cpu_mem_bubble_data,
                           cpu_mem_rel_bubble_data=cpu_mem_rel_bubble_data)
