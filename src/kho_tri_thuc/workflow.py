"""One offline CLI facade over the six modules; JSON requests retain explicit actors/times."""
from __future__ import annotations

import inspect

from .ha_tang.primitives import DataError
from .hoc.service import Learning, Reconciliation
from .kiem_chung.service import Quality, reconstruct_open_items
from .trang_thai.service import Sessions
from .tri_thuc.service import Knowledge
from .xuat.service import ReviewExport
from .xuat.shadow import ShadowJunskyExport


ACTIONS = (
    "knowledge-stage", "knowledge-approve", "knowledge-revoke", "knowledge-query", "knowledge-export", "knowledge-import", "history-link",
    "session-open", "session-propose", "session-cancel", "review-export", "review-import", "batch-export", "batch-recover", "batch-cancel-prepared", "shadow-export", "shadow-recover", "shadow-reconcile",
    "reconcile", "label-from-journal", "label-revoke", "learning-rebuild", "rule-propose", "dataset-register", "evaluate", "candidate-evaluate", "blind-export", "month-close", "reconstruct",
)


def dispatch(store, action, request):
    knowledge, sessions, review = Knowledge(store), Sessions(store), ReviewExport(store)
    shadow = ShadowJunskyExport(store)
    learning, quality = Learning(store), Quality(store)
    methods = {
        "knowledge-stage": knowledge.stage_many, "knowledge-approve": knowledge.approve, "knowledge-revoke": knowledge.revoke,
        "knowledge-query": knowledge.query, "knowledge-export": knowledge.export_pending, "knowledge-import": knowledge.import_workbook,
        "history-link": knowledge.link_history, "session-open": sessions.open, "session-propose": sessions.propose,
        "session-cancel": sessions.cancel, "review-export": review.review_workbook, "review-import": review.import_review,
        "batch-export": review.export, "batch-recover": review.recover, "reconcile": Reconciliation(store).reconcile,
        "batch-cancel-prepared": review.cancel_prepared,
        "shadow-export": shadow.export, "shadow-recover": shadow.recover, "shadow-reconcile": shadow.reconcile,
        "label-from-journal": learning.from_journal, "label-revoke": learning.revoke, "learning-rebuild": learning.rebuild,
        "rule-propose": learning.propose_rule, "dataset-register": quality.register, "evaluate": quality.evaluate,
        "candidate-evaluate": quality.evaluate_candidate, "blind-export": quality.blind_workbook, "month-close": quality.close_month,
        "reconstruct": reconstruct_open_items,
    }
    method = methods.get(action)
    if not method or not isinstance(request, dict):
        raise DataError("WORKFLOW_REQUEST", "Lệnh không tồn tại hoặc request phải là JSON object.")
    try:
        inspect.signature(method).bind(**request)
    except TypeError as exc:
        raise DataError("WORKFLOW_ARGUMENTS", "Request thiếu/thừa tham số; xem docs/HUONG-DAN-VAN-HANH.md.") from exc
    result = method(**request)
    return result if isinstance(result, dict) else {"result": result, "fixture_only": True}
