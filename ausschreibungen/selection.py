"""Konsolidierte Berichtsauswahl mit Verweisen auf unveränderte Auswertungen."""

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from html import escape
from typing import Any

Data = dict[str, Any]
UnitRef = tuple[str, int]
ORDER = "Offene Frist zuerst, dann belegte Passung und nächste eindeutige Einreichungsfrist."


def reference(ref: UnitRef) -> Data:
    return {"publication_number": ref[0], "unit_index": ref[1]}


def only(values: list[str]) -> str | None:
    return values[0] if len(values) == 1 and values[0] else None


def notice_identity(doc: Data) -> str | None:
    identifier = only(doc["metadata"]["notice_ids"])
    version = only(doc["metadata"]["versions"])
    return f"{identifier.lower()}-{version}" if identifier and version else None


def source(doc: Data, records: list[Data]) -> Data:
    return {
        "publication_number": doc["publication_number"],
        "evidence": [
            {"path": r["path"], "quote": r["value"], "lot_id": r["lot_id"]} for r in records
        ],
    }


def identification(doc: Data, lot: str | None = None) -> Data:
    return source(
        doc,
        [
            r
            for r in doc["records"]
            if r["path"].count("/") == 2
            and r["path"].rsplit("/", 1)[-1]
            in {"cbc:ID[1]", "cbc:VersionID[1]", "cbc:ContractFolderID[1]"}
            or (
                lot
                and r["lot_id"] == lot
                and r["path"].count("/") == 3
                and r["path"].endswith("/cbc:ID[1]")
            )
        ],
    )


def change_records(doc: Data) -> list[Data]:
    return [r for r in doc["records"] if "/efac:Changes[" in r["path"]]


def normalized_target(identifier: str) -> str:
    if re.fullmatch(r"[0-9]+-[0-9]{4}", identifier):
        serial, year = identifier.split("-")
        return f"{serial.lstrip('0') or '0'}-{year}"
    return identifier.lower()


def find_predecessors(
    docs: dict[str, Data],
    targets: dict[str, set[str]],
    notes: dict[str, list[Data]],
    disputed: set[str],
) -> dict[str, str]:
    predecessors: dict[str, str] = {}
    successors: dict[str, list[str]] = defaultdict(list)
    for number, doc in docs.items():
        records = change_records(doc)
        if not records:
            continue
        refs = [
            normalized_target(r["value"])
            for r in records
            if re.search(r"/efbc:ChangedNoticeIdentifier\[\d+\]$", r["path"])
        ]
        matches = {n for target in refs for n in targets.get(target, ())}
        other = docs[next(iter(matches))] if len(refs) == len(matches) == 1 else None
        procedure = doc["metadata"]["procedure_ids"]
        if (
            other is None
            or other is doc
            or other["notice_type"] != doc["notice_type"]
            or (
                procedure
                and other["metadata"]["procedure_ids"]
                and procedure != other["metadata"]["procedure_ids"]
            )
        ):
            point = {
                "reason": "Früherer Stand der Berichtigung im Lauf nicht eindeutig zugeordnet.",
                "sources": [
                    source(doc, records),
                    *(identification(docs[n]) for n in sorted(matches)),
                ],
            }
            notes[number].append(point)
            for match in matches - {number}:
                notes[match].append(point)
            disputed.update(matches)
            if matches or len(refs) != 1:
                disputed.add(number)
            continue
        parent = other["publication_number"]
        predecessors[number] = parent
        successors[parent].append(number)

    # Eine eindeutige Kette hat einen Anfang und höchstens einen Nachfolger je Stand.
    reachable = set()
    for number in docs.keys() - predecessors.keys():
        while number not in reachable:
            reachable.add(number)
            children = successors.get(number, [])
            if len(children) != 1:
                break
            number = children[0]
    for child, parent in list(predecessors.items()):
        if child not in reachable:
            point = {
                "reason": "Widersprüchliche Berichtigungskette (Verzweigung oder Kreis).",
                "sources": [
                    source(docs[child], change_records(docs[child])),
                    identification(docs[parent]),
                ],
            }
            notes[child].append(point)
            notes[parent].append(point)
            disputed.update((child, parent))
            del predecessors[child]
    return predecessors


