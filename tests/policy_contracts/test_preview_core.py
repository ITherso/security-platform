from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import time as LocalTime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

from pydantic import ValidationError
import pytest

from security_platform.policy_contracts.errors import PolicyContractError
from security_platform.policy_contracts.fingerprints import adapter_fingerprint, bundle_fingerprint
from security_platform.policy_contracts.hbf_bridge import HBF_SOURCE_FILES, load_hbf_adapter
from security_platform.policy_contracts.immutable import FrozenObject, freeze_object
from security_platform.policy_contracts.models import MAX_SCENARIOS, MAX_TRACE_ENTRIES, PolicyBundle, PreviewOutcome, PreviewScenario
from security_platform.policy_contracts.preview import preview_policy
from security_platform.policy_contracts.zone_safety import ensure_unambiguous_zones

HBF_ROOT = Path(__file__).resolve().parents[3] / "HostBasedFirewall-main"


@pytest.fixture(scope="module")
def adapter():
    if not (HBF_ROOT / "src/policy_engine.py").exists():
        pytest.skip("Explicit reviewed HBF source fixture is unavailable")
    result = load_hbf_adapter(HBF_ROOT)
    assert result is not None
    return result


def bundle(*, zones=(), rules=(), default="ALLOW", objects=None):
    return PolicyBundle.model_validate({"schema_version": 1,
        "ordered_zones": [{"name": name, "cidrs": list(cidrs)} for name, cidrs in zones],
        "objects": objects or {}, "policies": {"default_action": default, "policies": list(rules)}})


def scenario(**changes):
    return PreviewScenario.model_validate({"scenario_id": "sample", "src_ip": "10.1.2.3", "dst_ip": "198.51.100.1",
        "protocol": "TCP", "dst_port": 443, "network_profile": "PUBLIC", "evaluation_local_time": "12:00:00", **changes})


def test_actual_legacy_order_hash_collision_and_public_rejection_in_both_positions(adapter):
    rules = [{"id": 1, "name": "A deny", "src_zones": ["A"], "action": "DENY"}]
    orders = [("A", ["10.0.0.0/8"]), ("B", ["10.0.0.0/8"])]
    a = adapter.normalize(bundle(zones=orders, rules=rules))
    b = adapter.normalize(bundle(zones=list(reversed(orders)), rules=rules))
    assert adapter.legacy_version(a) == adapter.legacy_version(b)
    assert adapter.evaluate(a, scenario())[0]["action"] == "DENY"
    assert adapter.evaluate(b, scenario())[0]["action"] == "ALLOW"
    assert bundle_fingerprint(a) != bundle_fingerprint(b)
    good = bundle()
    for bad in (a, b):
        for base, candidate in ((bad, good), (good, bad)):
            result = preview_policy(base, candidate, [scenario()], adapter)
            assert result.status == "blocked" and result.blocker_codes == ("ambiguous_equal_prefix_zones",)
            assert result.results == () and result.preview_fingerprint is None


@pytest.mark.parametrize("zones", [
    [("A", ["10.1.2.3/8"]), ("B", ["10.0.0.0/8"])],
    [("A", ["2001:db8::/32"]), ("B", ["2001:0db8:0000::/32"])],
])
def test_host_bits_and_ipv6_text_aliases_reject_cross_zone_ties(zones):
    with pytest.raises(PolicyContractError, match="ambiguous_equal_prefix_zones"):
        ensure_unambiguous_zones(bundle(zones=zones))


@pytest.mark.parametrize("zones", [
    [("A", ["10.0.0.0/8", "10.1.2.3/8"])],
    [("A", ["10.0.0.0/8"]), ("B", ["11.0.0.0/8"])],
    [("A", ["0.0.0.0/0"]), ("B", ["::/0"])],
    [("A", ["10.0.0.0/8"]), ("B", ["10.1.2.0/24"])],
])
def test_nonambiguous_zones_remain_valid(zones, adapter):
    supplied = bundle(zones=zones)
    ensure_unambiguous_zones(supplied)
    assert preview_policy(supplied, supplied, [scenario()], adapter).status == "ok"


def test_longest_prefix_is_preserved_across_zone_order_changes(adapter):
    zones = [("WIDE", ["10.0.0.0/8"]), ("NARROW", ["10.1.2.0/24"])]
    rules = [{"id": 1, "name": "Narrow deny", "src_zones": ["NARROW"], "action": "DENY"}]
    a, b = bundle(zones=zones, rules=rules), bundle(zones=list(reversed(zones)), rules=rules)
    result = preview_policy(a, b, [scenario()], adapter)
    assert result.status == "ok"
    assert result.results[0].base.decision.action == result.results[0].candidate.decision.action == "DENY"
    assert result.base_fingerprint != result.candidate_fingerprint


