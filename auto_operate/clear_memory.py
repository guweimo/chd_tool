"""
Windows Memory Cleaner - Process Service (Standalone)
Handles single/batch process memory optimization and enumeration.

Zero external dependencies — only uses Python standard library (ctypes).

Provides:
  - trim_process_working_set(pid)   — optimize one process
  - enumerate_processes()           — list all processes
  - find_process_by_name(name)      — search by name
  - get_process_memory_usage(pid)   — query memory usage
"""

import ctypes
from ctypes import wintypes, byref, c_void_p, c_ulonglong, c_bool, c_int
from dataclasses import dataclass
from typing import Optional, List


# ---------------------------------------------------------------------------
# Native Methods (self-contained, no import from native_methods.py)
# ---------------------------------------------------------------------------

class _NativeMethods:
    """Minimal Windows API declarations needed by this module."""

    _kernel32 = ctypes.windll.kernel32
    _psapi = ctypes.windll.psapi

    # --- OpenProcess ---
    _OpenProcess = _kernel32.OpenProcess
    _OpenProcess.argtypes = [c_ulonglong, c_bool, c_ulonglong]
    _OpenProcess.restype = c_void_p

    @staticmethod
    def open_process(access, inherit_handle, process_id):
        return _NativeMethods._OpenProcess(access, inherit_handle, process_id)

    # --- CloseHandle ---
    _CloseHandle = _kernel32.CloseHandle
    _CloseHandle.argtypes = [c_void_p]
    _CloseHandle.restype = c_bool

    @staticmethod
    def close_handle(handle):
        return _NativeMethods._CloseHandle(handle)

    # --- EmptyWorkingSet ---
    _EmptyWorkingSet = _psapi.EmptyWorkingSet
    _EmptyWorkingSet.argtypes = [c_void_p]
    _EmptyWorkingSet.restype = c_bool

    @staticmethod
    def empty_working_set(process_handle):
        return _NativeMethods._EmptyWorkingSet(process_handle)

    # --- CreateToolhelp32Snapshot ---
    _CreateToolhelp32Snapshot = _kernel32.CreateToolhelp32Snapshot
    _CreateToolhelp32Snapshot.argtypes = [c_ulonglong, c_ulonglong]
    _CreateToolhelp32Snapshot.restype = c_void_p

    @staticmethod
    def create_toolhelp32_snapshot(flags, process_id=0):
        return _NativeMethods._CreateToolhelp32Snapshot(flags, process_id)

    # --- PROCESSENTRY32W ---
    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(c_ulonglong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", c_int),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    # --- Process32FirstW ---
    _Process32FirstW = _kernel32.Process32FirstW
    _Process32FirstW.argtypes = [c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
    _Process32FirstW.restype = c_bool

    @staticmethod
    def process32_first(snapshot, entry):
        return _NativeMethods._Process32FirstW(snapshot, entry)

    # --- Process32NextW ---
    _Process32NextW = _kernel32.Process32NextW
    _Process32NextW.argtypes = [c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
    _Process32NextW.restype = c_bool

    @staticmethod
    def process32_next(snapshot, entry):
        return _NativeMethods._Process32NextW(snapshot, entry)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    name: str
    parent_pid: int = 0
    thread_count: int = 0

    def __repr__(self):
        return f"ProcessInfo(pid={self.pid}, name='{self.name}')"


@dataclass
class OptimizationResult:
    """Result of an optimization operation."""
    success: bool
    message: str = ""
    processes_trimmed: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# MemoryType constants (inline, no import from enums.py)
# ---------------------------------------------------------------------------

class _MemoryType:
    """Memory type flags — inline copy to avoid external dependency."""
    NONE = 0
    WORKING_SETS = 1 << 3  # 8


# ---------------------------------------------------------------------------
# ProcessService — fully standalone
# ---------------------------------------------------------------------------

class ProcessService:
    """Service for per-process memory optimization and enumeration.

    Fully self-contained — no imports from other project modules.

    Usage:
        svc = ProcessService()

        # Optimize a single process
        result = svc.trim_process_working_set(1234)

        # Optimize multiple processes
        result = svc.optimize_processes([1234, 5678])

        # Enumerate all processes
        procs = svc.enumerate_processes()

        # Find by name
        chrome = svc.find_process_by_name("chrome.exe")
    """

    # Process access rights
    PROCESS_ALL_ACCESS = 0x1F0FFF
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    PROCESS_VM_WRITE = 0x0020
    PROCESS_VM_OPERATION = 0x0008

    # Toolhelp snapshot flags
    TH32CS_SNAPPROCESS = 0x00000002

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Single process optimization (core atomic operation)
    # ------------------------------------------------------------------

    def trim_process_working_set(self, pid: int) -> OptimizationResult:
        """Empty the working set of a single process.

        Args:
            pid: Target process ID.

        Returns:
            OptimizationResult with success status and message.
        """
        if pid == 0 or pid == 4:
            return OptimizationResult(
                success=False,
                message=f"Cannot optimize system process (PID {pid}).",
            )

        handle = None
        try:
            handle = _NativeMethods.open_process(self.PROCESS_ALL_ACCESS, False, pid)
            if not handle:
                return OptimizationResult(
                    success=False,
                    message=f"Failed to open process PID {pid}. Access denied?",
                )

            if _NativeMethods.empty_working_set(handle):
                return OptimizationResult(
                    success=True,
                    message=f"Working set trimmed for PID {pid}.",
                    processes_trimmed=1,
                )
            else:
                return OptimizationResult(
                    success=False,
                    message=f"EmptyWorkingSet failed for PID {pid}.",
                )
        except Exception as e:
            return OptimizationResult(
                success=False,
                message=f"Error trimming PID {pid}: {e}",
                error=str(e),
            )
        finally:
            if handle:
                _NativeMethods.close_handle(handle)

    def optimize_process(self, pid: int, memory_type: int = None) -> OptimizationResult:
        """Optimize a single process by PID.

        Per-process optimization only supports WORKING_SETS.

        Args:
            pid: Target process ID.
            memory_type: Must be WORKING_SETS (ignored otherwise).

        Returns:
            OptimizationResult
        """
        if memory_type is None:
            memory_type = _MemoryType.WORKING_SETS

        if memory_type != _MemoryType.WORKING_SETS and not (memory_type & _MemoryType.WORKING_SETS):
            return OptimizationResult(
                success=False,
                message="Per-process optimization only supports WORKING_SETS.",
            )

        return self.trim_process_working_set(pid)

    def optimize_processes(self, pids: List[int], memory_type: int = None) -> OptimizationResult:
        """Optimize multiple processes by their PIDs.

        Args:
            pids: List of target process IDs.
            memory_type: Must be WORKING_SETS (ignored otherwise).

        Returns:
            OptimizationResult with aggregate results.
        """
        if memory_type is None:
            memory_type = _MemoryType.WORKING_SETS

        total = len(pids)
        trimmed = 0
        failed = []

        for pid in pids:
            result = self.trim_process_working_set(pid)
            if result.success:
                trimmed += result.processes_trimmed
            else:
                failed.append(f"PID {pid}: {result.error}")

        msg = f"Trimmed {trimmed}/{total} processes."
        if failed:
            msg += f" Failed: {'; '.join(failed)}"

        return OptimizationResult(
            success=len(failed) == 0,
            message=msg,
            processes_trimmed=trimmed,
            error="; ".join(failed) if failed else None,
        )

    # ------------------------------------------------------------------
    # Process enumeration
    # ------------------------------------------------------------------

    def enumerate_processes(self) -> List[ProcessInfo]:
        """Enumerate all running processes.

        Returns:
            List of ProcessInfo objects.
        """
        processes = []
        snapshot = _NativeMethods.create_toolhelp32_snapshot(self.TH32CS_SNAPPROCESS)
        if snapshot == c_void_p(-1).value:
            return processes

        try:
            entry = _NativeMethods.PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(_NativeMethods.PROCESSENTRY32W)

            if _NativeMethods.process32_first(snapshot, byref(entry)):
                while True:
                    processes.append(ProcessInfo(
                        pid=entry.th32ProcessID,
                        name=entry.szExeFile,
                        parent_pid=entry.th32ParentProcessID,
                        thread_count=entry.cntThreads,
                    ))

                    if not _NativeMethods.process32_next(snapshot, byref(entry)):
                        break
        finally:
            _NativeMethods.close_handle(snapshot)

        return processes

    def find_process_by_name(self, name: str) -> List[ProcessInfo]:
        """Find processes by name (case-insensitive).

        Args:
            name: Process name (e.g. 'chrome.exe' or 'chrome').

        Returns:
            List of matching ProcessInfo objects.
        """
        name_lower = name.lower()
        if not name_lower.endswith(".exe"):
            name_lower += ".exe"

        return [p for p in self.enumerate_processes() if p.name.lower() == name_lower]

    def empty_all_working_sets(self, exclude_pids: Optional[set] = None) -> int:
        """Empty working sets of all running processes.

        Args:
            exclude_pids: Optional set of PIDs to skip.

        Returns:
            Number of processes trimmed.
        """
        count = 0
        exclude = exclude_pids or set()
        snapshot = _NativeMethods.create_toolhelp32_snapshot(self.TH32CS_SNAPPROCESS)
        if snapshot == c_void_p(-1).value:
            return 0

        try:
            entry = _NativeMethods.PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(_NativeMethods.PROCESSENTRY32W)

            if _NativeMethods.process32_first(snapshot, byref(entry)):
                while True:
                    process_id = entry.th32ProcessID
                    if process_id not in exclude and process_id != 0 and process_id != 4:
                        result = self.trim_process_working_set(process_id)
                        if result.success:
                            count += 1

                    if not _NativeMethods.process32_next(snapshot, byref(entry)):
                        break
        finally:
            _NativeMethods.close_handle(snapshot)

        return count

    # ------------------------------------------------------------------
    # Process memory query
    # ------------------------------------------------------------------

    def get_process_memory_usage(self, pid: int) -> Optional[int]:
        """Get the working set size of a process.

        Args:
            pid: Process ID.

        Returns:
            Working set size in bytes, or None if unavailable.
        """
        # Try psutil first (optional)
        try:
            import psutil
            proc = psutil.Process(pid)
            return proc.memory_info().rss
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback: use ctypes + psapi
        try:
            handle = _NativeMethods.open_process(
                self.PROCESS_QUERY_INFORMATION | self.PROCESS_VM_READ, False, pid
            )
            if not handle:
                return None

            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            result = ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, byref(counters), counters.cb
            )
            _NativeMethods.close_handle(handle)

            if result:
                return counters.WorkingSetSize
        except Exception:
            pass

        return None


def main():
    svc = ProcessService()
    procs = svc.find_process_by_name("chrome.exe")
    pids = [p.pid for p in procs]
    result = svc.optimize_processes(pids)


if __name__ == "__main__":
    main()

