import asyncio
import unittest
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from approval_manager import ApprovalManager
from risk_analyzer import is_high_risk
from agent_service import AgentService
from models_catalog import AVAILABLE_MODELS, resolve_model_alias, format_models_list

class TestApprovalAndRisk(unittest.IsolatedAsyncioTestCase):

    def test_high_risk_detection(self):
        # Destructive commands that MUST be flagged as high risk
        high_risk_commands = [
            "rm -rf ./build",
            "rm -r node_modules",
            "rmdir /s /q temp",
            "del /f /s *.log",
            "git reset --hard HEAD~1",
            "git clean -fd",
            "DROP TABLE users;",
            "format D:"
        ]
        for cmd in high_risk_commands:
            risk, reason = is_high_risk("run_command", {"CommandLine": cmd})
            self.assertTrue(risk, f"Command '{cmd}' should have been flagged as high risk!")
            self.assertTrue(len(reason) > 0)

        # Safe normal commands that MUST NOT be flagged
        safe_commands = [
            "npm run test",
            "npx expo install @react-navigation/native",
            "git status",
            "git commit -m 'feat: added habit tracker'",
            "python main.py",
            "dir",
            "mkdir my_folder"
        ]
        for cmd in safe_commands:
            risk, _ = is_high_risk("run_command", {"CommandLine": cmd})
            self.assertFalse(risk, f"Command '{cmd}' should NOT be high risk!")

    def test_default_review_mode(self):
        manager = ApprovalManager()
        service = AgentService(manager)
        self.assertEqual(service.review_mode, "high_risk_only")

    async def test_tool_summary_formatting(self):
        manager = ApprovalManager()
        cmd_summary = manager.format_tool_summary(
            "run_command",
            {"CommandLine": "rm -rf node_modules", "Cwd": "/app"},
            risk_reason="Destructive command detected"
        )
        self.assertIn("High-Risk Action", cmd_summary)
        self.assertIn("rm -rf node_modules", cmd_summary)

    async def test_approval_resolution_allow(self):
        manager = ApprovalManager(timeout_seconds=5)
        
        async def mock_send(action_id, tool_name, summary):
            await asyncio.sleep(0.01)
            manager.resolve(action_id, approved=True)

        result = await manager.request_approval(
            tool_name="run_command",
            args={"CommandLine": "rm -rf /test"},
            send_prompt_fn=mock_send,
            risk_reason="Destructive rm -rf"
        )
        self.assertTrue(result)

    async def test_approval_resolution_deny(self):
        manager = ApprovalManager(timeout_seconds=5)
        
        async def mock_send(action_id, tool_name, summary):
            await asyncio.sleep(0.01)
            manager.resolve(action_id, approved=False)

        result = await manager.request_approval(
            tool_name="run_command",
            args={"CommandLine": "rmdir /s /q test"},
            send_prompt_fn=mock_send,
            risk_reason="Destructive rmdir /s"
        )
        self.assertFalse(result)

    def test_model_alias_resolution(self):
        self.assertEqual(resolve_model_alias("flash"), "gemini-2.5-flash")
        self.assertEqual(resolve_model_alias("2.5"), "gemini-2.5-flash")
        self.assertEqual(resolve_model_alias("pro"), "gemini-2.5-pro")
        self.assertEqual(resolve_model_alias("3.7"), "gemini-3.7-flash")
        self.assertEqual(resolve_model_alias("gemini-1.5-flash"), "gemini-1.5-flash")
        self.assertIsNone(resolve_model_alias("nonexistent-model"))

    def test_models_list_formatting(self):
        msg = format_models_list("gemini-2.5-flash")
        self.assertIn("gemini-2.5-flash", msg)
        self.assertIn("ACTIVE", msg)
        self.assertIn("15 RPM", msg)

if __name__ == "__main__":
    unittest.main()
