"""Publication integrity checks; deliberately offline and deterministic."""
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import build

ROOT=Path(__file__).resolve().parent
def check(condition,message):
    if not condition: raise AssertionError(message)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

class Document(HTMLParser):
    def __init__(self,text):
        super().__init__(); self.ids=set(); self.links=[]; self.feed(text)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:
            check(attrs['id'] not in self.ids,'Duplicate ID '+attrs['id']); self.ids.add(attrs['id'])
        for key in ['href','src']:
            if key in attrs: self.links.append(attrs[key])

def validate():
    history=[]
    for path in sorted((ROOT/'content').glob('????-??-??/data.json')):
        d=json.loads(path.read_text(encoding='utf-8')); md=(path.parent/'report.md').read_text(encoding='utf-8')
        check(d['date']==path.parent.name,'Date/path mismatch')
        check(d['strict_blind'] is False,'Do not claim strict blind analysis')
        check(all(marker in md for marker in ['①','②','③','④']),'Missing analysis phase')
        chars=build.display_chars(md)
        check(4000<=chars<=5000,f'{d["date"]} report is {chars} visible characters')
        for key in ['cutoff_at','prepared_at','numeric_recorded_at','deadline','forecast_start']:
            check(dt.datetime.fromisoformat(d[key]).utcoffset() is not None,'Timezone missing: '+key)
        check(dt.datetime.fromisoformat(d['forecast_start'])<=dt.datetime.fromisoformat(d['numeric_recorded_at']),'Forecast initialized before start')
        check(len({s['id'] for s in d['scenarios']})==len(d['scenarios']),'Duplicate scenario IDs')
        check(len({n['url'] for n in d['news']})==len(d['news']),'Duplicate source URL; combine coverage')
        check(len({n['id'] for n in d['news']})==len(d['news']),'Duplicate news IDs')
        for n in d['news']:
            check(n['phase'] in [1,2],'Unknown news phase')
            check(n['published_date']<=d['date'],'Future publication date presented as published')
            check(urlsplit(n['url']).scheme=='https','Non-HTTPS source')
            check(set(n['scenarios'])<=set(s['id'] for s in d['scenarios']),'Unknown scenario tag')
        previous=history[-1] if history else None
        consecutive=previous and (dt.date.fromisoformat(d['date'])-dt.date.fromisoformat(previous['date'])).days==1
        for s in d['scenarios']:
            for key in ['p_final','p_previous_final','p_web_before_github']:
                v=s[key]; check(v is None or isinstance(v,(int,float)) and 0<=v<=1,'Probability out of range')
            p=next((r for r in previous['scenarios'] if r['id']==s['id']),None) if previous else None
            same=consecutive and p and p['definition_version']==s['definition_version'] and d['series_id']==previous['series_id'] and dt.datetime.fromisoformat(d['deadline'])==dt.datetime.fromisoformat(previous['deadline']) and dt.datetime.fromisoformat(d['forecast_start'])==dt.datetime.fromisoformat(previous['forecast_start'])
            if p and d['series_id']==previous['series_id'] and p['definition_version']==s['definition_version']:
                check(p['target']==s['target'],'Definition changed without a new version')
            expected_prior=p['p_final'] if same else None
            check(s['p_previous_final']==expected_prior,'Incorrect prior for '+s['id'])
            if d['initial']:
                check(all(s[k] is None for k in ['p_previous_final','p_web_before_github','daily_delta_pp','github_delta_pp']),'Initial values must stay null')
            for left,out in [('p_previous_final','daily_delta_pp'),('p_web_before_github','github_delta_pp')]:
                expected=round((s['p_final']-s[left])*100,6) if s['p_final'] is not None and s[left] is not None else None
                actual=s[out]
                check(actual is None if expected is None else actual is not None and abs(actual-expected)<1e-5,'Wrong delta '+s['id']+' '+out)
        history.append(d)
    check(bool(history),'No reports')
    # Scan only publishable content and output. Internal local receipts are not inputs.
    forbidden=[r'(?<![A-Za-z])(?i:[A-Z]):[\\/]',r'(?i)\\\\[a-z0-9.-]+\\',r'gh[pousr]_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{20,}',r'-----BEGIN [A-Z ]*PRIVATE KEY',r'(?i)private github',r'(?i)\.codex[\\/]',r'(?i)github\.com/[^/\s]+/[^/\s]*(?:osint|research)[^/\s]*']
    for folder in ['content','dist']:
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and path.suffix in ['.md','.json','.html','.js','.css','.xml']:
                text=path.read_text(encoding='utf-8')
                check(not any(re.search(p,text) for p in forbidden),'Nonpublic information in '+str(path.relative_to(ROOT)))
    documents={p:Document(p.read_text(encoding='utf-8')) for p in (ROOT/'dist').rglob('*.html')}
    for path,doc in documents.items():
        for raw in doc.links:
            link=urlsplit(raw)
            if link.scheme or link.netloc: continue
            if link.path:
                check(link.path.startswith(build.BASE+'/'),'Link escapes Pages base: '+raw)
                target=ROOT/'dist'/unquote(link.path[len(build.BASE)+1:])
                if target.is_dir(): target=target/'index.html'
                check(target.is_file(),'Broken local reference: '+raw)
            else: target=path
            if link.fragment and target in documents:
                check(unquote(link.fragment) in documents[target].ids,'Broken fragment: '+raw)
    for file in ['feed.xml','sitemap.xml']: ET.parse(ROOT/'dist'/file)
    ledger=json.loads((ROOT/'publications.json').read_text(encoding='utf-8'))
    check(set(ledger)=={d['date'] for d in history},'Missing publication record')
    for date,files in ledger.items():
        for name,digest in files.items():
            check(name in ['report.md','data.json'],'Unexpected publication artifact')
            check(sha(ROOT/'content'/date/name)==digest,'Published artifact changed: '+date+'/'+name)
    # In CI, compare the existing publication ledger with the parent commit.
    if '--check-history' in sys.argv:
        prior=subprocess.run(['git','show','HEAD^:publications.json'],cwd=ROOT,text=True,capture_output=True,encoding='utf-8')
        if prior.returncode==0:
            old=json.loads(prior.stdout)
            check(all(ledger.get(date)==files for date,files in old.items()),'Published baseline overwritten; append a correction instead')
    check(build.deadline_label({'deadline':'2026-11-04T13:59:59+09:00'})=='2026年11月3日 23:59 米東部時間','Timezone conversion')
    check(build.date_label('2026-09-13T02:36:00+00:00')=='09/13 11:36 JST','JST conversion')
    print(f'PASS: {len(history)} report(s), {len(documents)} HTML pages, local links, anchors, privacy, probability deltas, dates, XML, immutable publication hashes.')
    print('Report character counts: '+', '.join(f'{d["date"]} = {build.display_chars((ROOT/"content"/d["date"]/"report.md").read_text(encoding="utf-8"))}' for d in history))

if __name__=='__main__': validate()
