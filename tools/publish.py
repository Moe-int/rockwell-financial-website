#!/usr/bin/env python3
"""Rockwell Financial site publisher (no dependencies).
Usage: python3 tools/publish.py
- Builds <slug>/index.html for every content/articles/<slug>.json (always regenerated from tools/article_template.html).
- Rebuilds insights listing pages (9 per page, newest first), the 4 "latest" cards on the home page, and sitemap.xml.
Article JSON keys: slug, title, description (120-155 chars), date (YYYY-MM-DD), img (path under uploads/ or img/), img_alt, body (HTML: p, h2, h3, ul/ol/li, strong, em, a, blockquote, table).
"""
import json, re, pathlib, datetime, html
ROOT=pathlib.Path(__file__).resolve().parent.parent; BASE="https://rockwellfinancial.com.au/"; PER=9
def esc(s): return html.escape(s, quote=True)
def disp(d): return d.strftime("%B %-d, %Y")
# ---------- 1. build pages from JSON ----------
tpl=(ROOT/"tools/article_template.html").read_text()
specs=[json.loads(p.read_text()) for p in sorted((ROOT/"content/articles").glob("*.json"))]
def article_dirs():
    out=[]
    for d in ROOT.iterdir():
        f=d/"index.html"
        if d.is_dir() and f.exists():
            t=f.read_text()
            if '<aside class="side">' not in t: continue
            h1=re.search(r'<h1 class="art-h1">(.*?)</h1>',t,re.S); dt=re.search(r'<div class="meta"><span>By <b>Rockwell Financial</b></span><span>([^<]+)</span>',t)
            img=re.search(r'class="featured" src="\.\./([^"]+)"',t)
            try: date=datetime.datetime.strptime(dt.group(1).strip(),"%B %d, %Y").date()
            except Exception: date=datetime.date(2020,1,1)
            out.append(dict(slug=d.name,title=html.unescape(re.sub(r'<[^>]+>','',h1.group(1))).strip(),date=date,img=img.group(1) if img else "uploads/about-new.png"))
    out.sort(key=lambda a:(a["date"],a["slug"]), reverse=True); return out
for s in specs:
    d=datetime.date.fromisoformat(s["date"]); url=BASE+s["slug"]+"/"
    others=[a for a in article_dirs() if a["slug"]!=s["slug"]][:4]
    more="".join(f'<a href="../{a["slug"]}/">{esc(a["title"])}</a>' for a in others)
    ld={"@context":"https://schema.org","@graph":[
        {"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Home","item":BASE},{"@type":"ListItem","position":2,"name":"Resources & Insights","item":BASE+"insights/"},{"@type":"ListItem","position":3,"name":s["title"],"item":url}]},
        {"@type":"BlogPosting","headline":s["title"],"description":s["description"],"image":BASE+s["img"],"datePublished":s["date"],"dateModified":s.get("modified",s["date"]),"author":{"@type":"Organization","name":"Rockwell Financial","url":BASE},"publisher":{"@type":"Organization","name":"Rockwell Financial","logo":{"@type":"ImageObject","url":BASE+"brand/logo.png"}},"mainEntityOfPage":url,"inLanguage":"en-AU","keywords":s.get("keywords","")}]}
    page=(tpl.replace("{{TITLE_ESC}}",esc(s["title"])).replace("{{DESC_ESC}}",esc(s["description"])).replace("{{URL}}",url)
           .replace("{{IMG_ABS}}",BASE+s["img"]).replace("{{JSONLD}}",json.dumps(ld,ensure_ascii=False).replace("</","<\\/"))
           .replace("{{TITLE_HTML}}",esc(s["title"])).replace("{{DATE_DISPLAY}}",disp(d)).replace("{{IMG}}",s["img"])
           .replace("{{IMG_ALT_ESC}}",esc(s.get("img_alt",s["title"]))).replace("{{BODY}}",s["body"]).replace("{{MORE}}",more))
    out=ROOT/s["slug"]; out.mkdir(exist_ok=True); (out/"index.html").write_text(page)
# ---------- 2. listings ----------
arts=article_dirs()
def card(a,pre): return (f'<div class="post"><a href="{pre}{a["slug"]}/"><img loading="lazy" decoding="async" src="{pre}{a["img"]}" alt="{esc(a["title"])}"></a>'
                          f'<div><small>{disp(a["date"])}</small><h4><a href="{pre}{a["slug"]}/">{esc(a["title"])}</a></h4><a href="{pre}{a["slug"]}/">Read article<i>↗</i></a></div></div>')
n=(len(arts)+PER-1)//PER
t1=(ROOT/"insights/index.html").read_text(); t2=(ROOT/"insights/page/2/index.html").read_text()
for k in range(n):
    pre="../" if k==0 else "../../../"; t=t1 if k==0 else t2
    chunk="".join(card(a,pre) for a in arts[k*PER:(k+1)*PER])
    t=re.sub(r'(<div class="blog blog3">).*?(</div>\s*<div class="pager">)',lambda m:m.group(1)+chunk+m.group(2),t,count=1,flags=re.S)
    pager="".join(f'<a href="{pre}insights/{"" if i==0 else f"page/{i+1}/"}"{" class=on" if i==k else ""}>{i+1}</a>' for i in range(n))
    if k<n-1: pager+=f'<a href="{pre}insights/page/{k+2}/">→</a>'
    t=re.sub(r'<div class="pager">.*?</div>',f'<div class="pager">{pager}</div>',t,count=1,flags=re.S)
    t=re.sub(r'Page \d+ of \d+ · \d+ articles',f'Page {k+1} of {n} · {len(arts)} articles',t)
    if k>0:
        t=re.sub(r'Page \d+ \|',f'Page {k+1} |',t); t=re.sub(r'insights/page/\d+/"',f'insights/page/{k+1}/"',t)
        t=re.sub(r'("name": ?")Page \d+(")',rf'\g<1>Page {k+1}\2',t); t=re.sub(r'(insights/page/)\d+(/")',rf'\g<1>{k+1}\2',t)
        t=re.sub(r'<div class="pager">.*?</div>',f'<div class="pager">{pager}</div>',t,count=1,flags=re.S)
    dest=ROOT/("insights" if k==0 else f"insights/page/{k+1}"); dest.mkdir(parents=True,exist_ok=True); (dest/"index.html").write_text(t)
h=(ROOT/"index.html").read_text()
h=re.sub(r'(<div class="blog">).*?(</div>\s*</div></section>)',lambda m:m.group(1)+"".join(card(a,"") for a in arts[:4])+m.group(2),h,count=1,flags=re.S)
(ROOT/"index.html").write_text(h)
# ---------- 3. sitemap ----------
sm=(ROOT/"sitemap.xml").read_text(); have=set(re.findall(r'<loc>([^<]+)</loc>',sm)); add=""
for a in arts:
    u=BASE+a["slug"]+"/"
    if u not in have: add+=f"<url><loc>{u}</loc><lastmod>{a['date'].isoformat()}</lastmod></url>\n"
for k in range(2,n+1):
    u=f"{BASE}insights/page/{k}/"
    if u not in have: add+=f"<url><loc>{u}</loc><lastmod>{datetime.date.today().isoformat()}</lastmod></url>\n"
(ROOT/"sitemap.xml").write_text(sm.replace("</urlset>",add+"</urlset>"))
print(f"articles: {len(arts)} | insights pages: {n} | built from JSON: {len(specs)} | sitemap +{add.count('<url>')}")
