from gridpact import db, ledger


def fresh(tmp_path):
    return db.connect(tmp_path / "test.db")


def test_chain_links_and_verifies(tmp_path):
    conn = fresh(tmp_path)
    rows = [ledger.append(conn, "A", "register", {"n": i}) for i in range(5)]
    assert [r["seq"] for r in rows] == [1, 2, 3, 4, 5]
    assert rows[0]["prev_hash"] == ledger.GENESIS
    assert all(rows[i]["prev_hash"] == rows[i - 1]["hash"] for i in range(1, 5))
    assert ledger.verify_chain(conn) is None
    assert [e["payload"]["n"] for e in ledger.entries(conn, since_seq=3)] == [3, 4]


def test_tampering_entry_3_breaks_chain_at_3(tmp_path):
    conn = fresh(tmp_path)
    for i in range(5):
        ledger.append(conn, "A", "trade", {"kwh": 100 + i})
    conn.execute("UPDATE ledger SET payload_json = ? WHERE seq = 3", ('{"kwh":999}',))
    assert ledger.verify_chain(conn) == 3


def test_tampering_hash_breaks_next_link(tmp_path):
    conn = fresh(tmp_path)
    for i in range(3):
        ledger.append(conn, "A", "trade", {"i": i})
    # Rewrite entry 2's hash: entry 2 itself fails (hash no longer matches its content).
    conn.execute("UPDATE ledger SET hash = ? WHERE seq = 2", ("f" * 64,))
    assert ledger.verify_chain(conn) == 2
