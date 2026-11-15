import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI(title='VocalClean API')
origins = [s.strip().rstrip('/') for s in os.getenv('ALLOWED_ORIGINS', 'http://localhost:8000').split(',') if s.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET','POST'], allow_headers=['*'])
ROOT = Path(os.getenv('DATA_DIR', '/tmp/vocalclean')).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 25 * 1024 * 1024
jobs = {}
lock = threading.Lock()
semaphore = threading.Semaphore(1)
EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}

def update(job_id, **fields):
    with lock:
        jobs[job_id].update(fields)

def process(job_id, input_path):
    with semaphore:
        update(job_id, status='processing')
        try:
            work = ROOT / job_id
            result = subprocess.run(['python', '-m', 'demucs', '--two-stems=vocals', '-n', 'htdemucs', '-o', str(work / 'out'), str(input_path)], capture_output=True, text=True, timeout=1800)
            if result.returncode:
                raise RuntimeError((result.stderr or 'Demucs error')[-800:])
            stem_dir = work / 'out' / 'htdemucs' / input_path.stem
            vocals = stem_dir / 'vocals.wav'
            instrumental = stem_dir / 'no_vocals.wav'
            if not vocals.is_file() or not instrumental.is_file():
                raise RuntimeError('Output files were not created')
            update(job_id, status='done', vocals=str(vocals), instrumental=str(instrumental))
        except Exception as exc:
            update(job_id, status='failed', error=str(exc)[:400])

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/jobs', status_code=202)
async def create_job(file: UploadFile = File(...)):
    filename = Path(file.filename or '').name
    ext = Path(filename).suffix.lower()
    if ext not in EXTENSIONS:
        raise HTTPException(400, 'Unsupported audio extension')
    job_id = uuid.uuid4().hex
    folder = ROOT / job_id
    folder.mkdir()
    input_path = folder / ('input' + ext)
    total = 0
    try:
        with input_path.open('wb') as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise HTTPException(413, 'Maximum file size is 25 MB')
                output.write(chunk)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    finally:
        await file.close()
    if not total:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(400, 'Empty file')
    with lock:
        jobs[job_id] = {'status':'queued', 'created':time.time()}
    threading.Thread(target=process, args=(job_id, input_path), daemon=True).start()
    return {'job_id':job_id, 'status':'queued'}

@app.get('/jobs/{job_id}')
def get_job(job_id: str):
    with lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, 'Job not found')
        return {'status':job['status'], 'error':job.get('error')}

@app.get('/jobs/{job_id}/{stem}')
def download(job_id: str, stem: str):
    if stem not in ('vocals', 'instrumental'):
        raise HTTPException(404, 'Unknown stem')
    with lock:
        job = jobs.get(job_id)
        if not job or job['status'] != 'done':
            raise HTTPException(404, 'Result not available')
        path = job[stem]
    return FileResponse(path, media_type='audio/wav', filename=f'{stem}.wav')
