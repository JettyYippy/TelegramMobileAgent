import asyncio
import uuid
import time
from typing import Dict, Any, Callable, Awaitable, Optional

class ApprovalRequest:
    def __init__(self, action_id: str, tool_name: str, args: Dict[str, Any], summary: str, future: asyncio.Future):
        self.action_id = action_id
        self.tool_name = tool_name
        self.args = args
        self.summary = summary
        self.future = future
        self.created_at = time.time()

class ApprovalManager:
    """Coordinates interactive approval flow between agent tool execution and Telegram."""

    def __init__(self, timeout_seconds: int = 300):
        self.timeout_seconds = timeout_seconds
        self.pending_requests: Dict[str, ApprovalRequest] = {}

    def format_tool_summary(self, tool_name: str, args: Dict[str, Any], risk_reason: str = "") -> str:
        """Formats tool parameters into a clear, mobile-friendly markdown string."""
        header = f"🚨 **High-Risk Action:** {risk_reason}\n\n" if risk_reason else ""
        if tool_name == "run_command":
            cmd = args.get("CommandLine", "N/A")
            cwd = args.get("Cwd", "N/A")
            return f"{header}💻 **Command:** `{cmd}`\n📂 **Dir:** `{cwd}`"
        
        elif tool_name in ("write_to_file", "create_file"):
            target = args.get("TargetFile", args.get("target_file", "N/A"))
            overwrite = args.get("Overwrite", False)
            content = args.get("CodeContent", args.get("code_content", ""))
            preview = "\n".join(content.splitlines()[:8])
            if len(content.splitlines()) > 8:
                preview += "\n... (truncated)"
            return (
                f"{header}📝 **File:** `{target}`\n"
                f"🔄 **Overwrite:** `{'Yes' if overwrite else 'No'}`\n"
                f"**Preview:**\n```\n{preview}\n```"
            )
        
        elif tool_name in ("replace_file_content", "edit_file"):
            target = args.get("TargetFile", args.get("target_file", "N/A"))
            instruction = args.get("Instruction", "")
            return f"{header}✏️ **Edit File:** `{target}`\n💡 **Instruction:** {instruction}"
        
        else:
            formatted_args = "\n".join(f"- **{k}**: `{v}`" for k, v in list(args.items())[:5])
            return f"{header}⚙️ **Tool:** `{tool_name}`\n{formatted_args}"

    async def request_approval(
        self,
        tool_name: str,
        args: Dict[str, Any],
        send_prompt_fn: Callable[[str, str, str], Awaitable[None]],
        risk_reason: str = ""
    ) -> bool:
        """
        Pauses execution, sends Telegram notification with buttons, and awaits approval.
        Returns True if approved, False if rejected or timed out.
        """
        action_id = uuid.uuid4().hex[:8]
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()

        summary = self.format_tool_summary(tool_name, args, risk_reason=risk_reason)
        request = ApprovalRequest(action_id, tool_name, args, summary, future)
        self.pending_requests[action_id] = request

        try:
            # Send prompt to Telegram
            await send_prompt_fn(action_id, tool_name, summary)
            
            # Await user response via inline button
            approved = await asyncio.wait_for(future, timeout=self.timeout_seconds)
            return approved
        except asyncio.TimeoutError:
            if not future.done():
                future.set_result(False)
            return False
        finally:
            self.pending_requests.pop(action_id, None)

    def resolve(self, action_id: str, approved: bool) -> tuple[bool, Optional[ApprovalRequest]]:
        """Resolves a pending request based on user button tap."""
        request = self.pending_requests.get(action_id)
        if request and not request.future.done():
            request.future.set_result(approved)
            return True, request
        return False, request
