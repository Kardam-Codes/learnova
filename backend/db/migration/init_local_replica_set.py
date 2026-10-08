"""Initiate the backed-up local service once and wait for a writable primary."""
import json
import time

from pymongo import MongoClient
from pymongo.errors import OperationFailure


def main():
    with MongoClient("mongodb://localhost:27017/?directConnection=true", serverSelectionTimeoutMS=5000) as client:
        try:
            config = client.admin.command("replSetGetConfig")["config"]
            if config["_id"] != "learnova-rs" or len(config["members"]) != 1 or config["members"][0]["host"] != "localhost:27017":
                raise RuntimeError("Existing replica-set configuration differs; manual review required.")
        except OperationFailure as error:
            if error.code != 94:  # NotYetInitialized; never replace an existing configuration.
                raise
            client.admin.command({"replSetInitiate": {"_id": "learnova-rs",
                "members": [{"_id": 0, "host": "localhost:27017"}]}})
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            hello = client.admin.command("hello")
            if hello.get("setName") == "learnova-rs" and hello.get("isWritablePrimary"):
                print(json.dumps({"replica_set": "learnova-rs", "writable_primary": True,
                                  "members": 1, "high_availability": False}))
                return
            time.sleep(0.25)
        raise RuntimeError("Replica set did not elect a writable primary within 40 seconds.")


if __name__ == "__main__":
    main()