def test_normalized_fingerprints_results_and_input_immutability(adapter):
    supplied = {"schema_version": 1, "ordered_zones": [{"name": "LAN", "cidrs": ["10.1.2.3/8"]}],
        "objects": {"services": {"HTTPS": {"ports": [443], "protocols": ["TCP"]}}},
        "policies": {"default_action": "DENY", "policies": [{"id": 1, "action": "ALLOW", "services": ["HTTPS"]}]}}
    original = deepcopy(supplied)
    first = PolicyBundle.model_validate(supplied)
    supplied["objects"]["services"]["HTTPS"]["ports"].append(80)
    assert first.objects["services"]["HTTPS"]["ports"] == (443,)
    with pytest.raises((AttributeError, TypeError)):
        first.objects["services"]["HTTPS"]["ports"].append(80)
    with pytest.raises((ValidationError, FrozenInstanceError)):
        first.ordered_zones[0].name = "CHANGED"
    with pytest.raises(FrozenInstanceError):
        first.objects._pairs = ()
    second = PolicyBundle.model_validate(original)
    before = second.model_dump(mode="json")
    one = preview_policy(first, second, [scenario()], adapter)
    two = preview_policy(first, second, [scenario()], adapter)
    assert one == two and one.status == "ok" and one.base_fingerprint == one.candidate_fingerprint
    assert second.model_dump(mode="json") == before
    assert one.adapter_identity == adapter.identity


def test_source_default_order_object_and_behavior_changes_bind_distinct_candidates(adapter):
    base = bundle()
    candidates = [bundle(default="DENY"),
        bundle(rules=[{"id": 1, "action": "DENY"}, {"id": 2, "action": "ALLOW"}]),
        bundle(rules=[{"id": 2, "action": "ALLOW"}, {"id": 1, "action": "DENY"}]),
        bundle(objects={"address_objects": {"SERVER": "198.51.100.1"}}),
        bundle(rules=[{"id": 1, "action": "ALLOW", "log": False}]),
        bundle(rules=[{"id": 1, "action": "ALLOW", "nat": True}])]
    outputs = [preview_policy(base, candidate, [scenario()], adapter) for candidate in candidates]
    assert all(result.status == "ok" for result in outputs)
    assert len({result.candidate_fingerprint for result in outputs}) == len(candidates)
    assert len({result.preview_fingerprint for result in outputs}) == len(candidates)
    assert len({result.base_fingerprint for result in outputs}) == 1


def test_time_profile_and_country_are_explicit_source_inputs(adapter):
    rules = [{"id": 1, "name": "Work daytime", "action": "DENY", "network_profiles": ["WORK"], "schedule": "DAY"}]
    candidate = bundle(rules=rules, objects={"schedules": {"DAY": {"start": "09:00", "end": "17:00"}}})
    cases = [scenario(scenario_id="work-day", network_profile="WORK"),
             scenario(scenario_id="work-night", network_profile="WORK", evaluation_local_time="22:00:00"),
             scenario(scenario_id="public-day", network_profile="PUBLIC")]
    result = preview_policy(bundle(), candidate, cases, adapter)
    assert [row.candidate.decision.action for row in result.results] == ["DENY", "ALLOW", "ALLOW"]
    for missing in (scenario(network_profile=None), scenario(evaluation_local_time=None)):
        rejected = preview_policy(bundle(), candidate, [missing], adapter)
        assert rejected.blocker_codes == ("insufficient_context",) and rejected.preview_fingerprint is None
    country = bundle(rules=[{"id": 1, "action": "DENY", "if": {"geo": "TR"}}])
    assert preview_policy(bundle(), country, [scenario()], adapter).blocker_codes == ("insufficient_context",)
    result = preview_policy(bundle(), country, [scenario(src_geo="tr")], adapter)
    assert result.status == "ok" and result.results[0].candidate.decision.action == "DENY"


