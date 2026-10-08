"""Quiz input, scoring, rewards, and counters shared by the transactional writer."""
import hashlib
import json

from fastapi import HTTPException
from pymongo import ReturnDocument


def normalize_answers(answers):
    if not isinstance(answers, list):
        raise HTTPException(400, "All quiz questions must be answered.")
    result = {}
    for answer in answers:
        if not isinstance(answer, dict) or not isinstance(answer.get("questionId"), str):
            raise HTTPException(400, "One or more quiz answers are invalid.")
        question = answer["questionId"]
        indexes = answer.get("selectedOptionIndexes")
        if (question in result or not isinstance(indexes, list) or not indexes
                or any(type(index) is not int or index < 0 for index in indexes)
                or len(indexes) != len(set(indexes))):
            raise HTTPException(400, "One or more quiz answers are invalid or repeated.")
        result[question] = sorted(indexes)
    return dict(sorted(result.items()))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def quiz_fingerprint(quiz):
    return digest({"max_attempts": quiz["max_attempts"], "questions": [
        {"id": question["id"], "prompt": question["question_text"], "order": question["display_order"],
         "options": sorted(question["options"], key=lambda option: option["display_order"])}
        for question in sorted(quiz["questions"], key=lambda question: question["display_order"])],
        "reward_rules": sorted(quiz["reward_rules"], key=lambda rule: rule["attempt_number"])})


def score_answers(quiz, submitted, answer_ids):
    questions = sorted(quiz["questions"], key=lambda question: question["display_order"])
    if set(submitted) != {question["id"] for question in questions}:
        raise HTTPException(400, "All quiz questions must be answered with valid question identities.")
    rows, correct = [], 0
    for question in questions:
        options = sorted(question["options"], key=lambda option: option["display_order"])
        selected = submitted[question["id"]]
        if any(index >= len(options) for index in selected):
            raise HTTPException(400, "One or more quiz answers are invalid.")
        expected = {index for index, option in enumerate(options) if option["is_correct"]}
        is_correct = set(selected) == expected
        correct += int(is_correct)
        for index in selected:
            rows.append({"id": answer_ids[(question["id"], index)], "question_id": question["id"],
                         "selected_option_id": options[index]["id"], "is_correct": is_correct})
    return float(round(correct / max(len(questions), 1) * 100, 2)), rows


def reward_for_attempt(quiz, number):
    rules = {rule["attempt_number"]: rule["points_awarded"] for rule in quiz["reward_rules"]}
    return int(rules.get(number, rules[max(rules)] if rules else 0))


def badge_for_points(total):
    for threshold, badge in ((101, "Master"), (81, "Expert"), (61, "Specialist"),
                             (41, "Achiever"), (21, "Explorer")):
        if total >= threshold:
            return badge
    return "Newbie"


def allocate_attempt(database, quiz, user_id, session, *, stamp, identifier):
    pair = {"quiz_id": quiz["_id"], "user_id": user_id}
    # A missing/stale counter must never reset existing history, including gaps.
    latest = database.quiz_attempts.find_one(pair, {"attempt_number": 1}, sort=[("attempt_number", -1)], session=session)
    maximum = latest["attempt_number"] if latest else 0
    counter = database.quiz_attempt_counters.find_one(pair, session=session)
    if counter is None:
        database.quiz_attempt_counters.insert_one({"_id": identifier, "schema_version": 1, **pair,
            "attempts_used": maximum, "updated_at": stamp}, session=session)
    elif counter["attempts_used"] < maximum:
        database.quiz_attempt_counters.update_one({"_id": counter["_id"]},
            {"$max": {"attempts_used": maximum}, "$set": {"updated_at": stamp}}, session=session)
    updated = database.quiz_attempt_counters.find_one_and_update({**pair, "attempts_used": {"$lt": quiz["max_attempts"]}},
        {"$inc": {"attempts_used": 1}, "$set": {"updated_at": stamp}},
        return_document=ReturnDocument.AFTER, session=session)
    if updated is None:
        raise HTTPException(400, "Maximum quiz attempts reached.")
    return updated["attempts_used"]


def award_points(database, user_id, points, session, *, stamp, identifier):
    # Shared balance write forces transactions from different courses to retry a
    # conflicting snapshot and calculate the badge from the resulting total.
    previous = database.learner_points.find_one({"user_id": user_id}, session=session)
    total = (previous["total_points"] if previous else 0) + points
    result = {"total_points": total, "current_badge": badge_for_points(total), "updated_at": stamp}
    database.learner_points.update_one({"user_id": user_id}, {"$set": result,
        "$setOnInsert": {"_id": identifier, "schema_version": 1}}, upsert=True, session=session)
    return result
