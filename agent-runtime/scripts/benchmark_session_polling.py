#!/usr/bin/env python3
"""Compare compatible full-session listing with compact sidebar polling."""
import os
from pathlib import Path
import sys
import tempfile
import time
import json
import statistics

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['PLATFORM_DATA_DIR']=tempfile.mkdtemp(prefix='session-polling-benchmark-')
from platform_app import domain as d,runtime as rt
from platform_app.main import app
from fastapi.testclient import TestClient

for i in range(50):
    identity=f'benchmark-{i:03d}'
    d.put('session',dict(id=identity,model_id='test/model',status='completed',messages=[dict(role='user',content=f'Report {i}'),dict(role='assistant',content='Document analysis. '*5000)],created_at='2026-11-11T10:00:00Z',updated_at='2026-11-11T10:00:00Z',event_seq=100))
    context=rt.resolve(identity)
    for j in range(10):(context.files_root/f'note-{j}.txt').write_text('Report note')
client=TestClient(app)
results={}
for name,url in [('full','/api/agent/sessions'),('summary','/api/agent/sessions?summary=true')]:
    client.get(url)
    samples=[]
    for _ in range(5):
        start=time.perf_counter();response=client.get(url);samples.append(round((time.perf_counter()-start)*1000,3));assert response.status_code==200
    results[name]=dict(median_ms=statistics.median(samples),samples_ms=samples,response_bytes=len(response.content),sessions=len(response.json()))
print(json.dumps(results,indent=2))
import shutil
shutil.rmtree(os.environ['PLATFORM_DATA_DIR'])
