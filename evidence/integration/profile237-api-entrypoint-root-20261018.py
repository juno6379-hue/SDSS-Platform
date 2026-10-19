"""Explicit Root-selected local source profile; localhost development API only."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(R/'backend')]
sys.path.append(str(R/'.runtime'))
from app.main import app,store
assert store.root==R/'data'
app.state.collection_source_profile_path=str(R/'data/first-group-training-priority/source-profile237-root-20261018.json')
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=8002)