def scopes(doc: Data) -> dict[str | None, int]:
    lots = doc["metadata"]["lot_ids"]
    return {
        lot: index
        for index, unit in enumerate(doc["units"])
        if ((lot := unit["lot_id"]) is None and not lots)
        or (lot is not None and not lot.startswith("unresolved:") and lots.count(lot) == 1)
    }


def verified_fit(unit: Data) -> Data:
    fit = unit["fit"]
    if fit["status"] in {"passend", "unpassend"} and not (
        fit.get("method") == "ai_verified" and fit.get("evidence")
    ):
        return {**fit, "status": "unklar", "reason": "Keine bestätigte Passungseinschätzung."}
    return fit


def participation_terms(unit: Data) -> set[tuple[str, datetime]]:
    paths = {e["path"] for e in unit["participation"].get("evidence", [])}
    return {
        (d["kind"], datetime.fromisoformat(d["berlin"]))
        for d in unit["fields"]["deadlines"]["values"]
        if d["berlin"] and any(e["path"] in paths for e in d["evidence"])
    }


def priority(entry: Data, unit: Data) -> tuple[bool, bool, datetime, str, int]:
    opened = entry["participation"]["status"] == "Frist offen"
    deadlines = participation_terms(unit) if opened else set()
    return (
        not opened,
        entry["fit"]["status"] != "passend",
        min((due for _, due in deadlines), default=datetime.max.replace(tzinfo=UTC)),
        entry["publication_number"],
        entry["unit_index"],
    )


def additional_duplicate_checkpoints(
    index: int, aliases: list[str], copies: list[Data]
) -> list[Data]:
    points: dict[str, Data] = {}
    for number, copy in zip(aliases[1:], copies[1:], strict=True):
        for point in copy["checkpoints"]:
            if point.get("method") != "ai_verified" or point in copies[0]["checkpoints"]:
                continue
            reason = point["reason"]
            additional = points.setdefault(reason, {"reason": reason, "sources": []})
            origin = {**reference((number, index)), "evidence": point["evidence"]}
            if origin not in additional["sources"]:
                additional["sources"].append(origin)
    return list(points.values())


