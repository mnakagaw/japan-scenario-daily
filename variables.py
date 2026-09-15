"""Observation panel: public measurements and source-attributed states, not forecasts."""
import datetime as dt
import html
import json
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from editions import load_editions, route as edition_route

def esc(value): return html.escape(str(value),quote=True)
def number(value): return f'{value:g}' if isinstance(value,(int,float)) else str(value)

def render_food_security_guide(root):
    guide=json.loads((root/'food-security-monitoring.json').read_text(encoding='utf-8'))
    topics=''.join(f'<li><strong>{esc(t["label"])}</strong><span>{esc(t["detail"])}</span></li>' for t in guide['topics'])
    sources='・'.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["label"])} ↗<span class="sr-only">（新しいタブ）</span></a>' for s in guide['sources'])
    return f'''<section class="method-prose bottleneck-guide" id="food-security-guide" aria-labelledby="food-security-title"><h3 id="food-security-title">{esc(guide['title'])}</h3><p>{esc(guide['scope_note'])}</p><ul class="bottleneck-list">{topics}</ul><p>{esc(guide['comparison_note'])}</p><p>{esc(guide['workflow_note'])}</p><details><summary>食料・肥料の一次情報の入口</summary><p>{sources}</p><p>入口の一覧に加え、各国の農業・貿易当局、気象機関、港湾・船社等の原文を確認します。取得できた範囲と、未取得の範囲を区別します。</p></details></section>'''

def render_bottleneck_guide(root):
    scope=json.loads((root/'bottlenecks.json').read_text(encoding='utf-8'))
    locations=''.join(f'<li><strong>{esc(region["region"])}</strong><span>{esc("、".join(region["locations"]))}</span></li>' for region in scope['regions'])
    sources='・'.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["label"])} ↗<span class="sr-only">（新しいタブ）</span></a>' for s in scope['sources'])
    return f'''<section class="method-prose bottleneck-guide" id="bottleneck-guide" aria-labelledby="bottleneck-title"><h3 id="bottleneck-title">確認対象の主な海峡・運河など</h3><p>{esc(scope['scope_note'])}</p><ul class="bottleneck-list">{locations}</ul><p><strong>掲載する動き：</strong>閉鎖・攻撃・通航制限、事故、渇水・荒天・海氷、混雑・ストライキ、迂回・運賃・保険条件の変化、復旧・再開。輸送量・日数・費用・供給、日本やA〜Hの判断に関わる重要事項を選びます。</p><p>重要なニュースがない地点は日報への掲載を省きます。重大な制約の継続は、継続を確認した日と理由を添えて掲載する場合があります。掲載なしは「異常なし」「全地点確認済み」という意味ではなく、重要な確認不足は留保として示します。</p><details><summary>確認に使う公開情報の入口</summary><p>{sources}</p><p>世界全体の障害情報から発見し、関係当局・運河庁・港湾当局・船社の発表と実通航・運航情報で確認します。このリストは観測範囲を示し、当日の確認完了一覧ではありません。</p></details></section>'''


def load_variables(root):
    records={}
    for folder,edition in load_editions(root):
        path=folder/'variables.json'
        if not path.exists(): continue
        data=json.loads(path.read_text(encoding='utf-8'))
        assert data['date']==edition['date'],'Variable record date mismatch'
        assert dt.datetime.fromisoformat(data['recorded_at']).utcoffset() is not None,'Variable timestamp needs timezone'
        ids=set()
        for v in data['items']:
            assert v['id'] not in ids,'Duplicate variable ID'; ids.add(v['id'])
            assert v['kind'] and v['observed'] and v['published'] and v['change_note']
            assert v['previous_value'] is None or isinstance(v['previous_value'],(int,float))
            assert v['sources'] and all(urlsplit(s['url']).scheme=='https' for s in v['sources'])
            assert all(key in v for key in ['label','group','value','unit','note','implication','watch','delta_unit'])
            assert isinstance(v.get('show_on_page',True),bool),'show_on_page must be a boolean'
            if 'show_on_page' in v: assert v.get('selection_reason','').strip(),'Explain the publication selection'
            if v['previous_value'] is not None: assert isinstance(v['value'],(int,float)),'Comparison needs numeric values'
        records[edition_route(edition)]=data
    return records

