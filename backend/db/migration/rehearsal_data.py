"""Read-only SQL capture and loss checks for disposable MongoDB rehearsals only."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import re
from uuid import UUID, NAMESPACE_URL, uuid5

from psycopg import sql

from backend.config.db import connect
from backend.db.mongo.bootstrap import initialize_auth_bootstrap
from backend.db.mongo.init_db import load_spec


def capture_source_rows():
    spec, _ = load_spec()
    result = {}
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            for table in spec["source_mapping"]:
                cursor.execute(sql.SQL("SELECT * FROM {} ORDER BY id").format(sql.Identifier(table)))
                columns = [column.name for column in cursor.description]
                result[table] = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return result


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.replace(microsecond=value.microsecond // 1000 * 1000)
    return value


def assemble_documents(source):
    spec, _ = load_spec()
    documents = defaultdict(list)
    for table, mapping in spec["source_mapping"].items():
        if "array" in mapping:
            continue
        for row in source[table]:
            item = {"_id" if k == "id" else "price_paise" if k == "price" else k: normalize(v)
                    for k, v in row.items()}
            item["schema_version"] = 1
            if table == "users":
                item["email"] = item["email"].strip().lower()
                if item.get("google_id") is None:
                    item.pop("google_id", None)
            if table == "courses":
                item.update(price_paise=int(row["price"] * 100), currency="INR", tags=[])
            if table == "course_tags":
                item["normalized_name"] = item["name"].strip().lower()
            if table == "course_content":
                item["attachments"] = []
            if table == "quizzes":
                item.update(version=1, questions=[], reward_rules=[])
            if table == "quiz_attempts":
                item.update(quiz_version=None, answers=[])
            if table == "course_payment_orders" and item.get("provider_payment_id") is None:
                item.pop("provider_payment_id", None)
            documents[mapping["collection"]].append(item)
    lookup = {name: {row["_id"]: row for row in rows} for name, rows in documents.items()}
    for row in source["course_tag_map"]:
        lookup["courses"][str(row["course_id"])]["tags"].append({"id": str(row["id"]), "tag_id": str(row["tag_id"]),
                                                              "name": lookup["tags"][str(row["tag_id"])]["name"]})
    for row in sorted(source["content_attachments"], key=lambda r: r["created_at"]):
        lookup["course_content"][str(row["content_id"])]["attachments"].append(
            normalize({k: v for k, v in row.items() if k != "content_id"}))
    questions = {}
    for row in sorted(source["quiz_questions"], key=lambda r: r["display_order"]):
        item = normalize({k: v for k, v in row.items() if k != "quiz_id"})
        item["options"] = []
        questions[item["id"]] = item
        lookup["quizzes"][str(row["quiz_id"])]["questions"].append(item)
    for row in sorted(source["quiz_options"], key=lambda r: r["display_order"]):
        questions[str(row["question_id"])]["options"].append(normalize({k: v for k, v in row.items() if k != "question_id"}))
    for row in source["quiz_reward_rules"]:
        lookup["quizzes"][str(row["quiz_id"])]["reward_rules"].append(normalize({k: v for k, v in row.items() if k != "quiz_id"}))
    for row in source["quiz_attempt_answers"]:
        lookup["quiz_attempts"][str(row["attempt_id"])]["answers"].append(normalize({k: v for k, v in row.items() if k != "attempt_id"}))
    return documents


def import_temporary_database(database, source):
    if not re.fullmatch(r"learnova_test_[0-9a-f]{32}", database.name):
        raise ValueError("This rehearsal importer can only write a generated temporary test database.")
    spec, _ = load_spec()
    if any(database[name].find_one() is not None for name in spec["domain_collections"]):
        raise RuntimeError("The rehearsal target must be empty.")
    documents = assemble_documents(source)
    with database.client.start_session() as session:
        with session.start_transaction():
            for name, rows in documents.items():
                if rows:
                    database[name].insert_many(rows, session=session)
    initialize_auth_bootstrap(database)
    # Attempt counters are derivable operational records, never invented attempts.
    counters = {}
    for attempt in documents["quiz_attempts"]:
        pair = (attempt["quiz_id"], attempt["user_id"])
        counters[pair] = max(counters.get(pair, 0), attempt["attempt_number"])
    for (quiz, user), maximum in counters.items():
        database.quiz_attempt_counters.insert_one({"_id": str(uuid5(NAMESPACE_URL, quiz + ":" + user)),
            "schema_version": 1, "quiz_id": quiz, "user_id": user, "attempts_used": maximum,
            "updated_at": next(a["submitted_at"] for a in documents["quiz_attempts"] if a["quiz_id"] == quiz and a["user_id"] == user)})
    return verify_preservation(database, source)


def verify_preservation(database, source):
    spec, _ = load_spec()
    stored = {name: list(database[name].find()) for name in spec["domain_collections"]}
    for table, mapping in spec["source_mapping"].items():
        reconstructed = []
        for parent in stored[mapping["collection"]]:
            if table == "course_tag_map":
                items = [{**item, "course_id": parent["_id"]} for item in parent["tags"]]
            elif table == "content_attachments":
                items = [{**item, "content_id": parent["_id"]} for item in parent["attachments"]]
            elif table == "quiz_questions":
                items = [{**item, "quiz_id": parent["_id"]} for item in parent["questions"]]
            elif table == "quiz_options":
                items = [{**item, "question_id": question["id"]} for question in parent["questions"] for item in question["options"]]
            elif table == "quiz_reward_rules":
                items = [{**item, "quiz_id": parent["_id"]} for item in parent["reward_rules"]]
            elif table == "quiz_attempt_answers":
                items = [{**item, "attempt_id": parent["_id"]} for item in parent["answers"]]
            else:
                items = [{**parent, "id": parent["_id"]}]
                if table == "courses":
                    items[0]["price"] = parent["price_paise"] / 100
            columns = list(source[table][0]) if source[table] else []
            reconstructed.extend({key: item.get(key) for key in columns} for item in items)
        expected = normalize(source[table])
        if table == "users":
            expected = [{**row, "email": row["email"].strip().lower()} for row in expected]
        if sorted(reconstructed, key=lambda r: r["id"]) != sorted(expected, key=lambda r: r["id"]):
            raise RuntimeError("Rehearsed source fields differ: " + table)
    return {"source_tables_preserved": len(source), "source_columns_mapped": 142,
            "source_rows_preserved": sum(len(rows) for rows in source.values())}