def select_results(research: Data, documents: list[Data], limit: int) -> Data:
    candidates = {n["publication_number"]: n for n in research["notices"]}
    docs: dict[str, Data] = {}
    aliases: dict[str, list[str]] = defaultdict(list)
    duplicate_keys: dict[tuple[str, str], str] = {}
    targets: dict[str, set[str]] = defaultdict(set)
    notes: dict[str, list[Data]] = defaultdict(list)
    disputed: set[str] = set()
    ordered = sorted(
        (d for d in documents if d.get("units") and d["status"] != "error"),
        key=lambda d: (d["status"] != "complete", d["publication_number"]),
    )
    for doc in ordered:
        number = doc["publication_number"]
        identity = notice_identity(doc)
        content_hash = doc.get("content_sha256")
        primary = (
            duplicate_keys.setdefault((identity, content_hash), number)
            if identity and content_hash
            else number
        )
        aliases[primary].append(number)
        targets[number].add(primary)
        if identity:
            targets[identity].add(primary)
        if primary == number:
            docs[number] = doc

    for identity in {notice_identity(d) for d in docs.values()} - {None}:
        matches = targets[identity]
        if len(matches) > 1:
            point = {
                "reason": "Widersprüchliche Dokumente mit gleicher "
                "Bekanntmachungskennung und Version.",
                "sources": [identification(docs[n]) for n in sorted(matches)],
            }
            disputed.update(matches)
            for n in matches:
                notes[n].append(point)

    predecessors = find_predecessors(docs, targets, notes, disputed)
    unit_predecessors: dict[UnitRef, UnitRef] = {}
    standalone_old: set[UnitRef] = set()
    for number, parent in predecessors.items():
        current, previous = scopes(docs[number]), scopes(docs[parent])
        for lot in current.keys() & previous.keys():
            unit_predecessors[number, current[lot]] = (parent, previous[lot])
        if len(current.keys() & previous.keys()) != max(
            len(docs[number]["units"]), len(docs[parent]["units"])
        ):
            point = {
                "reason": "Los oder Verfahren in den Ständen nicht eindeutig zugeordnet.",
                "sources": [
                    source(docs[number], change_records(docs[number])),
                    identification(docs[parent]),
                ],
            }
            notes[number].append(point)
            notes[parent].append(point)
            linked = {(parent, previous[lot]) for lot in current.keys() & previous.keys()}
            standalone_old.update(
                (parent, i) for i in range(len(docs[parent]["units"])) if (parent, i) not in linked
            )

    all_docs = {d["publication_number"]: d for d in ordered}
    superseded = set(unit_predecessors.values())
    entries = []
    possible_links: dict[tuple[str, str, str | None], list[Data]] = defaultdict(list)
    for number, doc in docs.items():
        lot_indexes = scopes(doc)
        procedure = only(doc["metadata"]["procedure_ids"])
        for index, unit in enumerate(doc["units"]):
            current_ref = (number, index)
            if current_ref in superseded:
                continue
            history = [current_ref]
            while history[-1] in unit_predecessors:
                history.append(unit_predecessors[history[-1]])
            stages = []
            for ref in reversed(history):
                stage = reference(ref)
                stage["ted_occurrences"] = [
                    {
                        "publication_number": n,
                        "search_groups": candidates[n].get("matched_queries", []),
                        "occurrence_count": len(candidates[n].get("occurrences", [])),
                    }
                    for n in aliases[ref[0]]
                ]
                if len(aliases[ref[0]]) > 1:
                    stage["duplicate_reason"] = (
                        "Gleiche Bekanntmachungskennung, Version und XML-Inhalt."
                    )
                elif stage["ted_occurrences"][0]["occurrence_count"] > 1:
                    stage["duplicate_reason"] = "Gleiche TED-Veröffentlichungsnummer."
                if ref in unit_predecessors:
                    stage["change_sources"] = [
                        source(docs[ref[0]], change_records(docs[ref[0]])),
                        identification(docs[unit_predecessors[ref][0]], unit["lot_id"]),
                    ]
                stages.append(stage)
            checkpoints = [point for n, _ in history for point in notes[n]]
            fit = verified_fit(unit)
            participation = unit["participation"]
            copies = [all_docs[n]["units"][index] for n in aliases[number]]
            checkpoints.extend(additional_duplicate_checkpoints(index, aliases[number], copies))
            if len({verified_fit(u)["status"] for u in copies}) > 1:
                reason = "Auswertungen der Dubletten widersprechen sich bei der Passung."
                fit = {"status": "unklar", "reason": reason, "evidence": []}
                checkpoints.append(
                    {
                        "reason": reason,
                        "sources": [
                            {"publication_number": n, "evidence": u["fit"]["evidence"]}
                            for n, u in zip(aliases[number], copies, strict=True)
                        ],
                    }
                )
            if any(u["participation"] != participation for u in copies):
                checkpoints.append(
                    {
                        "reason": "Teilnahmestände der Dubletten widersprechen sich.",
                        "sources": [
                            {
                                "publication_number": n,
                                "evidence": u["participation"].get("evidence", []),
                            }
                            for n, u in zip(aliases[number], copies, strict=True)
                        ],
                    }
                )
                participation = {
                    **participation,
                    "status": "ungeklärt",
                    "reason": checkpoints[-1]["reason"],
                }
            if participation["status"] in {"Frist offen", "Frist abgelaufen"} and (
                any(n in disputed for n, _ in history) or current_ref in standalone_old
            ):
                participation = {
                    **participation,
                    "status": "ungeklärt",
                    "reason": "Aktueller Dokumentstand für dieses Los oder Verfahren ungeklärt.",
                }
            entry = {
                **reference(current_ref),
                "lot_id": unit["lot_id"],
                "fit": fit,
                "participation": participation,
                "history": stages,
                "checkpoints": checkpoints,
            }
            entries.append(entry)
            if procedure and lot_indexes.get(unit["lot_id"]) == index:
                possible_links[procedure, doc["notice_type"], unit["lot_id"]].append(entry)

    for group in possible_links.values():
        if len(group) < 2:
            continue
        sources = []
        terms = set()
        for entry in group:
            doc = docs[entry["publication_number"]]
            terms.update(participation_terms(doc["units"][entry["unit_index"]]))
            origin = identification(doc, entry["lot_id"])
            origin["evidence"].extend(entry["participation"].get("evidence", []))
            sources.append(origin)

        reason = "Gleicher Verfahrens- und Losbezug. Zuordnung der Bekanntmachungen ungeklärt."
        if len(terms) > 1:
            reason += " Widersprüchliche Einreichungsfristen. Aktuelle Frist ungeklärt."
        for entry in group:
            participation = entry["participation"]
            if len(terms) > 1 and participation["status"] in {"Frist offen", "Frist abgelaufen"}:
                entry["participation"] = {**participation, "status": "ungeklärt", "reason": reason}
            entry["checkpoints"].append({"reason": reason, "sources": sources})

    for entry in entries:
        reasons = []
        if entry["fit"]["status"] == "unpassend":
            reasons.append("Fachlich unpassend")
        if entry["participation"]["status"] in {"nicht offen", "Frist abgelaufen"}:
            reasons.append(entry["participation"]["status"])
        entry["exclusion_reasons"] = reasons

    eligible = [e for e in entries if not e["exclusion_reasons"]]
    eligible.sort(
        key=lambda e: priority(e, docs[e["publication_number"]]["units"][e["unit_index"]])
    )
    return {
        "limit": limit,
        "order": ORDER,
        "selected": eligible[:limit],
        "limited": eligible[limit:],
        "excluded": [e for e in entries if e["exclusion_reasons"]],
        "unavailable": [
            d["publication_number"] for d in documents if d["publication_number"] not in all_docs
        ],
    }


