"""
Zye Office Integration Health
Performs non-invasive diagnostic health checks across all Office automation subsystems.
"""

from typing import Dict, Any, List, Optional
import os
import sys
import time

from zye_office.models import OfficeAppType
from zye_office.com_worker import STACOMWorker
from zye_office.app_registry import OfficeAppRegistry
from zye_office.session_manager import OfficeSessionManager
from zye_office.operation_registry import OfficeOperationRegistry
from zye_office.capability_registry import OfficeCapabilityRegistry


class OfficeIntegrationHealth:
    """
    Subsystem health diagnostic checker for Day 20 Office Live COM Automation.
    """

    def __init__(
        self,
        worker: Optional[STACOMWorker] = None,
        registry: Optional[OfficeAppRegistry] = None,
        session_manager: Optional[OfficeSessionManager] = None,
        op_registry: Optional[OfficeOperationRegistry] = None,
        cap_registry: Optional[OfficeCapabilityRegistry] = None,
    ):
        self.worker = worker
        self.registry = registry or OfficeAppRegistry()
        self.session_manager = session_manager or OfficeSessionManager()
        self.op_registry = op_registry or OfficeOperationRegistry()
        self.cap_registry = cap_registry or OfficeCapabilityRegistry()

    def run_health_check(self) -> Dict[str, Any]:
        """
        Runs comprehensive, non-destructive health checks across all Office subsystems.
        """
        start_time = time.time()
        results: Dict[str, Any] = {
            "timestamp": time.time(),
            "status": "healthy",
            "checks": {},
        }

        # 1. COM Subsystem Check
        try:
            import pythoncom
            import win32com.client
            results["checks"]["com_subsystem"] = {
                "status": "PASS",
                "details": "pythoncom and win32com.client available",
            }
        except ImportError as e:
            results["checks"]["com_subsystem"] = {
                "status": "FAIL",
                "error": str(e),
            }
            results["status"] = "unhealthy"

        # 2. STA COM Worker Check
        if self.worker and self.worker.is_alive():
            try:
                ping_res = self.worker.run(lambda: "pong")
                results["checks"]["sta_worker"] = {
                    "status": "PASS" if ping_res == "pong" else "FAIL",
                    "details": "Dedicated STA worker thread responding",
                }
            except Exception as e:
                results["checks"]["sta_worker"] = {
                    "status": "FAIL",
                    "error": str(e),
                }
                results["status"] = "degraded"
        else:
            results["checks"]["sta_worker"] = {
                "status": "IDLE",
                "details": "STA worker not currently running or not provided",
            }

        # 3. Application Discovery Check
        try:
            discovered = self.registry.discover_all()
            installed = [app.value for app, info in discovered.items() if info.is_installed]
            results["checks"]["application_discovery"] = {
                "status": "PASS",
                "installed_apps": installed,
                "total_tracked": len(discovered),
            }
        except Exception as e:
            results["checks"]["application_discovery"] = {
                "status": "FAIL",
                "error": str(e),
            }
            results["status"] = "degraded"

        # 4. Session Manager Check
        try:
            sessions = self.session_manager.list_sessions()
            results["checks"]["session_manager"] = {
                "status": "PASS",
                "active_sessions_count": len(sessions),
                "metadata_file": self.session_manager.metadata_path,
            }
        except Exception as e:
            results["checks"]["session_manager"] = {
                "status": "FAIL",
                "error": str(e),
            }
            results["status"] = "degraded"

        # 5. Operation Registry Check
        try:
            all_ops = self.op_registry.list_operations()
            results["checks"]["operation_registry"] = {
                "status": "PASS",
                "registered_operations_count": len(all_ops),
            }
        except Exception as e:
            results["checks"]["operation_registry"] = {
                "status": "FAIL",
                "error": str(e),
            }
            results["status"] = "degraded"

        # 6. Capability Registry Check
        try:
            all_caps = self.cap_registry.get_all_capabilities()
            results["checks"]["capability_registry"] = {
                "status": "PASS",
                "capabilities_count": len(all_caps),
            }
        except Exception as e:
            results["checks"]["capability_registry"] = {
                "status": "FAIL",
                "error": str(e),
            }
            results["status"] = "degraded"

        # 7. Export Directory Check
        try:
            export_dir = os.path.join(os.getcwd(), "data", "exports")
            os.makedirs(export_dir, exist_ok=True)
            test_file = os.path.join(export_dir, ".health_probe")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            results["checks"]["export_subsystem"] = {
                "status": "PASS",
                "directory": export_dir,
                "writable": True,
            }
        except Exception as e:
            results["checks"]["export_subsystem"] = {
                "status": "FAIL",
                "error": str(e),
            }
            results["status"] = "degraded"

        results["elapsed_ms"] = round((time.time() - start_time) * 1000, 2)
        return results
