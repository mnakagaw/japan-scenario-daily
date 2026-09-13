"""Public editions and explicitly pinned comparison references."""
import datetime as dt
import hashlib
import json
from pathlib import Path


def route(data):
    if data.get('edition_kind') == 'supplement':
        return 'supplements/' + data['edition_id'] + '/'
    return 'reports/' + data['date'] + '/'


def load_editions(root):
    paths=list((root/'content').glob('????-??-??/data.json'))
    paths+=list((root/'supplements').glob('????-??-??/??????/data.json'))
    records=[]
    for path in paths:
        data=json.loads(path.read_text(encoding='utf-8'))
        if path.parent.parent.parent.name == 'supplements':
            assert data.get('edition_kind')=='supplement','Supplement kind missing'
            assert data['edition_id']==path.parent.relative_to(root/'supplements').as_posix(),'Supplement ID/path mismatch'
            assert data['date']==path.parent.parent.name,'Supplement date mismatch'
        else:
            assert data['date']==path.parent.name,'Report date mismatch'
            assert data.get('edition_kind')!='supplement','Wrong edition directory'
        records.append((path.parent,data))
    return sorted(records,key=lambda pair:(pair[1]['date'],dt.datetime.fromisoformat(pair[1]['prepared_at'])))


def latest_per_day(history):
    selected={}
    for data in history: selected[data['date']]=data
    return list(selected.values())


def reference_data(root,reference):
    if reference is None: return None
    public=reference['path']
    parts=public.split('/')
    assert (len(parts)==3 and parts[0]=='reports' or len(parts)==4 and parts[0]=='supplements') and parts[-1]=='data.json','Invalid comparison reference'
    assert all(part not in ('','..','.') for part in parts) and '\\' not in public,'Unsafe reference'
    source=root/('content' if parts[0]=='reports' else parts[0])/Path(*parts[1:])
    assert source.resolve().is_relative_to(root.resolve()),'Reference outside public repository'
    raw=source.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==reference['sha256'],'Comparison reference changed'
    data=json.loads(raw)
    assert reference['prepared_at']==data['prepared_at'],'Reference edition time mismatch'
    assert public==route(data)+'data.json','Reference route mismatch'
    return data


def comparable(data,previous,scenario):
    if previous is None: return None
    row=next((item for item in previous['scenarios'] if item['id']==scenario['id']),None)
    same_series=data['series_id']==previous['series_id']
    if row and same_series and row['definition_version']==scenario['definition_version']:
        assert row['target']==scenario['target'],'Definition changed without version increment'
    same=row and same_series and all(dt.datetime.fromisoformat(data[k])==dt.datetime.fromisoformat(previous[k]) for k in ['deadline','forecast_start'])
    same=same and row['definition_version']==scenario['definition_version'] and row['target']==scenario['target']
    return row if same else None


def validate_references(records,d,include_same_day=False):
    candidates=[x for _,x in records if dt.datetime.fromisoformat(x['prepared_at'])<dt.datetime.fromisoformat(d['cutoff_at'])]
    fields=[('previous_day_reference',(dt.date.fromisoformat(d['date'])-dt.timedelta(days=1)).isoformat())]
    if include_same_day: fields.append(('same_day_reference',d['date']))
    for field,day in fields:
        assert field in d,'Comparison reference must be explicit'
        choices=[x for x in candidates if x['date']==day]
        expected=max(choices,key=lambda x:dt.datetime.fromisoformat(x['prepared_at'])) if choices else None
        ref=d[field]
        assert (ref is None)==(expected is None),'Missing or unexpected comparison edition'
        if ref: assert ref['path']==route(expected)+'data.json','Comparison must pin the last available edition'


def validate_supplements(root,records,display_chars):
    path=root/'supplement-publications.json'
    ledger=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    additions=[(folder,d) for folder,d in records if d.get('edition_kind')=='supplement']
    assert set(ledger)=={d['edition_id'] for _,d in additions},'Supplement publication inventory mismatch'
    for folder,d in additions:
        assert set(ledger[d['edition_id']])=={'report.md','data.json','variables.json'},'Supplement artifacts incomplete'
        for name,digest in ledger[d['edition_id']].items():
            assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest,'Published supplement changed'
            assert (root/'dist'/route(d)/name).read_bytes()==(folder/name).read_bytes(),'Supplement output differs from source'
        text=(folder/'report.md').read_text(encoding='utf-8')
        assert 4000<=display_chars(text)<=5000,'Supplement report length'
        assert all(marker in text for marker in '①②③④'),'Supplement phases missing'
        assert d['strict_blind'] is False and d['initial'] is False,'Supplement provenance flags'
        for key in ['run_started_at','cutoff_at','github_read_at','numeric_recorded_at','prepared_at','forecast_start','deadline']:
            assert dt.datetime.fromisoformat(d[key]).utcoffset() is not None,'Missing supplement timezone'
        times=[dt.datetime.fromisoformat(d[k]) for k in ['run_started_at','cutoff_at','github_read_at','numeric_recorded_at','prepared_at']]
        assert times==sorted(times),'Supplement phase order invalid'
        assert [s['id'] for s in d['scenarios']]==list('ABCDEFGH'),'Main scenarios must be A-H'
        validate_references(records,d,include_same_day=True)
        same=reference_data(root,d['same_day_reference'])
        previous=reference_data(root,d['previous_day_reference'])
        assert same['date']==d['date'] and dt.datetime.fromisoformat(same['prepared_at'])<dt.datetime.fromisoformat(d['cutoff_at']),'Invalid earlier same-day reference'
        if previous:
            assert (dt.date.fromisoformat(d['date'])-dt.date.fromisoformat(previous['date'])).days==1,'Invalid previous-day reference'
            assert dt.datetime.fromisoformat(previous['prepared_at'])<dt.datetime.fromisoformat(d['cutoff_at']),'Previous edition not available at cutoff'
        for s in d['scenarios']:
            for field in ['p_final','p_web_before_github','p_previous_final','p_same_day_previous_final']:
                value=s[field]
                assert value is None or type(value) in (int,float) and 0<=value<=1,'Invalid probability'
            for source,field in [(same,'p_same_day_previous_final'),(previous,'p_previous_final')]:
                row=comparable(d,source,s)
                assert s[field]==(row['p_final'] if row else None),'Incorrect pinned reference value'
            for source,difference in [('p_web_before_github','github_delta_pp'),('p_same_day_previous_final','same_day_delta_pp'),('p_previous_final','daily_delta_pp')]:
                expected=None if s[source] is None or s['p_final'] is None else round(100*(s['p_final']-s[source]),6)
                assert s[difference]==expected,'Incorrect supplement delta'
    return ledger
