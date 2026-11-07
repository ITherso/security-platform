"""Fixed, explicit HBF source loader at the offline CLI I/O boundary.

No source path/module is read from a policy document. The four reviewed modules
are isolated from sys.path and their namespaced imports cannot start the HBF
runtime. JSON-only pure calls reuse the actual HBF validators and evaluator.
"""
import builtins
from dataclasses import asdict, dataclass
from datetime import time as LocalTime
import hashlib
from pathlib import Path
import stat
import sys
from types import ModuleType

import pydantic

from .errors import PolicyContractError
from .immutable import thaw
from .models import AdapterIdentity, PolicyBundle, SourceManifestEntry

HBF_SOURCE_FILES = ("config_store.py", "document_limits.py", "policy_objects.py", "policy_engine.py")
PLATFORM_SOURCE_FILES = ("errors.py", "immutable.py", "models.py", "fingerprints.py", "zone_safety.py", "preview.py", "hbf_bridge.py")
MAX_SOURCE_BYTES = 256 * 1024


@dataclass(frozen=True, slots=True)
class HbfAdapter:
    identity: AdapterIdentity
    _objects_module: object
    _engine_module: object

    def normalize(self, bundle):
        objects = thaw(bundle.objects)
        objects["zones"] = {zone.name: list(zone.cidrs) for zone in bundle.ordered_zones}
        try:
            objects = self._objects_module.validate_objects(objects)
            policies = self._engine_module.validate_policies(thaw(bundle.policies), objects)
            zones = objects.pop("zones")
            return PolicyBundle.model_validate({"schema_version": 1,
                "ordered_zones": [{"name": name, "cidrs": values} for name, values in zones.items()],
                "objects": objects, "policies": policies})
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
            raise PolicyContractError("invalid_policy_bundle") from exc

    def _runtime_objects(self, bundle):
        objects = thaw(bundle.objects)
        objects["zones"] = {zone.name: list(zone.cidrs) for zone in bundle.ordered_zones}
        return objects

    def legacy_version(self, bundle):
        return self._engine_module.policy_version(self._runtime_objects(bundle), thaw(bundle.policies))

    def evaluate(self, bundle, scenario):
        # Every context that could otherwise sample ambient state is explicit.
        decision, trace = self._engine_module.evaluate_policies(thaw(bundle.policies), self._runtime_objects(bundle),
            scenario.src_ip, scenario.dst_ip, scenario.dst_port, src_geo=scenario.src_geo, protocol=scenario.protocol,
            network_profile=scenario.network_profile, now=LocalTime.fromisoformat(scenario.evaluation_local_time), explain=True)
        return asdict(decision), trace


def _read_source(path):
    for entry in (path, *path.parents):
        metadata = entry.lstat()
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise PolicyContractError("evaluator_unavailable")
    if not path.is_file():
        raise PolicyContractError("evaluator_unavailable")
    with path.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise PolicyContractError("evaluator_unavailable")
    return raw


def load_hbf_adapter(explicit_root):
    """Read explicit operator-selected source; return None for a fixed failure.

    Loading is trusted-code selection by the local operator, not verification of
    its producer. Actual bytes and runtime versions are bound in the manifest.
    No policy document can select a source, import, command or fallback engine.
    """
    registered = []
    try:
        root = Path(explicit_root).absolute()
        own = Path(__file__).absolute().parent
        sources = {name: _read_source(root / "src" / name) for name in HBF_SOURCE_FILES}
        manifest = [SourceManifestEntry(component="hbf", name=name,
            sha256=hashlib.sha256(sources[name]).hexdigest()) for name in HBF_SOURCE_FILES]
        manifest.extend(SourceManifestEntry(component="platform", name=name,
            sha256=hashlib.sha256(_read_source(own / name)).hexdigest()) for name in PLATFORM_SOURCE_FILES)
        identity = AdapterIdentity(python_implementation=sys.implementation.name, python_version=sys.version.split()[0],
            pydantic_version=pydantic.__version__, source_manifest=tuple(manifest))
        # Invocation identity prevents concurrent loaders from overwriting or
        # removing one another's temporary dataclass module registrations. It
        # never enters an adapter or preview content fingerprint.
        namespace = "_sp_hbf_" + hashlib.sha256(b"".join(sources.values())).hexdigest()[:16] + "_" + format(id(sources), "x")
        modules = {}
        original_import = builtins.__import__
        stdlib = {"contextlib", "copy", "errno", "json", "os", "pathlib", "tempfile", "threading", "time",
                  "msvcrt", "fcntl", "math", "ipaddress", "re", "dataclasses", "datetime", "hashlib"}
        def source_import(name, globals=None, locals=None, fromlist=(), level=0):
            if level:
                raise ImportError("unsupported HBF dependency")
            if name in modules:
                return modules[name]
            if name.split(".", 1)[0] not in stdlib:
                raise ImportError("unsupported HBF dependency")
            return original_import(name, globals, locals, fromlist, level)
        for filename in HBF_SOURCE_FILES:
            short = filename[:-3]
            qualified = namespace + "." + short
            module = ModuleType(qualified)
            module.__file__ = str(root / "src" / filename)
            module.__dict__["__builtins__"] = {**vars(builtins), "__import__": source_import}
            modules[short] = module
            sys.modules[qualified] = module
            registered.append(qualified)
            exec(compile(sources[filename], filename, "exec"), module.__dict__)
        return HbfAdapter(identity, modules["policy_objects"], modules["policy_engine"])
    except Exception:
        return None
    finally:
        for qualified in registered:
            sys.modules.pop(qualified, None)
