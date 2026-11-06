"""Private client files with native Windows DACL checks or POSIX owner/mode checks.

Windows APIs are loaded only when these explicit client operations run. The
server imports no COM, WinDivert or Windows-only Python dependency.
"""
from contextlib import contextmanager
import ctypes
import json
import os
from pathlib import Path
import stat
import tempfile
import time


class ClientFileError(ValueError):
    pass


def _require(condition):
    if not condition:
        raise ClientFileError("private_client_file_unavailable")


def _plain_path(path):
    path = Path(os.path.abspath(path))
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400)
    return path


def _windows_libraries():
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    return kernel, advapi


def _sid_string(pointer, kernel, advapi):
    output = ctypes.c_void_p()
    _require(bool(advapi.ConvertSidToStringSidW(pointer, ctypes.byref(output))))
    try:
        return ctypes.wstring_at(output.value)
    finally:
        kernel.LocalFree(output)


def _current_windows_sid():
    from ctypes import wintypes
    kernel, advapi = _windows_libraries()
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                         wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    token = wintypes.HANDLE()
    _require(bool(advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token))))
    try:
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        _require(0 < size.value <= 65536)
        buffer = ctypes.create_string_buffer(size.value)
        _require(bool(advapi.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size))))
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p)).contents.value
        return _sid_string(sid, kernel, advapi)
    finally:
        kernel.CloseHandle(token)


def _windows_descriptor(path):
    from ctypes import wintypes
    kernel, advapi = _windows_libraries()
    advapi.GetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    advapi.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi.GetAce.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
    owner, dacl, security = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
    _require(advapi.GetNamedSecurityInfoW(str(path), 1, 5, ctypes.byref(owner), None,
        ctypes.byref(dacl), None, ctypes.byref(security)) == 0)
    try:
        _require(bool(owner.value) and bool(dacl.value))
        # ACL header: revision, reserved byte, size, ACE count, reserved WORD.
        header = (ctypes.c_ushort * 4).from_address(dacl.value)
        count = header[2]
        _require(count <= 4096)
        aces = []
        for index in range(count):
            pointer = ctypes.c_void_p()
            _require(bool(advapi.GetAce(dacl, index, ctypes.byref(pointer))))
            ace = (ctypes.c_ubyte * 4).from_address(pointer.value)
            kind, flags, size = ace[0], ace[1], int.from_bytes(bytes(ace[2:4]), "little")
            _require(kind in (0, 1) and size >= 12)
            mask = ctypes.c_uint32.from_address(pointer.value + 4).value
            sid = _sid_string(pointer.value + 8, kernel, advapi)
            aces.append((kind, flags, mask, sid))
        return _sid_string(owner.value, kernel, advapi), aces
    finally:
        kernel.LocalFree(security)


def _windows_private_acl(path, *, ancestor=False):
    trusted = {_current_windows_sid(), "S-1-5-18", "S-1-5-32-544"}
    if ancestor:
        trusted.add("S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464")
    owner, aces = _windows_descriptor(path)
    _require(owner in trusted)
    # OWNER RIGHTS grants apply to the already validated object owner. Python
    # 3.13+ uses this well-known SID when creating mode-0700 Windows directories.
    trusted.add("S-1-3-4")
    forbidden = (0x000D0040 | 0x10000000 | 0x02000000) if ancestor else (0x001F01FF | 0xF2000000)
    for kind, flags, mask, sid in aces:
        if kind == 1 or flags & 0x8:
            continue
        _require(sid in trusted or not mask & forbidden)


def _install_private_windows_acl(path):
    from ctypes import wintypes
    kernel, advapi = _windows_libraries()
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR,
        wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    advapi.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.BOOL)]
    advapi.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    advapi.SetNamedSecurityInfoW.restype = wintypes.DWORD
    security = ctypes.c_void_p()
    sid = _current_windows_sid()
    sddl = f"D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;{sid})"
    _require(bool(advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(security), None)))
    try:
        present, defaulted, dacl = wintypes.BOOL(), wintypes.BOOL(), ctypes.c_void_p()
        _require(bool(advapi.GetSecurityDescriptorDacl(security, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted))))
        _require(bool(present.value) and bool(dacl.value))
        _require(advapi.SetNamedSecurityInfoW(str(path), 1, 0x80000004, None, None, dacl, None) == 0)
    finally:
        kernel.LocalFree(security)


def _check_ancestors(path):
    for parent in path.parents:
        info = parent.lstat()
        _require(stat.S_ISDIR(info.st_mode))
        if os.name == "nt":
            _windows_private_acl(parent, ancestor=True)
        else:
            _require(info.st_uid in (0, os.geteuid()))
            _require(not info.st_mode & 0o022 or bool(info.st_mode & stat.S_ISVTX) and info.st_uid == 0)


def validate_private_path(path, *, directory=False):
    path = _plain_path(path)
    info = path.lstat()
    _require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
    _check_ancestors(path)
    if os.name == "nt":
        _windows_private_acl(path)
    else:
        _require(info.st_uid == os.geteuid() and not info.st_mode & 0o077)
    return path


def create_private_directory(path):
    path = _plain_path(path)
    _check_ancestors(path)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    else:
        if os.name == "nt":
            _install_private_windows_acl(path)
    return validate_private_path(path, directory=True)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def bounded_json(raw, maximum):
    _require(isinstance(raw, bytes) and len(raw) <= maximum)
    def constant(value):
        raise ClientFileError("private_client_file_unavailable")
    try:
        value = json.loads(raw, object_pairs_hook=_unique, parse_constant=constant)
        _require(isinstance(value, dict))
        stack = [(value, 0)]
        nodes = 0
        while stack:
            current, depth = stack.pop()
            nodes += 1
            _require(depth <= 12 and nodes <= 10000)
            if isinstance(current, dict):
                stack.extend((item, depth + 1) for item in current.values())
            elif isinstance(current, list):
                stack.extend((item, depth + 1) for item in current)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ClientFileError("private_client_file_unavailable") from exc


def read_private_json(path, *, maximum=32768):
    try:
        path = validate_private_path(path)
        with path.open("rb") as stream:
            return bounded_json(stream.read(maximum + 1), maximum)
    except (OSError, ValueError) as exc:
        raise ClientFileError("private_client_file_unavailable") from exc


def write_private_json(path, value):
    path = _plain_path(path)
    validate_private_path(path.parent, directory=True)
    if path.exists():
        validate_private_path(path)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    _require(len(encoded) <= 32768)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".client-", suffix=".tmp")
    temporary = Path(name)
    try:
        if os.name == "nt":
            _install_private_windows_acl(temporary)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


@contextmanager
def private_lock(directory):
    directory = validate_private_path(directory, directory=True)
    path = directory / "client.lock"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(descriptor)
        if os.name == "nt":
            _install_private_windows_acl(path)
    validate_private_path(path)
    with path.open("r+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"\0")
            stream.flush()
        deadline, locked = time.monotonic() + 5, False
        try:
            while not locked:
                stream.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except OSError:
                    _require(time.monotonic() < deadline)
                    time.sleep(0.05)
            yield
        finally:
            if locked:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
