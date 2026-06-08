import csv
import json
import os
import tempfile

import pytest

from modules.session_manager import SessionManager, SessionMeta


@pytest.fixture
def mgr(tmp_path):
    return SessionManager(sessions_dir=str(tmp_path))


def test_start_session_creates_file(mgr, tmp_path):
    meta = mgr.start_session()
    assert os.path.exists(os.path.join(str(tmp_path), meta.filename))


def test_start_session_writes_index(mgr, tmp_path):
    mgr.start_session()
    index_path = os.path.join(str(tmp_path), "index.json")
    assert os.path.exists(index_path)
    data = json.loads(open(index_path).read())
    assert len(data) == 1
    assert data[0]["fish_count"] == 0


def test_append_catch_increments_count(mgr, tmp_path):
    mgr.start_session()
    mgr.append_catch("Salmon", "320")
    mgr.append_catch("Bass", "150")
    mgr.end_session()
    sessions = mgr.load_sessions()
    assert sessions[0].fish_count == 2


def test_append_catch_writes_csv_row(mgr, tmp_path):
    meta = mgr.start_session()
    mgr.append_catch("Salmon", "320")
    mgr.end_session()
    path = os.path.join(str(tmp_path), meta.filename)
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["timestamp", "fish_name", "weight_g"]
    assert rows[1][1] == "Salmon"
    assert rows[1][2] == "320"


def test_delete_session_removes_file_and_index_entry(mgr, tmp_path):
    meta = mgr.start_session()
    mgr.end_session()
    mgr.delete_session(meta.id)
    assert not os.path.exists(os.path.join(str(tmp_path), meta.filename))
    assert len(mgr.load_sessions()) == 0


def test_load_sessions_rebuilds_from_files_if_index_missing(mgr, tmp_path):
    meta = mgr.start_session()
    mgr.append_catch("Trout", "200")
    mgr.end_session()
    # Delete index to simulate corruption
    index_path = os.path.join(str(tmp_path), "index.json")
    os.remove(index_path)
    sessions = mgr.load_sessions()
    assert len(sessions) == 1
    assert sessions[0].fish_count == 1


def test_export_csv(mgr, tmp_path):
    mgr.start_session()
    mgr.append_catch("Salmon", "320")
    meta = mgr.load_sessions()[0]
    mgr.end_session()
    out = str(tmp_path / "out.csv")
    mgr.export_session(meta.id, out, "csv")
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["timestamp", "fish_name", "weight_g"]
    assert rows[1][1] == "Salmon"


def test_export_json(mgr, tmp_path):
    mgr.start_session()
    mgr.append_catch("Bass", "150")
    meta = mgr.load_sessions()[0]
    mgr.end_session()
    out = str(tmp_path / "out.json")
    mgr.export_session(meta.id, out, "json")
    data = json.loads(open(out).read())
    assert isinstance(data, list)
    assert data[0]["fish_name"] == "Bass"


def test_export_xlsx(mgr, tmp_path):
    mgr.start_session()
    mgr.append_catch("Perch", "80")
    meta = mgr.load_sessions()[0]
    mgr.end_session()
    out = str(tmp_path / "out.xlsx")
    mgr.export_session(meta.id, out, "xlsx")
    import openpyxl
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    headers = [ws.cell(1, c).value for c in range(1, 4)]
    assert headers == ["timestamp", "fish_name", "weight_g"]
    assert ws.cell(2, 2).value == "Perch"
