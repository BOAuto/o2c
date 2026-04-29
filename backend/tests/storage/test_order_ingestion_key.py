from app.storage.order_ingestion import build_order_ingestion_object_key


def test_order_ingestion_key_shape() -> None:
    key = build_order_ingestion_object_key(
        year=2026, month=4, storage_type="POattachments", file_name="doc.pdf"
    )
    assert key == "2026/04/OrderIngestion/POattachments/doc.pdf"