def test_manifest_tracks_exact_compiled_source_and_repeated_loader_changes(tmp_path, adapter):
    source = tmp_path / "HBF" / "src"
    source.mkdir(parents=True)
    for filename in HBF_SOURCE_FILES:
        shutil.copyfile(HBF_ROOT / "src" / filename, source / filename)
    old = load_hbf_adapter(source.parent)
    assert old is not None
    engine = source / "policy_engine.py"
    raw = engine.read_bytes().replace(b'reason="No policy matched"', b'reason="Changed source default"')
    engine.write_bytes(raw)
    new = load_hbf_adapter(source.parent)
    assert new is not None
    assert adapter_fingerprint(old.identity) != adapter_fingerprint(new.identity)
    actual = next(row.sha256 for row in new.identity.source_manifest if row.component == "hbf" and row.name == "policy_engine.py")
    assert actual == hashlib.sha256(raw).hexdigest()
    assert old.evaluate(old.normalize(bundle()), scenario())[0]["reason"] == "No policy matched"
    assert new.evaluate(new.normalize(bundle()), scenario())[0]["reason"] == "Changed source default"
    old_preview = preview_policy(bundle(), bundle(), [scenario()], old)
    new_preview = preview_policy(bundle(), bundle(), [scenario()], new)
    assert old_preview.base_fingerprint == new_preview.base_fingerprint
    assert old_preview.preview_fingerprint != new_preview.preview_fingerprint
    assert not list(source.rglob("*.pyc"))


def test_concurrent_loader_namespaces_do_not_collide(adapter):
    with ThreadPoolExecutor(max_workers=4) as pool:
        copies = list(pool.map(lambda _: load_hbf_adapter(HBF_ROOT), range(12)))
    assert all(copy is not None for copy in copies)
    assert {adapter_fingerprint(copy.identity) for copy in copies} == {adapter_fingerprint(adapter.identity)}


def test_unavailable_is_fixed_and_has_no_successful_approximation(tmp_path):
    assert load_hbf_adapter(tmp_path / "missing") is None
    result = preview_policy(bundle(), bundle(), [scenario()])
    assert result.status == "blocked" and result.blocker_codes == ("evaluator_unavailable",)
    assert result.preview_fingerprint is None and result.results == ()


@pytest.mark.parametrize("field,value", [("schema_version", True), ("schema_version", 2),
    ("apply", True), ("command", "ignored-command"), ("verified", True), ("execution_authorized", True)])
def test_bundle_unknown_authority_and_schema_coercion_rejected(field, value):
    payload = bundle().model_dump(mode="json")
    payload[field] = value
    with pytest.raises(ValidationError):
        PolicyBundle.model_validate(payload)


@pytest.mark.parametrize("value", [True, 0, 1, "false"])
def test_preview_execution_guard_is_strict_false(value):
    with pytest.raises(ValidationError):
        PreviewOutcome(status="blocked", blocker_codes=("evaluator_unavailable",), execution_authorized=value)


def test_bounds_and_no_partial_success(adapter):
    rules = [{"id": index + 1, "name": f"Rule {index}", "action": "ALLOW"} for index in range(500)]
    candidate = bundle(rules=rules)
    result = preview_policy(bundle(), candidate, [scenario()], adapter)
    assert result.status == "ok"
    assert len(result.results[0].candidate.trace) == MAX_TRACE_ENTRIES
    assert result.results[0].candidate.trace_total == 500 and result.results[0].candidate.trace_complete is False
    rejected = preview_policy(bundle(), candidate, [scenario(scenario_id=str(index)) for index in range(MAX_SCENARIOS + 1)], adapter)
    assert rejected.status == "blocked" and rejected.results == ()
    with pytest.raises(ValidationError):
        bundle(rules=rules + [{"id": 501, "action": "ALLOW"}])
    with pytest.raises(PolicyContractError):
        freeze_object(FrozenObject((("duplicate", 1), ("duplicate", 2))))
    deep = {}
    for _ in range(23):
        deep = {"child": deep}
    with pytest.raises(ValidationError):
        bundle(objects={"security_profiles": {"nested": deep}})


def test_workspace_preview_returns_base_not_candidate_legacy_version():
    if not (HBF_ROOT / "src/policy_workspace.py").exists():
        pytest.skip("Explicit reviewed source fixture unavailable")
    script = textwrap.dedent('''
        import json,sys,tempfile
        from pathlib import Path
        sys.path.insert(0, str(Path(sys.argv[1]) / "src"))
        from config_store import write_json
        from policy_workspace import PolicyWorkspace
        from policy_engine import policy_version,validate_policies
        with tempfile.TemporaryDirectory() as value:
            path=Path(value)
            write_json(path/'objects.json', {'zones':{}})
            write_json(path/'policies.json', {'default_action':'ALLOW','policies':[]})
            workspace=PolicyWorkspace(path/'policies.json',path/'objects.json',path/'policy_bundle')
            base=workspace.snapshot()
            candidate={'default_action':'DENY','policies':[]}
            result=workspace.preview(candidate,{'src_ip':'192.0.2.1','dst_ip':'198.51.100.1','dst_port':443,'protocol':'TCP','network_profile':'PUBLIC'})
            print(json.dumps({'returned':result['version'],'base':base['version'],
                'candidate':policy_version(base['objects'],validate_policies(candidate,base['objects']))}))
    ''')
    process = subprocess.run([sys.executable, "-B", "-c", script, str(HBF_ROOT)], capture_output=True, text=True, timeout=15)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["returned"] == result["base"] and result["returned"] != result["candidate"]