def render_selection(selection: Data) -> str:
    body = ['<h2 id="berichtsauswahl">Berichtsauswahl</h2>', f"<p>{escape(selection['order'])}</p>"]
    for key, label in (
        ("selected", "Im Bericht"),
        ("limited", "Außerhalb des Berichtslimits"),
        ("excluded", "Fachlich oder wegen Teilnahmestand ausgeschlossen"),
    ):
        entries = selection[key]
        body.append(f"<h3>{label} ({len(entries)})</h3><ul>")
        for entry in entries:
            trail = []
            for ref in entry["history"]:
                index = ref["unit_index"]
                copies = [escape(n["publication_number"]) for n in ref["ted_occurrences"]]
                trail.append(" / ".join(f'<a href="#los-{n}-{index}">TED {n}</a>' for n in copies))
            reason = " · ".join(entry["exclusion_reasons"]) or (
                entry["fit"]["status"] + " · " + entry["participation"]["status"]
            )
            scope = entry["lot_id"] or "Verfahren"
            body.append(f"<li>{' → '.join(trail)} · {escape(scope)} · {escape(reason)}")
            if (
                entry["checkpoints"]
                or len(trail) > 1
                or any(stage.get("duplicate_reason") for stage in entry["history"])
            ):
                details = {"history": entry["history"], "checkpoints": entry["checkpoints"]}
                body.append(
                    "<details><summary>Zuordnung und Belege</summary><pre>"
                    + escape(json.dumps(details, ensure_ascii=False, indent=2))
                    + "</pre></details>"
                )
            body.append("</li>")
        body.append("</ul>")
    return "".join(body)
