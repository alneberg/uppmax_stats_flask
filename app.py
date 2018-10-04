# -*- coding: utf-8 -*-
from flask import Flask, render_template
import pandas as pd
import re
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


@app.route("/")
def hello():
    df = _parse_data('data/sarek_run_1/finishedjobinfo.ssv')
    data = df[['jobid', 'maxmemory_in_GiB']].to_json(orient='values')
    return render_template('index.html', data=data)