def test_core_tripwires_and_deny_temp_nat_have_no_effects(adapter, monkeypatch):
    import builtins
    import ctypes
    import os
    import socket
    import threading
    import time
    source, sample = bundle(), scenario()
    temporary = bundle(rules=[{"id": 1, "action": "DENY_TEMP", "then": {"block": "60s"}}])
    nat = bundle(rules=[{"id": 1, "action": "ALLOW", "nat": True}])
    attempts = []
    def tripwire(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("forbidden ambient access")
    class Environment(Mapping):
        __getitem__ = __iter__ = __len__ = tripwire
    class NoClock:
        now = staticmethod(tripwire)
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", tripwire)
        patch.setattr(Path, "open", tripwire)
        patch.setattr(Path, "read_bytes", tripwire)
        patch.setattr(Path, "stat", tripwire)
        patch.setattr(Path, "lstat", tripwire)
        patch.setattr(os, "stat", tripwire)
        patch.setattr(os, "system", tripwire)
        patch.setattr(socket, "socket", tripwire)
        patch.setattr(socket, "getaddrinfo", tripwire)
        patch.setattr(subprocess, "Popen", tripwire)
        patch.setattr(threading, "Timer", tripwire)
        patch.setattr(threading.Thread, "start", tripwire)
        patch.setattr(time, "time", tripwire)
        patch.setattr(time, "monotonic", tripwire)
        patch.setattr(os, "getenv", tripwire)
        patch.setattr(os, "environ", Environment())
        patch.setattr(ctypes, "CDLL", tripwire)
        if hasattr(ctypes, "WinDLL"):
            patch.setattr(ctypes, "WinDLL", tripwire)
        patch.setattr(adapter._engine_module, "datetime", NoClock)
        temp_result = preview_policy(source, temporary, [sample], adapter)
        nat_result = preview_policy(source, nat, [sample], adapter)
    assert attempts == []
    assert temp_result.status == nat_result.status == "ok"
    assert temp_result.results[0].candidate.decision.temp_block_sec == 60
    assert nat_result.results[0].candidate.decision.nat is True
    assert not temp_result.execution_authorized and not nat_result.execution_authorized


@pytest.mark.parametrize("change", [{"dst_port": True}, {"dst_port": 1.0}, {"network_profile": "INVALID"},
                                   {"execution_authorized": True}, {"evaluation_local_time": "25:00:00"}])
def test_unvalidated_copied_scenario_is_rejected_before_evaluation(adapter, change):
    valid = scenario()
    copied = valid.model_copy(update=change)
    original = valid.model_dump(mode="json")
    result = preview_policy(bundle(), bundle(rules=[{"id": 1, "action": "DENY", "port": 1}]), [copied], adapter)
    assert result.status == "blocked" and result.blocker_codes == ("invalid_scenario",)
    assert result.results == () and result.preview_fingerprint is None
    assert valid.model_dump(mode="json") == original


@pytest.mark.parametrize("change", [{"schema_version": True}, {"contract_version": "wrong/v999"},
    {"normalization_version": "other/v2"}, {"execution_authorized": True}])
def test_unvalidated_copied_bundle_cannot_normalize_away_invalid_contract(adapter, change):
    valid = bundle()
    copied = valid.model_copy(update=change)
    original = valid.model_dump(mode="json")
    for base, candidate in ((copied, valid), (valid, copied)):
        result = preview_policy(base, candidate, [scenario()], adapter)
        assert result.status == "blocked" and result.blocker_codes == ("invalid_policy_bundle",)
        assert result.results == () and result.preview_fingerprint is None
    assert valid.model_dump(mode="json") == original


def test_unvalidated_copied_adapter_identity_is_unavailable(adapter):
    from dataclasses import replace
    invalid = replace(adapter, identity=adapter.identity.model_copy(update={"contract_version": "wrong/v999"}))
    result = preview_policy(bundle(), bundle(), [scenario()], invalid)
    assert result.blocker_codes == ("evaluator_unavailable",) and result.results == ()


def test_incompatible_source_initialization_error_is_fixed_unavailable(tmp_path):
    source = tmp_path / "HBF" / "src"
    source.mkdir(parents=True)
    for filename in HBF_SOURCE_FILES:
        shutil.copyfile(HBF_ROOT / "src" / filename, source / filename)
    with (source / "policy_engine.py").open("ab") as stream:
        stream.write(b"\nraise NameError('private source detail must not escape')\n")
    assert load_hbf_adapter(source.parent) is None
