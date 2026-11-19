"""Refresh the public Nova Scotia co-op directory without retaining street addresses."""
from datetime import datetime
import json
from pathlib import Path
import re
from urllib.request import urlopen

BASE = 'https://data.novascotia.ca/'
DATA = BASE + 'resource/k29k-n2db.json'
FIELDS = ['registry_id','co_op_name','town','incorporation_year','type','non_profit_n_for_profit_p']
OUTPUT = Path(__file__).resolve().parents[1] / 'web/ns-coops.json'


def edition():
    with urlopen(BASE + 'api/views/k29k-n2db', timeout=60) as source:
        metadata = json.load(source)
    if set(FIELDS) - {c['fieldName'] for c in metadata['columns']}:
        raise ValueError('Review changed co-op fields')
    stamp = re.search(r'as of (\w+ \d{1,2}, \d{4})', metadata['description'])
    if not stamp:
        raise ValueError('Review the published register coverage date')
    rows = []
    while True:
        url = DATA + '?$select=' + ','.join(FIELDS) + '&$order=registry_id&$limit=1000&$offset=' + str(len(rows))
        with urlopen(url, timeout=60) as source:
            batch = json.load(source)
        for item in batch:
            if not item.get('co_op_name') or not str(item.get('registry_id','')).isdigit():
                raise ValueError('Incomplete co-op record')
            rows.append([str(item.get(k,'')).strip() for k in FIELDS])
        if len(batch) < 1000:
            break
    if not rows or len({r[0] for r in rows}) != len(rows):
        raise ValueError('Missing or duplicate records')
    return dict(as_of=datetime.strptime(stamp[1], '%B %d, %Y').date().isoformat(), count=len(rows),
                source=BASE+'d/k29k-n2db', rows=rows)


if __name__ == '__main__':
    data = edition()
    tmp = OUTPUT.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    tmp.replace(OUTPUT)
    print(data['as_of'], data['count'])
