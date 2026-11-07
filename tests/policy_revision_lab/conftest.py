import os
from pathlib import Path
import tempfile
from uuid import uuid4

import pytest

from security_platform.connectors.hostbased_firewall.private_files import create_private_directory
from security_platform.policy_contracts.hbf_bridge import load_hbf_adapter
from security_platform.policy_contracts.models import PolicyBundle
from tools.policy_revision_lab.models import LabBinding


@pytest.fixture
def private_parent(tmp_path):
    temporary = None
    if os.name == "nt":
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        assert ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0
        temporary = tempfile.TemporaryDirectory(prefix=".security-revision-lab-test-", dir=buffer.value)
        root = Path(temporary.name)
    else:
        root = tmp_path
    private = create_private_directory(root / "private")
    try:
        yield private
    finally:
        if temporary is not None:
            temporary.cleanup()


@pytest.fixture(scope="session")
def hbf_source():
    explicit = os.environ.get("SP_HBF_SOURCE")
    parent = Path(__file__).resolve().parents[3]
    candidates = [Path(explicit)] if explicit else [parent / "HostBasedFirewall-main", parent / "HostBasedFirewall"]
    source = next((path for path in candidates if (path / "src" / "policy_engine.py").is_file()), None)
    assert source is not None, "SP_HBF_SOURCE must identify the explicit test HBF source"
    return source


@pytest.fixture(scope="session")
def hbf_adapter(hbf_source):
    adapter = load_hbf_adapter(hbf_source)
    assert adapter is not None
    return adapter


@pytest.fixture
def lab_binding():
    return LabBinding(kind="endpoint_staged", tenant_id=str(uuid4()), subject_id=str(uuid4()))


@pytest.fixture
def lab_bundle(hbf_adapter):
    return hbf_adapter.normalize(PolicyBundle(schema_version=1,
        ordered_zones=[{"name": "WAN", "cidrs": ["0.0.0.0/0"]}], objects={},
        policies={"default_action": "ALLOW", "policies": []}))
