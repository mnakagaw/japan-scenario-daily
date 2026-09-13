"""Dependency-free static publisher. Reads only this repository's content/."""
from __future__ import annotations
import argparse, datetime as dt, html, json, re, shutil
from pathlib import Path
from email.utils import format_datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from variables import load_variables, render_variables, render_bottleneck_guide

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dist'
SITE = 'https://mnakagaw.github.io/japan-scenario-daily'
BASE = '/japan-scenario-daily'
TITLE = '米中・中間選挙 シナリオ日報'
NEWS_LABELS = {}
WORLD_VARIABLES = {}

def e(value): return html.escape(str(value), quote=True)
def url(path=''): return BASE + '/' + path.lstrip('/')
def pct(value): return '未設定' if value is None else f'{value * 100:.0f}%'
def band(value): return 'undefined' if value is None else 'high' if value >= .6 else 'medium' if value >= .3 else 'low'
def delta(value, missing='初回'):
    if value is None: return f'<span class="change unavailable">— {e(missing)}</span>'
    kind, arrow = ('up','▲') if value > 0 else ('down','▼') if value < 0 else ('flat','→')
    return f'<span class="change {kind}">{arrow} {value:+g} pt</span>' if value else '<span class="change flat">→ 0 pt</span>'

def inline(text):
    text = e(text)
    def link(m):
        label, href = m.groups()
        if urlparse(html.unescape(href)).scheme != 'https': raise ValueError('Only HTTPS article links allowed')
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{label}<span class="sr-only">（外部リンク・新しいタブ）</span></a>'
    text = re.sub(r'\[([^]]+)\]\((https://[^)]+)\)', link, text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text

def markdown(text):
    """Render the small, deliberately restricted report format; never raw HTML."""
    blocks = re.split(r'\n\s*\n', text.strip())
    result = []
    for block in blocks:
        lines = block.splitlines()
        if lines[0].startswith('|'):
            rows = [line.strip().strip('|').split('|') for line in lines]
            header = ''.join(f'<th scope="col">{inline(x.strip())}</th>' for x in rows[0])
            body = ''.join('<tr>'+''.join(f'<td>{inline(x.strip())}</td>' for x in row)+'</tr>' for row in rows[2:])
            result.append(f'<div class="table-scroll"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>')
        elif all(re.match(r'^(- |\d+\. )', line) for line in lines):
            ordered = not lines[0].startswith('- ')
            tag = 'ol' if ordered else 'ul'
            start = f' start="{re.match(r"\d+",lines[0])[0]}"' if ordered else ''
            result.append(f'<{tag}{start}>'+''.join('<li>'+inline(re.sub(r'^(- |\d+\. )','',line))+'</li>' for line in lines)+f'</{tag}>')
        elif re.fullmatch(r'\*\*.+\*\*',block):
            title = block[2:-2]; phase = next((str(i) for i,c in enumerate('①②③④',1) if title.startswith(c)),None)
            anchor = f' id="phase-{phase}"' if phase else ''
            result.append(f'<h2{anchor}>{e(title)}</h2>')
        else: result.append('<p>'+inline(block)+'</p>')
    return '\n'.join(result)

def page(title, content, path='', active='today', data=None, description=None):
    nav = [('today','今日の日報',''),('archive','アーカイブ','archive/'),('compare','日付で比較','compare/'),('method','読み方・シナリオ・手法','method/')]
    navhtml = ''.join(f'<a href="{url(p)}"'+(' aria-current="page"' if key==active else '')+f'>{label}</a>' for key,label,p in nav)
    payload = '' if data is None else '<script id="page-data" type="application/json">'+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+'</script>'
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | {TITLE}</title><meta name="description" content="{e(description or '米中関係と米中間選挙を、日本への影響から読む日報。公開ニュース、シナリオの主観確率、参照研究との比較を日付ごとに記録。')}">
<link rel="canonical" href="{SITE}/{path}"><meta name="theme-color" content="#142b38"><link rel="icon" href="{url('assets/favicon.svg')}" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="日報 RSS" href="{url('feed.xml')}"><link rel="stylesheet" href="{url('assets/style.css')}"><script src="{url('assets/app.js')}" defer></script></head>
<body><a class="skip" href="#main">本文へ移動</a><header class="masthead"><div class="shell header-inner"><a class="brand" href="{url()}"><span class="brand-mark" aria-hidden="true">↗</span><span>米中・中間選挙<span class="brand-sub">シナリオ日報 <span lang="en">/ DAILY OBSERVATORY</span></span></span></a><nav aria-label="メイン">{navhtml}</nav><a class="rss" href="{url('feed.xml')}">RSS ↗</a></div></header>
<main id="main" class="shell">{content}</main>
<footer class="footer"><div class="shell"><strong>{TITLE}</strong><p>公開資料と参照研究を読み、日本への影響を考える。事実・解釈・予測を分け、公開後の訂正を記録します。</p><div class="footer-links"><a href="{url('method/')}">確率と判定条件</a><a href="{url('archive/')}">過去の日報</a><a href="{url('feed.xml')}">RSS</a><a href="https://github.com/mnakagaw/japan-scenario-daily">公開リポジトリ ↗</a><a href="#main">ページ上部 ↑</a></div></div></footer>{payload}</body></html>'''

def section_title(kicker,title,note=''):
    return f'<div class="section-heading"><div><p class="eyebrow">{e(kicker)}</p><h2>{e(title)}</h2></div>'+ (f'<p class="section-note">{e(note)}</p>' if note else '')+'</div>'

def date_label(value): return dt.datetime.fromisoformat(value).astimezone(ZoneInfo('Asia/Tokyo')).strftime('%m/%d %H:%M JST')

def deadline_label(d):
    date=dt.datetime.fromisoformat(d['deadline']).astimezone(ZoneInfo('America/New_York'))
    return f'{date.year}年{date.month}月{date.day}日 {date:%H:%M} 米東部時間'

def display_chars(text):
    text=re.sub(r'\[([^]]+)\]\([^)]+\)',r'\1',text)
    text=re.sub(r'^\|[-: |]+\|\s*$','',text,flags=re.M)
    text=re.sub(r'(?m)^\d+\.\s*','',text)
    return len(re.sub(r'[\s*`#|\-]','',text))

def spark(history, s):
    points=[]; target=history[-1]
    for d in history:
        row=next((r for r in d['scenarios'] if r['id']==s['id']),None)
        comparable=row and row['definition_version']==s['definition_version'] and d['series_id']==target['series_id'] and d['deadline']==target['deadline'] and d['forecast_start']==target['forecast_start']
        points.append((d['date'],row['p_final'] if comparable else None))
    valid=[(date,p) for date,p in points if p is not None]
    if not valid: return '<span class="history-empty">— 記録なし</span>'
    if len(valid)<2: return '<span class="history-empty">● 1回の記録</span>'
    # Only actual observations; do not create intervening dates or pre-baseline values.
    start=dt.date.fromisoformat(points[0][0]); end=dt.date.fromisoformat(points[-1][0]); days=max(1,(end-start).days)
    segments=[]; segment=[]; circles=[]; previous_date=None
    for date,p in points:
        day=dt.date.fromisoformat(date)
        if p is None or (previous_date and (day-previous_date).days!=1):
            if segment: segments.append(segment); segment=[]
        if p is not None:
            x=5+(day-start).days*80/days; y=32-p*28
            segment.append(f'{x:.1f},{y:.1f}'); circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="currentColor"/>')
        previous_date=day
    if segment: segments.append(segment)
    lines=''.join(f'<polyline points="{" ".join(seg)}" fill="none" stroke="currentColor" stroke-width="2"/>' for seg in segments if len(seg)>1)
    label='、'.join(f'{date} {pct(p)}' for date,p in points)
    return f'<svg class="spark" viewBox="0 0 90 38" role="img" aria-label="{e(label)}">{lines}{"".join(circles)}</svg>'

def scenario_table(d,history,items=None,rows_id='scenario-rows'):
    rows=[]
    for s in (d['scenarios'] if items is None else items):
        value=s['p_final']; width=0 if value is None else value*100
        rows.append(f'''<tr data-scenario="{s['id']}" data-probability="{width if value is not None else -1}"><th scope="row"><a class="scenario-link" href="{url('reports/'+d['date']+'/scenarios/'+s['id'].lower()+'/')}"><span class="scenario-id">{s['id']}</span><span>{e(s['label'])}<small>{e(s['reason'])}</small></span><span class="row-arrow" aria-hidden="true">↗</span></a></th><td><span class="probability {band(value)}">{pct(value)}</span><span class="bar-track" aria-hidden="true"><span class="bar {band(value)}" style="width:{width}%"></span></span></td><td>{delta(s['daily_delta_pp'],'未定義' if value is None else '初回' if d['initial'] else '比較不可')}</td><td><span class="confidence">{e(s['evidence_confidence'])}</span></td><td>{spark(history,s)}</td></tr>''')
    return '<div class="table-scroll scenario-scroll"><table class="scenario-table"><caption class="sr-only">最終主観確率、前日最終との差、根拠の確度、実際の記録推移</caption><thead><tr><th scope="col">判定対象・判断の理由</th><th scope="col">最終主観確率</th><th scope="col">前日最終比</th><th scope="col">根拠の確度</th><th scope="col">記録の推移</th></tr></thead><tbody id="'+e(rows_id)+'">'+''.join(rows)+'</tbody></table></div>'

def observation_label(identifier):
    return '旧I・中東物流の参考見通し' if identifier=='I' else '予備枠 J' if identifier=='J' else 'シナリオ '+identifier

def reserve_note(d):
    item=next((s for s in d['scenarios'] if s['id']=='J'),None)
    if item is None: return ''
    link=url('reports/'+d['date']+'/scenarios/j/')
    return f'<aside class="reserve-note"><strong>予備枠 J：{e(item["label"])}</strong><span>{e(item["target"])}</span><a href="{link}">説明を見る →</a></aside>'

def news_card(n, date=None):
    prefix='reports/'+date+'/' if date else ''
    countries=n.get('countries') or NEWS_LABELS.get(date,{}).get(n['id'],[])
    country_tags='<div class="news-countries"><span class="country-caption">国・地域</span>'+''.join(f'<span class="country-tag">{e(country)}</span>' for country in countries)+'</div>'
    tags=''
    for s in n['scenarios']:
        target=url(prefix)+'#variables' if s=='I' else url(prefix+'scenarios/'+s.lower()+'/')
        label='世界の横断変数' if s=='I' else observation_label(s)
        tags+=f'<a class="tag" href="{target}" aria-label="{label}の詳細">{"横断" if s=="I" else s}</a>'
    return f'''<article class="news-item" id="{e(n['id'])}" data-category="{e(n['category'])}" data-status="{e(n['status'])}" data-scenarios="{''.join(n['scenarios'])}"><div class="news-meta"><span class="status">{e(n['status'])}</span><span>{e(n['category'])}</span><span>公表・更新 {e(n['published_date'])}</span></div>{country_tags}<h3>{e(n['title'])}</h3><p>{e(n['summary'])}</p><div class="news-bottom"><span class="event">発生・対象：{e(n['event'])}</span><span class="tags">{tags}</span><a class="source" href="{e(n['url'])}" target="_blank" rel="noopener noreferrer">{e(n['source'])} ↗<span class="sr-only">（新しいタブ）</span></a></div></article>'''

def report_dashboard(d,history,md,path=''):
    date=d['date']; summaries=''.join(f'<li>{e(x)}</li>' for x in d['summary'])
    highlights=''
    for h in d['highlights']:
        target=url('reports/'+d['date']+'/')+'#variables' if h['scenario']=='I' else url('reports/'+d['date']+'/scenarios/'+h['scenario'].lower()+'/')
        label='世界の横断変数' if h['scenario']=='I' else observation_label(h['scenario'])
        highlights+=f'<a class="highlight" href="{target}"><span class="eyebrow">{e(h["label"])}</span><p>{e(h["text"])}</p><span>{label} <span aria-hidden="true">↗</span></span></a>'
    cats=sorted({n['category'] for n in d['news']}); categories=''.join(f'<option>{e(c)}</option>' for c in cats)
    select_s=''.join(f'<option value="{s["id"]}">{"世界の横断変数" if s["id"]=="I" else observation_label(s["id"])+" "+e(s["label"])}</option>' for s in d['scenarios'] if s['p_final'] is not None)
    news_scope=f'①の{sum(n["phase"]==1 for n in d["news"])}件＋②で追加確認した{sum(n["phase"]==2 for n in d["news"])}件。背景資料を含む。'
    comp=''.join(f'<tr><th scope="row">{e(c["ids"])}</th><td>{e(c["before"])}</td><td>{e(c["after"])}</td><td>{e(c["reason"])}</td></tr>' for c in d['comparison'])
    defined=[s for s in d['scenarios'] if s['id'] not in ('I','J') and s['p_final'] is not None]
    changes=[s for s in defined if s['daily_delta_pp'] is not None and s['daily_delta_pp'] != 0]
    comparable=[s for s in defined if s['daily_delta_pp'] is not None]
    moves='初回の確率記録です。前日差と上昇・低下は、比較可能な次回の記録から表示します。' if d['initial'] else '前日の比較可能な記録がないため、上昇・低下は判定しません。' if not comparable else '本日の比較可能なシナリオに確率の変更はありません。' if not changes else ' / '.join(f'{s["id"]} {s["daily_delta_pp"]:+g} pt：{s["reason"]}' for s in sorted(changes,key=lambda s:abs(s['daily_delta_pp']),reverse=True)[:3])
    return f'''<div class="edition"><span>DAILY BRIEF <b>No. {e(d['edition'])}</b></span><time datetime="{date}">{date.replace('-','.')}</time><span>日本への影響を読む</span></div>
<a class="scenario-guide-link" href="{url('method/')}#scenario-guide"><span class="guide-link-label">はじめて読む方へ</span><span class="guide-link-copy"><strong>主シナリオと世界の横断変数を読む</strong><span>想定している展開と、可能性を判断する条件を確認する</span></span><span class="guide-link-arrow" aria-hidden="true">→</span></a>
<div class="intro"><div><p class="eyebrow">TODAY’S OUTLOOK</p><h1>{e(d['title'])}</h1><ul class="summary-list">{summaries}</ul></div><aside class="edition-meta"><span class="label">本日の記録</span><strong>{date[5:].replace('-',' / ')}</strong><p>①情報固定 {date_label(d['cutoff_at'])}<br>公開版作成 {date_label(d['prepared_at'])}</p><a class="button" href="#full-report">日報全文を読む ↓</a><a href="{url('reports/'+date+'/report.md')}" download>Markdownを保存 ↗</a></aside></div>
<nav class="jump-nav" aria-label="日報内"><a href="#scenarios">主シナリオ A〜H</a><a href="#variables">世界の横断変数</a><a href="#news">ニュース <span>{len(d['news'])}</span></a><a href="#comparison">Web → 研究確認後</a><a href="#full-report">4段階の分析</a></nav>
<section class="highlights" aria-label="本日の焦点">{highlights}</section>
<div class="movement"><span class="movement-label">今日の動き</span><p>{e(moves)}</p></div>
<section id="scenarios">{section_title('MAIN SCENARIOS / A–H','主シナリオの可能性と、その動き','各行から判定条件・根拠・次の注目点へ')}<div class="section-toolbar"><p>期限：{deadline_label(d)}<br><span class="muted">併存可能な事象の主観推定。文字順は深刻さ・発生確率の順位ではありません。</span></p><label class="js-only">並び順 <select id="scenario-sort"><option value="id">分類順</option><option value="probability">確率の高い順</option></select></label></div>{scenario_table(d,history,[s for s in d['scenarios'] if s['id'] not in ('I','J')])}
<div class="legend"><span><i class="dot high"></i>60%以上</span><span><i class="dot medium"></i>30%以上60%未満</span><span><i class="dot low"></i>30%未満</span><span class="up">▲ 上昇</span><span class="down">▼ 低下</span><span>→ 据置 / — 比較不可</span></div><p class="small muted">色は日本への良悪を表しません。根拠の確度と確率は別です。初回は読後に数値化し、読前値を遡って作成していません。<a href="{url('method/')}">確率の読み方 →</a></p></section>
{render_variables(d,WORLD_VARIABLES,url)}
{reserve_note(d)}
<section id="news">{section_title('NEWS DESK','今日のニュースをたどる',news_scope)}<form class="filters js-only" id="news-filters" role="search"><label class="search-label">キーワード<input id="news-search" type="search" placeholder="例：関税、保険、台湾" autocomplete="off"></label><label>分野<select id="news-category"><option value="">すべての分野</option>{categories}</select></label><label>シナリオ・リスク<select id="news-scenario"><option value="">すべて</option>{select_s}</select></label><label>種別<select id="news-status"><option value="">すべて</option><option>新着</option><option>継続</option><option>追加確認</option><option>背景</option></select></label><button class="text-button" type="reset">解除</button></form><p class="small muted">{e(d['news_window_label'])}</p><p id="news-count" class="result-count" aria-live="polite">{len(d['news'])}件を表示</p><div id="news-list" class="news-list">{''.join(news_card(n,d['date']) for n in d['news'])}</div><p id="news-empty" class="empty-state" hidden>条件に合うニュースがありません。「解除」で全件に戻せます。</p></section>
<section id="comparison">{section_title('SECOND LOOK','研究を読んで、判断はどう変わったか','今日のWeb判断 → 今日の研究確認後。前日差とは別の比較。')}<p class="section-lead">{e(d['comparison_summary'])}</p><div class="table-scroll"><table class="comparison-table"><thead><tr><th scope="col">対象</th><th scope="col">① Web判断</th><th scope="col">② 研究確認後</th><th scope="col">③ 変化・不変の理由</th></tr></thead><tbody>{comp}</tbody></table></div><p class="note">{e(d['pre_post_note'])}</p></section>
<section id="full-report">{section_title('THE DAILY REPORT','本日の日報を読む',f'サマリーから総合判断まで、{display_chars(md):,}字（空白・URL・装飾を除く）。')}<p class="small muted">当初の本文にあるIは、現在の一覧では世界の横断変数と区別した過去の参考見通しとして扱っています。</p><div class="report-layout"><aside class="report-index"><p class="eyebrow">CONTENTS</p><a href="#phase-1">① Web分析・ニュース</a><a href="#phase-2">② 研究確認・追加分析</a><a href="#phase-3">③ 判断の違い</a><a href="#phase-4">④ 総合判断</a><button type="button" class="button print-button js-only">印刷 / PDFに保存</button><a href="{url('reports/'+date+'/data.json')}" download>公開データ JSON ↗</a></aside><article class="report-prose">{markdown(md)}</article></div></section>'''

def scenario_page(s,d,history):
    related=[n for n in d['news'] if s['id'] in n['scenarios']]
    back_anchor='variables' if s['id']=='I' else 'scenarios'
    page_group='ARCHIVED OUTLOOK / I' if s['id']=='I' else 'RESERVE / J' if s['id']=='J' else 'SCENARIO '+s['id']
    role_note='<p class="note">旧Iは当初の主観的な参考見通しとして保存しています。現在は主シナリオの一覧から分け、世界の横断変数として物流・制度の観測値と状態を追います。この過去の％を実測値や被害規模に転用していません。</p>' if s['id']=='I' else ''
    rows=''
    for h in reversed(history):
        r=next((r for r in h['scenarios'] if r['id']==s['id']),None)
        if not r: continue
        href=url('reports/'+h['date']+'/scenarios/'+s['id'].lower()+'/')
        condition=f"v{r['definition_version']} / {h['series_id']} / {deadline_label(h)}"
        rows+=f'<tr><th scope="row"><a href="{href}">{h["date"]}</a></th><td>{pct(r["p_web_before_github"])}</td><td>{pct(r["p_final"])}</td><td>{delta(r["daily_delta_pp"],"初回" if h["initial"] else "比較不可")}</td><td>{delta(r["github_delta_pp"],"読前未設定")}</td><td><details><summary>{e(condition)}</summary>{e(r["target"])}</details></td></tr>'

    return f'''<a class="back-link" href="{url("reports/"+d["date"]+"/")}#{back_anchor}">← 日報の一覧へ</a><div class="detail-heading"><div><p class="eyebrow">{page_group} / {d['date']}</p><h1>{e(s['label'])}</h1><p>{e(s['reason'])}</p></div><div class="detail-value"><span class="probability {band(s['p_final'])}">{pct(s['p_final'])}</span><span>最終主観確率 / 根拠の確度：{e(s['evidence_confidence'])}</span>{delta(s['daily_delta_pp'],'未定義' if s['p_final'] is None else '初回' if d['initial'] else '比較不可')}</div></div>{role_note}<div class="definition"><p class="eyebrow">WHAT COUNTS / 判定条件 v{s['definition_version']}</p><p>{e(s['target'])}</p><small>予測開始：{date_label(d['forecast_start'])}。期限：{deadline_label(d)}。Iは期限時点での残存を判断。</small></div><div class="evidence-grid"><section><p class="eyebrow">観測・支持材料</p><p>{e(s['support'])}</p></section><section><p class="eyebrow">反証・留保</p><p>{e(s['counter'])}</p></section><section><p class="eyebrow">次の注目点</p><p>{e(s['watch'])}</p></section></div><section>{section_title('RECORD','確率と判断の履歴')}<p>読前が未設定なら数値差を計算しません。定義・期限が変わる場合は比較を区切ります。</p><div class="table-scroll"><table><thead><tr><th>日付</th><th>今日Web判断</th><th>最終確率</th><th>前日最終比</th><th>今日①→②</th><th>当時の判定条件</th></tr></thead><tbody>{rows}</tbody></table></div></section><section>{section_title('RELATED NEWS','この項目に関係するニュース')}<div class="news-list">{''.join(news_card(n,d['date']) for n in related) or '<p class="empty-state">本日のニュースに該当する項目はありません。</p>'}</div></section>'''

def scenario_guide(d):
    # Plain-language introductions supplement the recorded definitions, which
    # remain the source of truth. New definition versions fall back to their text.
    descriptions = {
        ('A', 1): '米国と日本などの同盟国が、第一列島線に関わる演習・基地運用・共同対処・補給の協力を新たに進める展開です。前方で協力を強める方向を見ます。',
        ('B', 1): '米国が同盟を維持しながら、日本に求める費用や役割を具体化する展開です。「もっと負担を」という発言に加え、金額・比率・任務・期限が示されるかを見ます。',
        ('C', 1): '米国が本土・西半球を優先し、その分、他地域の任務・配置・予算を具体的に縮小する展開です。国内重視の姿勢だけでなく、資源の振り向け方が実際に変わるかを見ます。',
        ('D', 1): '米国が第一列島線での配置・任務・同盟上の役割を縮め、より後方の第二列島線へ重心を移す展開です。後方の拠点を強化しただけでは、この後退に当たりません。',
        ('E', 1): '米中が新たな関税緩和などの経済措置について、対象・税率・実施日のいずれかを双方から具体的に公表する展開です。一部の品目だけの限定合意も対象で、米中経済関係全体の正常化を意味するものではありません。',
        ('F', 1): '経済的な譲歩と、台湾への供与や第一列島線の軍事態勢に対する具体的な制約を、米中が同じ合意の交換条件にする展開です。双方が正式に公表した条件を見ます。',
        ('G', 1): '米中が台湾・西太平洋の勢力圏や同盟国の扱いについて、継続的に折り合う枠組みをつくる展開です。「quasi-G2」はこの大国間の協商を指し、通常の会談や経済合意だけでは成立としません。',
        ('H', 1): '米中の経済条件が改善しても、日本の同等の品目・業務には規制や追加負担が残る、または強まる展開です。同じ条件で比べられる取引や企業への影響を確認します。',
        ('I', 1): '中東から日本への輸送を妨げる保険・制裁・決済・通航などの制約が、評価期限の時点でも残る展開です。停戦が成立するかどうかとは別に、物流が実際に回復できるかを見ます。',
        ('J', 1): '既存の枠で捉えきれない展開のための予備枠です。現在は判定対象を定めていないため確率も未設定で、A〜Iの「残りの確率」を表すものではありません。'
    }
    groups=[('主シナリオ A〜H',lambda s:s['id'] not in ('I','J')),('過去の参考見通し（旧I）',lambda s:s['id']=='I'),('予備枠 J',lambda s:s['id']=='J')]
    links=''; cards=[]
    for group,predicate in groups:
        items=[s for s in d['scenarios'] if predicate(s)]
        if not items: continue
        links+=f'<div class="guide-index-group"><span>{e(group)}</span><div>'+''.join(f'<a href="#guide-{e(s["id"].lower())}" aria-label="{e(observation_label(s["id"])+" "+s["label"])}">{e(s["id"])}</a>' for s in items)+'</div></div>'
        cards.append(f'<h3 class="guide-group-title">{e(group)}</h3>')
        for s in items:
            description=descriptions.get((s['id'],s['definition_version']),s['target'])
            if s['id']=='I': description='当初はIとして確率を置きましたが、現在は主シナリオの一覧から分離しています。以下は当初の判定対象の説明で、物流変数の現在値ではありません。'+description
            detail=url('reports/'+d['date']+'/scenarios/'+s['id'].lower()+'/')
            cards.append(f'''<article class="guide-scenario" id="guide-{e(s['id'].lower())}"><h4><span class="scenario-id">{e(s['id'])}</span>{e(s['label'])}</h4><p>{e(description)}</p><details><summary>この日報での判定条件</summary><p>{e(s['target'])}</p></details><a class="guide-detail-link" href="{detail}">{e(d['date'])}の確率・根拠を見る →</a></article>''')
    return f'''<section class="method-prose scenario-guide" id="scenario-guide" aria-labelledby="scenario-guide-title"><p class="eyebrow">SCENARIO GUIDE</p><h2 id="scenario-guide-title">主シナリオと世界の横断変数の違い</h2><p><strong>A〜Hは主シナリオ</strong>として、米国の安全保障・同盟、米中の取引と日本への波及を見ます。<strong>世界の横断変数</strong>では、海峡・運河の通航、供給、エネルギー、制度、物価・金融などの条件と変化を別枠で追います。旧Iは過去の参考見通し、Jは未設定の予備枠として保持します。</p><p>横断変数はA〜Hのどの展開でも変化し得ます。例えば米中関係が改善しても、バブ・エル・マンデブ海峡の航行妨害や、パナマ運河の予約枠・喫水制限が残れば、輸送条件は改善しない場合があります。別枠の表示は、互いに無関係という意味ではありません。</p><p class="note">日本への影響の深刻さと、事象が起こる確率は別の軸です。A〜Hの文字順も、深刻さや発生確率の順位ではありません。複数が併存するため、確率の合計を100％にはしません。</p><p class="small muted">{e(d['date'])}号の定義に基づく説明です。評価期限：{deadline_label(d)}。Iは期限時点での制約の残存、主シナリオは開始後から期限までの確認を見ます。</p><nav class="guide-index" aria-label="主シナリオと過去の参考見通しの説明へ">{links}</nav><div class="guide-scenarios">{''.join(cards)}</div><a class="guide-return" href="{url()}#scenarios">最新の日報の一覧へ戻る →</a></section>'''


def method(d):
    return '<div class="page-heading"><p class="eyebrow">READING GUIDE</p><h1>確率を読み、判断の根拠を確かめる。</h1><p>毎日の見通しを同じ条件で比較するための、日報の作り方と読み方。</p></div>'+scenario_guide(d)+'''<section class="method-prose variable-method" id="variable-guide"><p class="eyebrow">GLOBAL VARIABLES</p><h2>横断変数は「世界の条件がどう変わったか」を見る</h2><p>シナリオは米中関係の展開、横断変数はその展開にも日本への影響にも関係する観測項目です。原油価格などの連続的な数値に加え、「予約枠に制限」「対象船への封鎖宣言」「通航再開」といった状態も記録します。</p><ul><li><strong>バブ・エル・マンデブ海峡／紅海：</strong>フーシ派の封鎖宣言の対象、攻撃、実通航、船社の回避、保険料。対象船を限定した措置と海峡の全面閉鎖を分けます。</li><li><strong>パナマ運河：</strong>水位、予約枠、実通航数、喫水、待ち時間、予約・輸送費用。予定された制限と施行済みのルールを分けます。</li><li><strong>その他の共通条件：</strong>ホルムズの通航・防護、パイプライン、原油価格、制裁・決済・保険、物価・金融。</li></ul><p>値・単位・対象日・公表日・情報の種類・比較元・変化・出典を示します。未取得は0や平常ではありません。更新周期は日次・月次・発表時などで異なり、日報の前日差と資料の前回値からの差を混同しません。</p><p>市場の利上げ織込みと日報の主観確率は別物です。横断変数の変化からA〜Hへ影響する経路は文章で説明し、機械的な点数や確率の加減算にはしません。旧Iの70％は当初の参考見通しとして過去号に残し、横断変数の実測値に置き換えていません。</p></section>'''+render_bottleneck_guide(ROOT)+'''<article class="method-prose">
<h2>4段階で判断を記録します</h2><ol><li><strong>Web分析：</strong>公開ニュースとデータを調べ、シナリオごとの判断・確率・根拠・情報締切を先に記録します。</li><li><strong>研究の確認：</strong>その後にGitHub上の参照研究を読み、公開原資料を確認して追加分析します。</li><li><strong>違いの説明：</strong>変わった判断、変わらない判断、追加事実、重複資料を区別します。</li><li><strong>総合判断：</strong>日本へのリスクと機会、次の観測、判断を変える条件をまとめます。</li></ol>
<p>この日報は研究から情報を受け取る運用です。研究へ作業を依頼したり、日報の判断を書き戻したりしません。参照研究が非公開でも、公開版では読者が確認できる原資料へのリンクと日報自身の分析を示します。</p>
<h2>％は未校正の主観推定です</h2><p>確率は統計モデルや市場の価格から自動算出した値ではありません。原則5ポイント刻みで、定義した事象の可能性を見積もります。根拠の確度「中・低」は材料の強さや不確かさを表す別の評価です。未取得の資料や不明な値を0％に変換しません。</p>
<p>主シナリオA〜Hは同時に起こり得るため、合計100％にはなりません。世界の横断変数には実測値・公式ルール・報道された状態・市場期待などを、その種類を明記して載せます。Jは残りの確率ではなく、対象未定義の予備枠です。</p>
<h2>期限・判定対象を揃えます</h2><p>初期の予測開始は2026年9月13日11:36 JST、期限は2026年11月3日23:59米東部時間です。Aなどは開始後から期限までに条件を満たす事象を公式確認する見通し。Iは、停戦の有無を問わず期限時点で日本向け中東輸送の制約が残る見通しです。過去の演習や措置は判断材料であり、将来の条件達成そのものとしません。</p>
<h2>二つの差を分けます</h2><p><strong>前日差</strong>は今日の最終確率−前日の比較可能な最終確率。<strong>今日①→②</strong>は研究確認後の最終確率−今日のWeb分析時点の確率。単位はパーセントポイント（pt）です。40％から45％なら+5ptです。定義・評価期限・系列が違う場合や値が欠ける場合は「比較不可」とします。</p>
<p>初回9月13日は日報の読後に初めて数値化しました。過去日の値と当日の読前確率は存在せず、差や推移を遡って作っていません。同日の研究に先に触れた履歴もあるため、完全な初見・独立した盲検分析とは扱いません。今後も過去に読んだ知識は残ります。</p>
<h2>色は利害や危険度ではありません</h2><p>橙は60％以上、黄は30％以上60％未満、青は30％未満。動きは赤の▲上昇、青の▼低下、→据置、—初回・比較不可です。色だけに頼らず、数値・文字・矢印を併記します。Aの同盟強化とIの物流制約が同じ色でも、日本への意味は異なります。</p>
<h2>ニュースの範囲と出典</h2><p>直近24時間を中心に、影響が続く数日前の発表や背景資料も含めます。新着・継続・追加確認・背景を表示し、公表日と発生日を分けます。件数はニュース項目数で、同じ事象に関する転載は独立の証拠として重複加算しません。発言、予定、暫定措置、実施済みの決定を区別します。</p><p>初回のWeb分析固定は9月13日11:20 JSTごろ。研究確認後に追加した2件は②の段階の確認です。リンク先は更新・削除されることがあり、ライブページと大学指標ページの表示内容は日報掲載時点から変わる場合があります。原文転載はせず短い要約と直接リンクを掲載します。</p>
<p>各ニュースの「国・地域」ラベルは、記事が主に扱う国や地域を示します。複数国に関わる場合は併記し、特定国に絞れない市況は「国際市場」と表示します。ニュースのキーワード検索では国名でも絞り込めます。</p>
<h2>公開・更新・訂正</h2><p>日本時間の毎日15時30分に調査・分析を開始し、日報の作成・検査、GitHubへの保存、GitHub Pagesの公開確認まで実施する運用です。公開は作成・検査の完了後になります。最新号へのリンクと、日付ごとの固定ページを用意します。画面の日付・情報固定時刻で、どの時点の判断かを確認してください。新しい日報が未公開の場合、前回号をその日の日報と表示しません。</p><p>過去の確率や本文は新しい予測で上書きせず保持します。誤記や出典の修正は対象の日報に訂正注記を追加し、日付・理由を訂正履歴に追記します。元の本文・数値はそのまま保持します。モデルの指定はGPT-6 Astra / Ultra。実行時に確認できたモデルを各号に記録します。</p>
<p>印刷ボタンから日報部分を印刷・PDF保存できます。RSSは公開済みの日報へのリンクを配信します。ログイン、コメント、トラッキング用Cookieは設けていません。</p></article>'''


def correction_notice(d, records):
    matching=[c for c in records if c['report_date']==d['date']]
    if not matching: return ''
    return '<aside class="note" aria-label="訂正注記"><strong>この号の訂正・追記</strong><ul>'+''.join(f'<li>{e(c["date"])}：{e(c["text"])}</li>' for c in matching)+'</ul><p>以下の本文と数値は当初の公開記録を保持しています。</p></aside>'

def write(path,text):
    target=OUT/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(text,encoding='utf-8',newline='\n')

def build(base='/japan-scenario-daily'):
    global BASE, NEWS_LABELS, WORLD_VARIABLES
    BASE=base.rstrip('/')
    WORLD_VARIABLES=load_variables(ROOT)
    NEWS_LABELS={p.parent.name:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'content').glob('????-??-??/news-labels.json')}
    # Never delete arbitrary paths. This fixed generated-output path is repo-local.
    if OUT.exists():
        assert OUT.resolve().parent == ROOT and not OUT.is_symlink()
        shutil.rmtree(OUT)
    OUT.mkdir()
    history=[]; reports={}
    for path in sorted((ROOT/'content').glob('????-??-??/data.json')):
        d=json.loads(path.read_text(encoding='utf-8')); history.append(d)
        labels=NEWS_LABELS.get(d['date'],{})
        if not set(labels)<=set(n['id'] for n in d['news']): raise ValueError('Unknown news label ID')
        for n in d['news']:
            countries=n.get('countries') or labels.get(n['id'],[])
            if not isinstance(countries,list) or not countries or not all(isinstance(c,str) and c.strip() for c in countries):
                raise ValueError('Missing country/region labels: '+d['date']+'/'+n['id'])
        reports[d['date']]=(path.parent/'report.md').read_text(encoding='utf-8')
    if not history: raise ValueError('No public report records')
    latest=history[-1]
    corrections_data=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'corrections').glob('*.json'))]
    write('index.html',page(latest['title'],correction_notice(latest,corrections_data)+report_dashboard(latest,history,reports[latest['date']]),data={'history':history}))
    for i,d in enumerate(history):
        route='reports/'+d['date']+'/'
        write(route+'index.html',page(d['date']+'の日報',correction_notice(d,corrections_data)+report_dashboard(d,history[:i+1],reports[d['date']],route),route,data={'history':history[:i+1]}))
        write(route+'report.md',reports[d['date']]); write(route+'data.json',json.dumps(d,ensure_ascii=False,indent=2)+'\n')
        if d['date'] in WORLD_VARIABLES: write(route+'variables.json',json.dumps(WORLD_VARIABLES[d['date']],ensure_ascii=False,indent=2)+'\n')
        if d['date'] in NEWS_LABELS: write(route+'news-labels.json',json.dumps(NEWS_LABELS[d['date']],ensure_ascii=False,indent=2)+'\n')
        for s in d['scenarios']:
            detail=route+'scenarios/'+s['id'].lower()+'/'
            write(detail+'index.html',page(d['date']+' '+s['label'],correction_notice(d,corrections_data)+scenario_page(s,d,history[:i+1]),detail))
    last_seen={}
    for i,d in enumerate(history):
        for s in d['scenarios']: last_seen[s['id']]=(i,d,s)
    for i,d,s in last_seen.values():
        route='scenarios/'+s['id'].lower()+'/'
        write(route+'index.html',page(s['label'],scenario_page(s,d,history[:i+1]),route))
    archive='<div class="page-heading"><p class="eyebrow">ARCHIVE</p><h1>毎日の判断を、記録に残す。</h1><p>公開済み '+str(len(history))+' 日分。元の判断と根拠を日付でたどれます。</p></div><div class="archive-list">'
    for d in reversed(history):
        archive+=f'<a class="archive-item" href="{url("reports/"+d["date"]+"/")}"><time>{d["date"]}</time><div><h2>{e(d["title"])}</h2><p>{e(d["summary"][0])}</p></div><span>読む ↗</span></a>'
    archive+='</div>'
    write('archive/index.html',page('アーカイブ',archive,'archive/','archive'))
    options=''.join(f'<option value="{d["date"]}">{d["date"]}</option>' for d in reversed(history))
    compare=f'''<div class="page-heading"><p class="eyebrow">COMPARE DATES</p><h1>昨日から変わったことを確かめる。</h1><p>前日の最終判断と、今日の最終判断を比較します。研究確認前後の違いは、各日報の「研究を読んで、判断はどう変わったか」で読めます。</p></div><div class="compare-controls js-only"><label>比較元<select id="compare-from">{options}</select></label><span aria-hidden="true">→</span><label>比較先<select id="compare-to">{options}</select></label></div><div id="date-comparison" aria-live="polite"><p class="empty-state">{'初回の公開です。2日目から日付を選んで確率と判断の変化を比較できます。' if len(history)<2 else '日付を選ぶと比較できます。JavaScriptが無効の場合はアーカイブから各日報をご覧ください。'}</p></div><p class="note">欠測は0ではありません。日付が連続しない場合は指定日間の比較であり、前日差とは表示しません。判定条件や期限の変更をまたぐ差は算出しません。</p><a class="button" href="{url('archive/')}">過去の日報へ →</a>'''
    write('compare/index.html',page('日付で比較',compare,'compare/','compare',{'history':history}))
    corrections='<section class="method-prose"><h2>訂正・公開履歴</h2><ul>'+''.join(f'<li><time>{e(c["date"])}</time> — {e(c["text"])}</li>' for d in reversed(history) for c in d['corrections'])+'</ul></section>'
    corrections+='<ul class="method-prose">'+''.join(f'<li>{e(c["date"])} / {e(c["report_date"])}号の訂正：{e(c["text"])}</li>' for c in corrections_data)+'</ul>'
    write('method/index.html',page('読み方・シナリオ・手法',method(latest)+corrections,'method/','method'))
    write('404.html',page('ページが見つかりません',f'<div class="page-heading"><p class="eyebrow">404</p><h1>このページは見つかりません。</h1><a class="button" href="{url()}">最新の日報へ →</a></div>','404.html'))
    feed='<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>'+TITLE+'</title><link>'+SITE+'/</link><description>米中関係と米中間選挙の日報</description><language>ja</language><atom:link href="'+SITE+'/feed.xml" rel="self" type="application/rss+xml"/>'
    for d in reversed(history):
        link=SITE+'/reports/'+d['date']+'/'
        feed+=f'<item><title>{e(d["date"]+" "+d["title"])}</title><link>{link}</link><guid isPermaLink="true">{link}</guid><pubDate>{format_datetime(dt.datetime.fromisoformat(d["prepared_at"]))}</pubDate><description>{e(" ".join(d["summary"]))}</description></item>'
    write('feed.xml',feed+'</channel></rss>')
    paths=['','archive/','compare/','method/']+['reports/'+d['date']+'/' for d in history]+['scenarios/'+s['id'].lower()+'/' for s in latest['scenarios']]
    write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{SITE}/{p}</loc></url>' for p in paths)+'</urlset>')
    shutil.copytree(ROOT/'assets',OUT/'assets')
    write('.nojekyll','')
    print(f'Built {len(history)} report(s), {len(latest["news"])} news items, {len(latest["scenarios"])} scenario pages.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--base-path',default='/japan-scenario-daily'); args=parser.parse_args(); build(args.base_path)
