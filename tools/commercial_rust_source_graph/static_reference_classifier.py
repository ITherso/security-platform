"""Classify bounded token observations; never resolve Rust modules or macros."""
from __future__ import annotations

from copy import deepcopy
import hashlib

from .source_graph_contracts import (InputError, relative_path, reference_identifier,
                                     condition_identifier, diagnostic_identifier)
from .rust_reference_lexer import LexResult, Token


class _MacroBoundary(Exception):
    def __init__(self, first: Token, last: Token):
        self.first, self.last = first, last


def _is(token: Token, value: str) -> bool:
    return token.text == value and not token.raw_identifier


def _safe_literal(value: str | None) -> str | None:
    if value is None or not 0 < len(value) <= 1024:
        return None
    try:
        return relative_path(value, "literal_relative_path")
    except InputError:
        return None


def classify_source(raw: bytes, source_identity: dict, lexed: LexResult,
                     limits: dict | None = None) -> dict:
    """Return only closed metadata; raw text, literal values and tokens stay local."""
    if (type(raw) is not bytes or len(raw) != source_identity["observed_bytes"]
            or hashlib.sha256(raw).hexdigest() != source_identity["observed_sha256"]
            or lexed.source_id != source_identity["source_id"]
            or lexed.source_sha256 != source_identity["observed_sha256"]):
        raise InputError("rust_source_classifier_identity_mismatch")
    reference_limit, diagnostic_limit = 2048, 4096
    if limits is not None:
        if type(limits) is not dict:
            raise InputError("rust_source_invalid_classifier_limits")
        reference_limit = limits.get("max_references", reference_limit)
        diagnostic_limit = limits.get("max_diagnostics", diagnostic_limit)
        if (type(reference_limit) is not int or not 0 < reference_limit <= 2048
                or type(diagnostic_limit) is not int or not 0 < diagnostic_limit <= 4096):
            raise InputError("rust_source_invalid_classifier_limits")
    summary = deepcopy(lexed.summary)
    if not summary["scan_complete"]:
        return {"lexical_summary": summary, "references": [], "conditions": [],
                "diagnostics": deepcopy(list(lexed.diagnostics))}
    tokens, matching = lexed.tokens, lexed.matching
    references, conditions, diagnostics = [], [], []
    source_id, sha = lexed.source_id, lexed.source_sha256
    opaque_macros = 0

    def diagnostic(code, first, last, scope, reference_id=None):
        if len(diagnostics) >= diagnostic_limit:
            raise InputError("rust_source_diagnostic_limit_exceeded")
        row = {"source_file_reference": source_id, "source_sha256": sha,
               "position": first.position, "byte_end": last.end, "code": code,
               "reference_id": reference_id, "lexical_scope": list(scope)}
        row["diagnostic_id"] = diagnostic_identifier(row)
        if any(prior["diagnostic_id"] == row["diagnostic_id"] for prior in diagnostics):
            return
        diagnostics.append(row)

    def reference(kind, first, last, scope, condition_ids, *, name=None, path=None,
                  status="observed_static_reference", reliable=True, reasons=()):
        if len(references) >= reference_limit:
            raise InputError("rust_source_reference_limit_exceeded")
        if len(scope) > 128:
            raise InputError("rust_source_module_scope_limit_exceeded")
        reasons = list(reasons)
        if condition_ids:
            reasons.append("condition_evaluation_not_performed")
        row = {"source_file_reference": source_id, "source_sha256": sha,
               "position": first.position, "byte_end": last.end, "reference_kind": kind,
               "declared_module_name": name, "literal_relative_path": path,
               "lexical_scope": list(scope), "nesting_depth": len(scope),
               "parent_inline_reference": scope[-1] if scope else None,
               "condition_ids": list(dict.fromkeys(condition_ids)), "interpretation_status": status,
               "context_reliability": "lexically_bounded" if reliable else "context_unresolved",
               "resolved_file": False, "reason_codes": list(dict.fromkeys(reasons))}
        row["reference_id"] = reference_identifier(row)
        references.append(row)
        return row

    def attribute(index, end):
        cursor = index + 1
        style = "outer"
        if cursor < end and _is(tokens[cursor], "!"):
            cursor, style = cursor + 1, "inner"
        if cursor >= end or not _is(tokens[cursor], "["):
            return None
        close = matching[cursor]
        if not cursor < close < end:
            return None
        content = list(tokens[cursor + 1:close])
        head = content[0] if content else None
        kind = head.text if head is not None and head.kind == "identifier" and not head.raw_identifier else "other"
        result = {"first": tokens[index], "last": tokens[close], "style": style,
                  "kind": kind, "condition_id": None, "path": None,
                  "path_supported": False, "conditional_path": False, "end": close + 1}
        if kind in ("cfg", "cfg_attr"):
            row = {"source_file_reference": source_id, "source_sha256": sha,
                   "position": tokens[index].position, "byte_end": tokens[close].end,
                   "kind": kind, "attribute_style": style,
                   "span_sha256": hashlib.sha256(raw[tokens[index].start:tokens[close].end]).hexdigest(),
                   "evaluation_status": "condition_declared_evaluation_not_performed"}
            row["condition_id"] = condition_identifier(row)
            if len(conditions) >= 4096:
                raise InputError("rust_source_condition_limit_exceeded")
            conditions.append(row)
            result["condition_id"] = row["condition_id"]
            if kind == "cfg_attr":
                result["conditional_path"] = any(_is(content[pos], "path") and _is(content[pos + 1], "=")
                                                 for pos in range(len(content) - 1))
        elif kind == "path":
            result["path_supported"] = (len(content) == 3 and _is(content[1], "=")
                                         and content[2].kind == "string")
            if result["path_supported"]:
                result["path"] = _safe_literal(content[2].value)
                result["path_supported"] = result["path"] is not None
        return result

    def module_head(index, end):
        cursor = index
        if _is(tokens[cursor], "pub"):
            cursor += 1
            if cursor < end and _is(tokens[cursor], "("):
                cursor = matching[cursor] + 1
        if cursor < end and _is(tokens[cursor], "mod"):
            return cursor
        return None

    def detach_paths(attrs, scope):
        for item in attrs:
            if item["kind"] == "path":
                diagnostic("attribute_binding_unresolved", item["first"], item["last"], scope)

    def scan(start, end, scope, inherited_conditions, reliable):
        nonlocal opaque_macros
        cursor, attrs = start, []
        inner_conditions, statement_conditions = list(inherited_conditions), []
        while cursor < end:
            token = tokens[cursor]
            if _is(token, "#"):
                item = attribute(cursor, end)
                if item is not None:
                    if item["style"] == "inner":
                        if item["condition_id"] is not None:
                            inner_conditions.append(item["condition_id"])
                        if item["kind"] == "path":
                            diagnostic("attribute_binding_unresolved", item["first"], item["last"], scope)
                    else:
                        attrs.append(item)
                    cursor = item["end"]
                    continue
            head = module_head(cursor, end)
            if head is not None:
                name_index, finish = head + 1, head + 2
                condition_ids = inner_conditions + statement_conditions + [a["condition_id"] for a in attrs if a["condition_id"]]
                if (finish >= end or tokens[name_index].kind != "identifier"
                        or tokens[finish].text not in (";", "{")):
                    row = reference("unsupported_reference", tokens[head], tokens[head], scope, condition_ids,
                                    status="unsupported_reference", reliable=False, reasons=("unsupported_static_reference",))
                    diagnostic("unsupported_reference", tokens[head], tokens[head], scope, row["reference_id"])
                    detach_paths(attrs, scope)
                    attrs, statement_conditions, cursor = [], [], head + 1
                    continue
                name = tokens[name_index].text
                inline = _is(tokens[finish], "{")
                closing = matching[finish] if inline else finish
                paths = [a for a in attrs if a["kind"] == "path"]
                conditional_path = any(a["conditional_path"] for a in attrs)
                kind = "inline_module_declaration" if inline else "external_module_declaration"
                status, path, reasons = "observed_static_reference", None, []
                context = reliable
                if inline:
                    reasons.append("inline_module_has_no_external_file")
                    if paths:
                        status, context = "attribute_binding_unresolved", False
                        reasons.append("attribute_binding_not_established")
                elif conditional_path:
                    status, context = "conditional_path_unresolved", False
                    reasons.append("conditional_path_not_established")
                elif len(paths) == 1 and paths[0]["path_supported"]:
                    kind, path = "explicit_path_module_declaration", paths[0]["path"]
                    reasons.append("literal_path_requires_explicit_allowlist")
                    if scope or not reliable:
                        status, context = "path_resolution_context_unresolved", False
                        reasons.append("relative_path_context_not_established")
                elif paths:
                    status, context = "attribute_binding_unresolved", False
                    reasons.append("attribute_binding_not_established")
                    if any(not a["path_supported"] for a in paths):
                        reasons.append("unsupported_literal_path")
                else:
                    reasons.append("module_file_resolution_not_performed")
                row = reference(kind, tokens[head], tokens[closing], scope, condition_ids, name=name,
                                path=path, status=status, reliable=context, reasons=reasons)
                if status != "observed_static_reference":
                    diagnostic(status, tokens[head], tokens[closing], scope, row["reference_id"])
                if inline:
                    scan(finish + 1, closing, scope + [row["reference_id"]], condition_ids, reliable)
                attrs, statement_conditions, cursor = [], [], closing + 1
                continue
            if attrs:
                detach_paths(attrs, scope)
                statement_conditions += [a["condition_id"] for a in attrs if a["condition_id"]]
                attrs = []
            if (token.kind == "identifier" and cursor + 1 < end and _is(tokens[cursor + 1], "!")
                    and not (cursor + 2 < end and _is(tokens[cursor + 2], "="))):
                opening = cursor + 2
                if _is(token, "macro_rules"):
                    if opening < end and tokens[opening].kind == "identifier":
                        opening += 1
                if opening < end and tokens[opening].text in ("(", "[", "{"):
                    closing = matching[opening]
                    if closing < opening or closing >= end:
                        raise InputError("rust_source_inconsistent_macro_boundary")
                    opaque_macros += 1
                    if _is(token, "include"):
                        condition_ids = inner_conditions + statement_conditions
                        args = tokens[opening + 1:closing]
                        literal = len(args) == 1 and args[0].kind == "string"
                        path = _safe_literal(args[0].value) if literal else None
                        qualified = cursor > start and _is(tokens[cursor - 1], ":")
                        if qualified:
                            row = reference("unsupported_reference", token, tokens[closing], scope, condition_ids,
                                            status="unsupported_reference", reliable=False,
                                            reasons=("macro_expansion_not_performed", "unsupported_static_reference"))
                        elif path is not None:
                            context = reliable and not scope
                            row = reference("literal_include_reference", token, tokens[closing], scope, condition_ids,
                                            path=path, reliable=context,
                                            status="observed_static_reference" if context else "path_resolution_context_unresolved",
                                            reasons=("literal_path_requires_explicit_allowlist",) if context else
                                            ("literal_path_requires_explicit_allowlist", "relative_path_context_not_established"))
                        elif literal:
                            row = reference("unsupported_reference", token, tokens[closing], scope, condition_ids,
                                            status="unsupported_reference", reliable=False,
                                            reasons=("unsupported_literal_path", "unsupported_static_reference"))
                        else:
                            row = reference("dynamic_reference_unresolved", token, tokens[closing], scope, condition_ids,
                                            status="dynamic_reference_unresolved", reliable=False,
                                            reasons=("dynamic_include_not_evaluated", "macro_expansion_not_performed"))
                        if row["interpretation_status"] != "observed_static_reference":
                            diagnostic(row["interpretation_status"], token, tokens[closing], scope, row["reference_id"])
                    cursor, statement_conditions = closing + 1, []
                    continue
                # An unbounded/unsupported macro form must not leave following
                # tokens available as though they were ordinary source items.
                raise _MacroBoundary(token, tokens[min(cursor + 1, end - 1)])
            if token.text in ("(", "[", "{"):
                closing = matching[cursor]
                if closing < cursor or closing >= end:
                    raise InputError("rust_source_inconsistent_lexical_boundary")
                # Non-module groups do not establish a safe relative module base.
                scan(cursor + 1, closing, scope, inner_conditions + statement_conditions, False)
                cursor = closing + 1
                if token.text == "{":
                    statement_conditions = []
                continue
            if _is(token, ";"):
                statement_conditions = []
            cursor += 1
        detach_paths(attrs, scope)

    try:
        scan(0, len(tokens), [], [], True)
    except _MacroBoundary as error:
        references, conditions, diagnostics = [], [], []
        diagnostic("macro_context_unresolved", error.first, error.last, [])
        summary.update(lexical_status="lexical_boundary_unresolved", scan_complete=False,
                       opaque_macro_tree_count=opaque_macros, reference_count=0,
                       condition_count=0, diagnostic_count=1)
        return {"lexical_summary": summary, "references": [], "conditions": [], "diagnostics": diagnostics}
    references.sort(key=lambda row: (row["position"]["byte_offset"], row["reference_id"]))
    conditions.sort(key=lambda row: (row["position"]["byte_offset"], row["condition_id"]))
    diagnostics.sort(key=lambda row: (row["position"]["byte_offset"], row["diagnostic_id"]))
    summary.update(opaque_macro_tree_count=opaque_macros, reference_count=len(references),
                   condition_count=len(conditions), diagnostic_count=len(diagnostics))
    return {"lexical_summary": summary, "references": references,
            "conditions": conditions, "diagnostics": diagnostics}


__all__ = ("classify_source",)
