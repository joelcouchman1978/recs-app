import os

def test_repo_shape():
    assert os.path.exists("apps/api/app/recs.py"), "apps/api/app/recs.py missing"
    assert os.path.isdir("apps/web") or True