def render_variables(d,records,url):
    record=records.get(edition_route(d))
    if record is None:
        return '<section id="variables"><h2>世界の横断変数</h2><p class="empty-state">この号の横断変数は未収録です。未収録は、平常・変化なしを意味しません。</p></section>'
    visible=[v for v in record['items'] if v.get('show_on_page',True)]
    groups={}
    for v in visible: groups.setdefault(v['group'],[]).append(v)
    rendered=[]
    for group,items in groups.items():
        cards=[]
        for v in items:
            numeric=isinstance(v['value'],(int,float))
            value='未取得' if v['value'] is None else number(v['value'])
            if v['previous_value'] is not None:
                difference=round(v['value']-v['previous_value'],6)
                direction='up' if difference>0 else 'down' if difference<0 else 'flat'
                arrow='▲' if difference>0 else '▼' if difference<0 else '→'
                change=f'<span class="change {direction}">{arrow} {difference:+g} {esc(v["delta_unit"])}</span>'
                prior=f'比較元 {number(v["previous_value"])} {esc(v["unit"])}'
            else:
                change='<span class="change unavailable">— 数値差は未算出</span>'
                prior='比較元の数値は未収録'
            links=''.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["label"])} ↗<span class="sr-only">（新しいタブ）</span></a>' for s in v['sources'])
            cards.append(f'''<article class="variable-card" id="variable-{esc(v['id'])}"><div class="variable-meta"><span>{esc(v['kind'])}</span><span>公表 {esc(v['published'])}</span></div><h4>{esc(v['label'])}</h4><div class="variable-reading"><strong class="variable-value {'numeric' if numeric else 'state'}">{esc(value)}</strong><span>{esc(v['unit'])}</span></div><p class="variable-date">対象：{esc(v['observed'])}</p><div class="variable-comparison">{change}<span>{prior}</span></div><p class="variable-change-note">{esc(v['change_note'])}</p><p>{esc(v['note'])}</p><details><summary>日本への影響・次に見る変化</summary><p>{esc(v['implication'])}</p><p><strong>次の観測：</strong>{esc(v['watch'])}</p></details><div class="variable-sources">{links}</div></article>''')
        rendered.append(f'<div class="variable-group"><h3>{esc(group)}</h3><div class="variable-grid">{"".join(cards)}</div></div>')
    when=dt.datetime.fromisoformat(record['recorded_at']).astimezone(ZoneInfo('Asia/Tokyo')).strftime('%m/%d %H:%M JST')
    download=url(edition_route(d)+'variables.json')
    coverage=f'<p class="note">{esc(record["coverage_note"])}</p>' if record.get('coverage_note') else ''
    empty='<p class="empty-state">この号に掲載する横断変数はありません。掲載がないことは、全地点の確認完了や異常なしを意味しません。</p>' if not visible else ''
    return f'''<section id="variables" class="world-variables"><span id="cross-risk" class="anchor-alias"></span><div class="section-heading"><div><p class="eyebrow">GLOBAL VARIABLES</p><h2>世界の横断変数と、その変化</h2></div><a class="small" href="{url('method/')}#variable-guide">主シナリオとの違い →</a></div><p class="section-lead">海峡・運河、供給、エネルギー、物価・金融など、A〜Hに共通して影響し得る条件を追います。数値で測る項目と、通航・制度などの状態を確認する項目を分けて表示します。</p><p class="small">海上物流は世界の主要ボトルネックを確認対象とし、重要なニュース・変化のある地点を掲載します。掲載のない地点を異常なしとは扱いません。<a href="{url('method/')}#bottleneck-guide">確認対象と掲載基準 →</a></p><p class="small muted">掲載 {len(visible)}項目 ／ 記録 {when} ／ <a href="{download}" download>横断変数のデータを保存</a></p><p class="note">{esc(record['basis_note'])} 各変数の対象日と公表日は異なります。比較は資料に記載された前回値などとの比較で、すべてが前日比ではありません。色や数値差は日本への利害を自動判定するものではありません。</p>{coverage}{''.join(rendered)}{empty}</section>'''
