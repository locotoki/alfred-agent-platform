from sqlalchemy import inspect

from agent_core.db.session import engine

def test_tables_present():
    insp = inspect(engine)
    assert "document_chunks" in insp.get_table_names()
