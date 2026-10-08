"""Enrollment-first reporting; content positions are legacy minutes, not elapsed time.

Missing progress renders as yet_to_start, but (like SQL COUNT FILTER) does not
contribute to a status summary or match a status filter. Summary covers all rows.
English name ordering matches the preserved English_India PostgreSQL baseline;
UUID joins retain simple collation and their existing indexes.
"""
from fastapi import HTTPException
from pymongo.collation import Collation
from backend.db.mongo.transactions import run_transaction


def report_pipeline():
    pipeline = []
    for collection, local, alias in (
        ("courses", "course_id", "course"), ("users", "user_id", "user"),
    ):
        pipeline.extend([
            {"$lookup": {"from": collection, "localField": local,
                          "foreignField": "_id", "as": alias}},
            {"$unwind": "$" + alias},
        ])
    for collection, alias, stages in (
        ("course_progress", "progress", []),
        ("content_progress", "positions", [
            {"$group": {"_id": None, "minutes": {"$sum": "$last_position"}}}]),
    ):
        pipeline.append({"$lookup": {
            "from": collection, "let": {"course": "$course_id", "user": "$user_id"},
            "pipeline": [{"$match": {"$expr": {"$and": [
                {"$eq": ["$course_id", "$$course"]},
                {"$eq": ["$user_id", "$$user"]},
            ]}}}, *stages], "as": alias,
        }})
    pipeline.extend([
        {"$set": {"progress": {"$arrayElemAt": ["$progress", 0]},
                  "positions": {"$arrayElemAt": ["$positions", 0]}}},
        {"$project": {"courseId": "$course_id", "participantId": "$user_id",
                      "courseName": "$course.title", "participantName": "$user.name",
                      "enrolledDate": "$enrolled_at", "progress": 1, "positions": 1}},
    ])
    return pipeline


def course_progress_report(database, status_filter=None):
    selected = status_filter.lower() if status_filter else None
    statuses = ("yet_to_start", "in_progress", "completed")
    if selected and selected not in statuses:
        raise HTTPException(400, "Invalid status filter.")
    # Keep UUID joins on simple collation so their existing indexes remain usable.
    # Two batched name sorts reproduce English source ordering without applying
    # linguistic collation to every foreign-key lookup.
    def snapshot(session):
        records = list(database.enrollments.aggregate(report_pipeline(), session=session))
        if not records:
            return records
        ranks = []
        for collection, field in (("courses", "title"), ("users", "name")):
            rank = {}
            for item in database[collection].find({}, {field: 1}, session=session).sort(field, 1).collation(
                    Collation(locale="en", strength=3)):
                rank.setdefault(item[field], len(rank))
            ranks.append(rank)
        records.sort(key=lambda row: (ranks[0][row["courseName"]], ranks[1][row["participantName"]]))
        return records
    records = run_transaction(database, snapshot)
    counts = {key: 0 for key in statuses}
    rows = []
    for record in records:
        progress = record.get("progress") or {}
        raw_status = progress.get("status")
        if raw_status in counts:
            counts[raw_status] += 1
        if selected and raw_status != selected:
            continue
        minutes = int((record.get("positions") or {}).get("minutes") or 0)
        def date(value):
            return value.isoformat() if value else None
        rows.append({
            "id": len(rows) + 1, "courseId": record["courseId"],
            "courseName": record["courseName"], "participantId": record["participantId"],
            "participantName": record["participantName"],
            "enrolledDate": date(record.get("enrolledDate")),
            "startDate": date(progress.get("started_at")),
            "completedDate": date(progress.get("completed_at")),
            "timeSpent": f"{minutes // 60}:{minutes % 60:02d}",
            "completionPercentage": f"{float(progress.get('completion_percentage') or 0):.0f}%",
            "status": raw_status or "yet_to_start",
        })
    return {"summary": [
        {"id": "participants", "label": "Total Participants", "value": len(records)},
        *[{"id": key.replace("_", "-"), "label": label, "value": counts[key]}
          for key, label in zip(statuses, ("Yet to Start", "In Progress", "Completed"))],
    ], "rows": rows, "activeFilter": selected}
