"""로컬 실증용 영속 카탈로그. 운영 PostGIS 전환 전까지 SQLite를 사용한다."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, root: Path, recover_jobs=False):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'catalog.sqlite3'
        with self.connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, body TEXT, PRIMARY KEY(kind,id))')
        # 프로세스 중단 작업을 성공으로 복원하지 않는다.
        for job in self.list('jobs') if recover_jobs else []:
            if job['status'] in ('queued', 'running'):
                job.update(status='failed', error='서버 재시작으로 중단되었습니다. 입력을 확인하고 다시 실행하십시오.', finished_at=now())
                self.put('jobs', job)

    @contextmanager
    def connect(self):
        # sqlite3의 with만으로는 연결이 닫히지 않아 Windows 파일 잠금이 남는다.
        connection = sqlite3.connect(self.db, timeout=30)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def put(self, kind, record):
        record = dict(record)
        record.setdefault('id', uuid.uuid4().hex)
        record.setdefault('created_at', now())
        with self.connect() as conn:
            conn.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)', (kind, record['id'], json.dumps(record, ensure_ascii=False, allow_nan=False)))
        return record

    def get(self, kind, identifier):
        with self.connect() as conn:
            row = conn.execute('SELECT body FROM records WHERE kind=? AND id=?', (kind, identifier)).fetchone()
        if not row:
            raise KeyError(identifier)
        return json.loads(row[0])

    def list(self, kind):
        with self.connect() as conn:
            rows = conn.execute('SELECT body FROM records WHERE kind=? ORDER BY rowid DESC', (kind,)).fetchall()
        return [json.loads(row[0]) for row in rows]
