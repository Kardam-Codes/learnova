"""Initialize the reviewed MongoDB application schema without PostgreSQL dependencies."""
import argparse
import json
from backend.config.mongo import create_mongo_client, get_mongo_settings
from backend.db.mongo.init_db import initialize_database
from backend.db.mongo.quiz_schema import upgrade_quiz_receipts
from backend.db.mongo.payment_schema import upgrade_payment_intents
from backend.db.mongo.bootstrap import initialize_auth_bootstrap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", required=True)
    parser.parse_args()
    settings = get_mongo_settings()
    if settings is None:
        raise SystemExit("Configure MONGODB_URI and MONGODB_DB first.")
    with create_mongo_client(settings) as client:
        database = client[settings.database]
        initialize_database(database, application=True)
        upgrade_quiz_receipts(database, application=True)
        result = upgrade_payment_intents(database, application=True)
        initialize_auth_bootstrap(database)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
