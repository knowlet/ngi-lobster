from lobster_core import ConfidenceLevel, EvidenceRecord, Provenance, to_plain_data


def test_evidence_record_roundtrip_shape():
    record = EvidenceRecord(
        schema_version="v1",
        record_id="ev_1",
        source_id="gooaye",
        source_type="channel",
        created_at_utc="2026-04-13T00:00:00Z",
        provenance=Provenance(source_urls=["https://t.me/Gooaye/6060"]),
        metadata={"confidence": ConfidenceLevel.MEDIUM},
    )
    data = to_plain_data(record)
    assert data["record_id"] == "ev_1"
    assert data["provenance"]["source_urls"][0] == "https://t.me/Gooaye/6060"
    assert data["metadata"]["confidence"] == "medium"

