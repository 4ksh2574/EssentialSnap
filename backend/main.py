import os, tempfile, shutil, subprocess, json, re
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app=FastAPI(title='EssentialSnap API')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['POST','GET'],allow_headers=['*'])
ALLOWED={'youtube.com','youtu.be','instagram.com','x.com','twitter.com'}
class Link(BaseModel): url:str
class Download(Link): format_id:str

def check_url(value):
    try:
        u=urlparse(value); host=(u.hostname or '').lower()
        if u.scheme not in ('http','https') or not host or not any(host==d or host.endswith('.'+d) for d in ALLOWED):
            raise ValueError()
    except Exception: raise HTTPException(400,'Supported hosts: YouTube, Instagram and X. Use links to content you are authorized to save.')
    return value

def run(args):
    try: return subprocess.run(args,capture_output=True,text=True,timeout=120)
    except subprocess.TimeoutExpired: raise HTTPException(504,'Timed out while processing media.')

@app.get('/')
def root(): return {'name':'EssentialSnap API','status':'ready'}

@app.post('/api/info')
def info(body:Link):
    url=check_url(body.url)
    r=run(['yt-dlp','--no-warnings','--no-playlist','--skip-download','-J',url])
    if r.returncode: raise HTTPException(400,'Unable to retrieve media metadata. The post may be unavailable or unsupported.')
    try: d=json.loads(r.stdout)
    except: raise HTTPException(500,'Metadata response was invalid.')
    formats=[]
    for f in d.get('formats',[]):
        if not f.get('url') or f.get('vcodec')=='none': continue
        height=f.get('height') or 0
        if not height: continue
        formats.append({'id':str(f.get('format_id')),'label':f'{height}p · {f.get("ext","media")} · {f.get("format_id")}'})
    # Prefer best combined video format; allow selection of available formats only.
    formats.sort(key=lambda x:int(re.search(r'(\\d+)p',x['label']).group(1)),reverse=True)
    if not formats: raise HTTPException(400,'No downloadable video formats were exposed for this link.')
    return {'title':d.get('title','Media'),'platform':d.get('extractor_key','Media'),'duration':d.get('duration'),'formats':formats[:30]}

@app.post('/api/download')
def download(body:Download):
    url=check_url(body.url)
    if not re.fullmatch(r'[A-Za-z0-9_-]+',body.format_id): raise HTTPException(400,'Invalid format selection.')
    tmp=tempfile.mkdtemp(prefix='essentialsnap-')
    out=os.path.join(tmp,'media.%(ext)s')
    r=run(['yt-dlp','--no-warnings','--no-playlist','--max-filesize','150M','-f',body.format_id,'--merge-output-format','mp4','-o',out,url])
    if r.returncode:
        shutil.rmtree(tmp,ignore_errors=True)
        raise HTTPException(400,'Download failed. This format may not be available or permitted.')
    found=[os.path.join(tmp,x) for x in os.listdir(tmp) if os.path.isfile(os.path.join(tmp,x))]
    if not found:
        shutil.rmtree(tmp,ignore_errors=True);raise HTTPException(500,'No file produced.')
    path=found[0]
    def cleanup(): shutil.rmtree(tmp,ignore_errors=True)
    return FileResponse(path,filename=os.path.basename(path),media_type='application/octet-stream',background=None)
