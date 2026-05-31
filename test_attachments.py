#!/usr/bin/env python3
"""Test script to analyze MessageV1 attachments serialization and parquet round-trip."""

import json
import tempfile
from pathlib import Path

import pandas as pd

from src.llm_tracer.schema.v1 import AttachmentV1, MessageV1


def main():
    print("=" * 80)
    print("Test: MessageV1 Attachments Serialization and Parquet Round-trip")
    print("=" * 80)

    # 1. Create a MessageV1 object with attachments
    print("\n1. Creating MessageV1 object with attachments...")
    attachment = AttachmentV1(
        name="example.txt", mime_type="text/plain", content="Hello, world!"
    )

    message = MessageV1(
        role="user",
        content="Here's a message with an attachment",
        attachments=[attachment],
    )
    print(f"   Created: {message}")

    # 2. Serialize with model_dump(mode="json")
    print("\n2. Serializing with model_dump(mode='json')...")
    serialized = message.model_dump(mode="json")
    print(f"   Serialized data: {serialized}")
    print(f"   Type of attachments field: {type(serialized['attachments'])}")
    print(f"   Content of attachments: {serialized['attachments']}")

    # 3. Create a DataFrame with this data
    print("\n3. Creating DataFrame with serialized data...")
    df = pd.DataFrame([serialized])
    print(f"   DataFrame shape: {df.shape}")
    print(f"   DataFrame dtypes:\n{df.dtypes}")
    print(f"   DataFrame head:\n{df}")

    # 4. Write to parquet file
    print("\n4. Writing to parquet file...")
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
        parquet_path = Path(f.name)

    df.to_parquet(parquet_path, index=False)
    print(f"   Wrote to: {parquet_path}")

    # 5. Read it back
    print("\n5. Reading back from parquet file...")
    df_read = pd.read_parquet(parquet_path)
    print(f"   DataFrame shape: {df_read.shape}")
    print(f"   DataFrame dtypes after reading:\n{df_read.dtypes}")
    print(f"   DataFrame head:\n{df_read}")

    # 6. Try to JSON-serialize it
    print("\n6. Attempting JSON serialization of read data...")
    try:
        # Try converting to dict first
        data_dict = df_read.to_dict(orient="records")[0]
        print(f"   Converted to dict: {data_dict}")
        print(f"   Type of attachments in dict: {type(data_dict['attachments'])}")

        # Try JSON serialization
        json_str = json.dumps(data_dict, default=str)
        print("   ✓ JSON serialization successful!")
        print(f"   JSON string (first 200 chars): {json_str[:200]}...")
    except Exception as e:
        print("   ✗ JSON serialization failed!")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {e}")

    # 7. Detailed type analysis
    print("\n7. Detailed type analysis of attachments field...")
    attachments_from_read = df_read["attachments"].iloc[0]
    print(f"   Type: {type(attachments_from_read)}")
    print(f"   Value: {attachments_from_read}")
    print(f"   Repr: {repr(attachments_from_read)}")

    # Check what's inside
    if isinstance(attachments_from_read, list):
        if len(attachments_from_read) > 0:
            print(f"   First element type: {type(attachments_from_read[0])}")
            print(f"   First element: {attachments_from_read[0]}")

    # Clean up
    parquet_path.unlink()
    print(f"\n   Cleaned up parquet file: {parquet_path}")

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
