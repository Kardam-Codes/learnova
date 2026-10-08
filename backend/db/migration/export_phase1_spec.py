"""
File: export_phase1_spec.py
Owner: BOTH CAN ADD
Purpose: Export the versioned MongoDB design and existing HTTP contract.
What it is: An offline specification generator; it does not initialize a database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

# Embedded source references are reconstructible from their containing parent.
MAPPINGS = {
    "users": {"collection": "users"},
    "courses": {"collection": "courses", "rename": {"price": "price_paise"}},
    "course_tags": {"collection": "tags"},
    "course_tag_map": {"collection": "courses", "array": "tags", "parent": "course_id"},
    "course_attendees": {"collection": "enrollments"},
    "course_content": {"collection": "course_content"},
    "content_attachments": {"collection": "course_content", "array": "attachments", "parent": "content_id"},
    "quizzes": {"collection": "quizzes"},
    "quiz_questions": {"collection": "quizzes", "array": "questions", "parent": "quiz_id"},
    "quiz_options": {"collection": "quizzes", "array": "questions[].options", "parent": "question_id"},
    "quiz_reward_rules": {"collection": "quizzes", "array": "reward_rules", "parent": "quiz_id"},
    "quiz_attempts": {"collection": "quiz_attempts"},
    "quiz_attempt_answers": {"collection": "quiz_attempts", "array": "answers", "parent": "attempt_id"},
    "course_progress": {"collection": "course_progress"},
    "content_progress": {"collection": "content_progress"},
    "learner_points": {"collection": "learner_points"},
    "point_events": {"collection": "point_events"},
    "course_reviews": {"collection": "reviews"},
    "course_payment_orders": {"collection": "payment_orders"},
}


def object_schema(properties: dict, required: list[str]) -> dict:
    return {"bsonType": "object", "required": required,
            "properties": properties, "additionalProperties": False}


def array_schema(items: dict) -> dict:
    return {"bsonType": "array", "items": items}


def source_schema(table: str, columns: list[dict], enums: dict) -> dict:
    mapping = MAPPINGS[table]
    properties = {}
    required = []
    for column in columns:
        original = column["column_name"]
        if original == mapping.get("parent"):
            continue
        name = mapping.get("rename", {}).get(original, original)
        if original == "id" and not mapping.get("array"):
            name = "_id"
        kind = column["data_type"]
        if name == "price_paise":
            field = {"bsonType": ["int", "long"], "minimum": 0}
        elif kind == "uuid":
            field = {"bsonType": "string", "pattern": UUID_PATTERN}
        elif kind == "USER-DEFINED" and column["udt_name"] in enums:
            field = {"bsonType": "string", "enum": enums[column["udt_name"]]}
        elif kind in {"integer", "bigint", "smallint"}:
            field = {"bsonType": ["int", "long"]}
        elif kind == "numeric":
            field = {"bsonType": "double"}
        elif kind == "boolean":
            field = {"bsonType": "bool"}
        elif kind.startswith("timestamp"):
            field = {"bsonType": "date"}
        elif kind in {"text", "character varying"}:
            field = {"bsonType": "string"}
        else:
            raise ValueError(f"Unmapped source type: {table}.{original}: {kind}")
        if column["is_nullable"] == "YES":
            # Optional unique identifiers use missing instead of null.
            if original not in {"google_id", "provider_payment_id"}:
                types = field["bsonType"]
                field["bsonType"] = (types if isinstance(types, list) else [types]) + ["null"]
                if "enum" in field:
                    field["enum"] = field["enum"] + [None]
        else:
            required.append(name)
        if original in {"display_order", "max_attempts", "attempt_number", "amount_paise"}:
            field["minimum"] = 1
        if original in {"points_awarded", "points_earned", "total_points", "last_position", "completed_count", "incomplete_count"}:
            field["minimum"] = 0
        if original in {"score", "completion_percentage"}:
            field.update({"minimum": 0, "maximum": 100})
        if table == "course_reviews" and original == "rating":
            field.update({"minimum": 1, "maximum": 5})
        if table == "course_payment_orders" and original == "status":
            field["enum"] = ["created", "paid", "failed"]
        properties[name] = field
    if not mapping.get("array"):
        properties["schema_version"] = {"bsonType": "int", "enum": [1]}
        required.append("schema_version")
    return object_schema(properties, required)


def index(name: str, keys: list[tuple[str, int]], *, unique=False, partial=None) -> dict:
    result = {"name": name, "keys": [[key, direction] for key, direction in keys]}
    if unique:
        result["unique"] = True
    if partial:
        result["partialFilterExpression"] = partial
    return result


def build_spec(manifest: dict) -> dict:
    columns = {}
    for column in manifest["schema"]["columns"]:
        if column["table_name"] in MAPPINGS:
            columns.setdefault(column["table_name"], []).append(column)
    if set(columns) != set(MAPPINGS):
        raise ValueError("The baseline tables differ from the reviewed nineteen-table design.")
    enums = {}
    for row in manifest["schema"]["enums"]:
        enums.setdefault(row["typname"], []).append(row["enumlabel"])
    definitions = {table: source_schema(table, fields, enums) for table, fields in columns.items()}
    collections = {}
    for table, mapping in MAPPINGS.items():
        if "array" not in mapping:
            collections[mapping["collection"]] = {"validator": {"$jsonSchema": definitions[table]},
                                                    "validationLevel": "strict", "validationAction": "error", "indexes": []}
    def properties(collection):
        return collections[collection]["validator"]["$jsonSchema"]["properties"]
    def add_array(collection, key, definition):
        properties(collection)[key] = array_schema(definition)
        collections[collection]["validator"]["$jsonSchema"]["required"].append(key)

    # Preserve tag catalogue IDs, timestamps, unused entries, and link-row IDs.
    tag_link = definitions["course_tag_map"]
    tag_link["properties"]["name"] = {"bsonType": "string"}
    tag_link["required"].append("name")
    add_array("courses", "tags", tag_link)
    properties("tags")["normalized_name"] = {"bsonType": "string"}
    collections["tags"]["validator"]["$jsonSchema"]["required"].append("normalized_name")
    properties("courses")["currency"] = {"bsonType": "string", "enum": ["INR"]}
    collections["courses"]["validator"]["$jsonSchema"]["required"].append("currency")
    add_array("course_content", "attachments", definitions["content_attachments"])
    definitions["quiz_questions"]["properties"]["options"] = array_schema(definitions["quiz_options"])
    definitions["quiz_questions"]["required"].append("options")
    add_array("quizzes", "questions", definitions["quiz_questions"])
    add_array("quizzes", "reward_rules", definitions["quiz_reward_rules"])
    properties("quizzes")["version"] = {"bsonType": "int", "minimum": 1}
    collections["quizzes"]["validator"]["$jsonSchema"]["required"].append("version")
    add_array("quiz_attempts", "answers", definitions["quiz_attempt_answers"])
    properties("quiz_attempts").update({
        "quiz_version": {"bsonType": ["int", "null"], "minimum": 1},
        "course_id": {"bsonType": "string", "pattern": UUID_PATTERN},
        "content_id": {"bsonType": "string", "pattern": UUID_PATTERN},
        "submission_key": {"bsonType": "string", "minLength": 1, "maxLength": 128},
        "submission_fingerprint": {"bsonType": "string"},
    })
    properties("point_events")["attempt_id"] = {"bsonType": "string", "pattern": UUID_PATTERN}
    # Email stays normalized; optional provider identifiers are omitted when absent.
    properties("users")["email"]["minLength"] = 1
    for collection, field in [("users", "google_id"), ("payment_orders", "provider_payment_id")]:
        properties(collection)[field]["minLength"] = 1

    def cross_rule(collection, rule):
        original = collections[collection]["validator"]
        collections[collection]["validator"] = {"$and": [original, rule]}

    cross_rule("users", {"$or": [
        {"provider": "local", "password_hash": {"$type": "string"}},
        {"provider": "google", "google_id": {"$type": "string"}},
    ]})
    cross_rule("courses", {"$or": [
        {"access_rule": {"$ne": "payment"}}, {"price_paise": {"$gt": 0}},
    ]})
    cross_rule("course_content", {"$or": [
        {"content_type": "quiz", "content_mode": "quiz"},
        {"content_type": "lesson", "content_mode": {"$in": ["video", "document", "image"]}},
    ]})

    indexes = {
        "users": [index("uq_users_email", [("email", 1)], unique=True),
                  index("uq_users_google_id", [("google_id", 1)], unique=True,
                        partial={"google_id": {"$type": "string"}}), index("ix_users_role", [("role", 1)])],
        "tags": [index("uq_tags_normalized_name", [("normalized_name", 1)], unique=True)],
        "courses": [index("uq_courses_slug", [("slug", 1)], unique=True),
                    index("ix_courses_published_visibility", [("is_published", 1), ("visibility", 1)])],
        "course_content": [index("uq_content_course_slug", [("course_id", 1), ("slug", 1)], unique=True),
                           index("uq_content_course_order", [("course_id", 1), ("display_order", 1)], unique=True)],
        "quizzes": [index("uq_quizzes_content", [("content_id", 1)], unique=True),
                    index("ix_quizzes_course", [("course_id", 1)])],
        "enrollments": [index("uq_enrollments_course_user", [("course_id", 1), ("user_id", 1)], unique=True),
                        index("ix_enrollments_user_course", [("user_id", 1), ("course_id", 1)])],
        "course_progress": [index("uq_progress_course_user", [("course_id", 1), ("user_id", 1)], unique=True),
                            index("ix_course_progress_user", [("user_id", 1)])],
        "content_progress": [index("uq_progress_content_user", [("content_id", 1), ("user_id", 1)], unique=True),
                             index("ix_content_progress_course_user", [("course_id", 1), ("user_id", 1)])],
        "quiz_attempts": [index("uq_attempt_number", [("quiz_id", 1), ("user_id", 1), ("attempt_number", 1)], unique=True),
                          index("uq_attempt_submission", [("quiz_id", 1), ("user_id", 1), ("submission_key", 1)],
                                unique=True, partial={"submission_key": {"$type": "string"}}),
                          index("ix_attempts_user_submitted", [("user_id", 1), ("submitted_at", -1)])],
        "learner_points": [index("uq_points_user", [("user_id", 1)], unique=True)],
        "point_events": [index("uq_point_events_attempt", [("attempt_id", 1)], unique=True,
                               partial={"attempt_id": {"$type": "string"}}),
                         index("ix_point_events_user_created", [("user_id", 1), ("created_at", -1)])],
        "reviews": [index("uq_reviews_course_user", [("course_id", 1), ("user_id", 1)], unique=True),
                    index("ix_reviews_course_created", [("course_id", 1), ("created_at", -1)])],
        "payment_orders": [index("uq_provider_order", [("provider_order_id", 1)], unique=True),
                           index("uq_provider_payment", [("provider_payment_id", 1)], unique=True,
                                 partial={"provider_payment_id": {"$type": "string"}}),
                           index("ix_payments_user_course_created", [("user_id", 1), ("course_id", 1), ("created_at", -1)])],
    }
    for name, definitions_list in indexes.items():
        collections[name]["indexes"] = definitions_list

    date = {"bsonType": "date"}
    integer = {"bsonType": "int", "minimum": 0}
    version = {"bsonType": "int", "enum": [1]}
    uuid = {"bsonType": "string", "pattern": UUID_PATTERN}
    operational = {
        "app_metadata": object_schema({
            "_id": {"bsonType": "string", "enum": ["auth_bootstrap"]},
            "schema_version": version, "claimed": {"bsonType": "bool"},
            "administrator_id": {"bsonType": ["string", "null"], "pattern": UUID_PATTERN},
            "updated_at": date,
        }, ["_id", "schema_version", "claimed", "administrator_id", "updated_at"]),
        "schema_migrations": object_schema({
            "_id": {"bsonType": "string"}, "version": {"bsonType": "int", "minimum": 1},
            "checksum": {"bsonType": "string"}, "applied_at": date,
        }, ["_id", "version", "checksum", "applied_at"]),
        "quiz_attempt_counters": object_schema({
            "_id": uuid, "schema_version": version, "quiz_id": uuid, "user_id": uuid,
            "attempts_used": integer, "updated_at": date,
        }, ["_id", "schema_version", "quiz_id", "user_id", "attempts_used", "updated_at"]),
    }
    for name, definition in operational.items():
        collections[name] = {"validator": {"$jsonSchema": definition},
                             "validationLevel": "strict", "validationAction": "error", "indexes": []}
    collections["quiz_attempt_counters"]["indexes"] = [
        index("uq_counter_quiz_user", [("quiz_id", 1), ("user_id", 1)], unique=True)]

    field_mapping = {}
    for table, mapping in MAPPINGS.items():
        target = mapping["collection"]
        prefix = target + ("." + mapping["array"] + "[]" if mapping.get("array") else "")
        fields = {}
        for column in columns[table]:
            name = column["column_name"]
            if name == mapping.get("parent"):
                fields[name] = "reconstructed from enclosing parent id"
            else:
                destination = mapping.get("rename", {}).get(name, name)
                if name == "id" and not mapping.get("array"):
                    destination = "_id"
                fields[name] = prefix + "." + destination
        field_mapping[table] = {**mapping, "fields": fields}
    return {
        "spec_version": 1, "status": "phase_1_design_live_mongodb_validation_pending",
        "source_snapshot": manifest["created_at_utc"],
        "retention": "Preserve all existing records and access, confirmed by user.",
        "domain_collections": sorted(indexes),
        "operational_collections": sorted(operational),
        "source_mapping": field_mapping,
        "collections": collections,
        "notes": [
            "Do not apply this specification to the existing MongoDB service during Phase 1.",
            "Nullable google_id and provider_payment_id are omitted when absent; other SQL nullable fields may be null.",
            "Prices are converted with decimal arithmetic into integer paise; API price remains unchanged.",
            "Empty quizzes are preserved. Submission readiness and distinct embedded IDs require service checks.",
            "No new arbitrary quiz/attachment count limits are introduced; enforce MongoDB BSON document size before writes.",
            "Legacy quiz versions are unknown; retain null rather than inventing a historical version.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-manifest", required=True, type=Path)
    args = parser.parse_args()
    manifest_path = args.baseline_manifest.resolve()
    if not manifest_path.is_relative_to((ROOT / ".local" / "migration-baseline").resolve()):
        parser.error("Use a captured private baseline manifest in this workspace.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    spec = build_spec(manifest)
    output = ROOT / "docs" / "migration" / "phase1"
    output.mkdir(parents=True, exist_ok=True)
    spec_path = output / "mongodb-schema-v1.json"
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    from backend.main import app
    openapi = app.openapi()
    (output / "postgres-openapi-baseline.json").write_text(json.dumps(openapi, indent=2) + "\n", encoding="utf-8")
    operations = []
    for path, methods in openapi["paths"].items():
        for method, operation in methods.items():
            if method in {"get", "post", "put", "patch", "delete", "options", "head"}:
                operations.append({"method": method.upper(), "path": path,
                                   "operation_id": operation["operationId"],
                                   "documented_responses": sorted(operation["responses"]),
                                   "parameters": operation.get("parameters", []),
                                   "request_body": operation.get("requestBody")})
    (output / "endpoint-inventory.json").write_text(json.dumps(operations, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_directory": str(output), "source_tables": len(spec["source_mapping"]),
                      "domain_collections": len(spec["domain_collections"]),
                      "operational_collections": len(spec["operational_collections"]),
                      "api_operations": len(operations),
                      "schema_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
