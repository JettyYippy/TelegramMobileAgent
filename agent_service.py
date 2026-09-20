import os
import asyncio
from pathlib import Path
from typing import Optional, Callable, Awaitable, Dict, Any

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig, types
from google.antigravity.hooks import hooks

from approval_manager import ApprovalManager
from risk_analyzer import is_high_risk
import config

# Tool names that modify files or execute terminal commands
MODIFYING_TOOLS = {
    "run_command",
    "write_to_file",
    "replace_file_content",
    "create_file",
    "edit_file",
    "manage_task"
}

class AgentService:
    def __init__(self, approval_manager: ApprovalManager):
        self.approval_manager = approval_manager
        self.workspace_dir = Path(config.DEFAULT_WORKSPACE).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        # Modes: "high_risk_only" (default), "safe" (all modifying), "strict" (all tools)
        self.review_mode = "high_risk_only"
        self.is_running = False
        self._send_telegram_fn: Optional[Callable[[str, str, str], Awaitable[None]]] = None

    def set_telegram_sender(self, send_fn: Callable[[str, str, str], Awaitable[None]]):
        self._send_telegram_fn = send_fn

    def set_workspace(self, path_str: str) -> Path:
        target_path = Path(path_str).resolve()
        target_path.mkdir(parents=True, exist_ok=True)
        self.workspace_dir = target_path
        return self.workspace_dir

    def set_review_mode(self, mode: str):
        if mode in ("high_risk_only", "safe", "strict"):
            self.review_mode = mode

    async def execute_prompt(
        self,
        prompt: str,
        on_thought: Optional[Callable[[str], Awaitable[None]]] = None,
        on_token: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """Executes a user prompt using Antigravity Agent with pre-tool permission interception."""
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)
        api_key = os.getenv("GEMINI_API_KEY", config.GEMINI_API_KEY).strip()

        if not api_key:
            return (
                "⚠️ **Gemini API Key Missing**\n\n"
                "To start running agent tasks from your phone, please add your Gemini API key to the `.env` file on your desktop:\n"
                "`GEMINI_API_KEY=your_key`\n\n"
                "👉 Get your free key here: https://aistudio.google.com/app/api-keys\n\n"
                "Once saved in `.env`, send your prompt again and it will run automatically!"
            )

        self.is_running = True

        # Pre-tool decision hook
        @hooks.pre_tool_call_decide
        async def decide_tool_permission(tool_call: types.ToolCall) -> types.HookResult:
            tool_name = getattr(tool_call, "name", str(tool_call))
            tool_args = getattr(tool_call, "args", {})

            if self.review_mode == "high_risk_only":
                # Only prompt for high-risk destructive commands (e.g. rm -rf, rmdir /s, del /f)
                high_risk, reason = is_high_risk(tool_name, tool_args)
                if not high_risk:
                    return types.HookResult(allow=True)
                
                if not self._send_telegram_fn:
                    return types.HookResult(allow=False)
                
                approved = await self.approval_manager.request_approval(
                    tool_name=tool_name,
                    args=tool_args,
                    send_prompt_fn=self._send_telegram_fn,
                    risk_reason=reason
                )
                return types.HookResult(allow=approved)

            elif self.review_mode == "safe":
                # Ask for any modifying tool
                if tool_name not in MODIFYING_TOOLS:
                    return types.HookResult(allow=True)

                if not self._send_telegram_fn:
                    return types.HookResult(allow=False)

                approved = await self.approval_manager.request_approval(
                    tool_name=tool_name,
                    args=tool_args,
                    send_prompt_fn=self._send_telegram_fn
                )
                return types.HookResult(allow=approved)

            else:  # strict mode
                if not self._send_telegram_fn:
                    return types.HookResult(allow=False)
                approved = await self.approval_manager.request_approval(
                    tool_name=tool_name,
                    args=tool_args,
                    send_prompt_fn=self._send_telegram_fn
                )
                return types.HookResult(allow=approved)

        agent_kwargs = {
            "workspaces": [str(self.workspace_dir)],
            "api_key": api_key,
            "system_instructions": (
                "You are an expert AI software engineer assistant controlled remotely via Telegram. "
                "The user is reading your updates on their phone while you build and execute tasks on their desktop.\n\n"
                "MANDATORY PROTOCOL:\n"
                "Before executing any tool calls to write files or run commands, you MUST ALWAYS output a concise "
                "summary of the request and your planned implementation (2-4 bullet points) under the heading:\n"
                "📋 Summary & Implementation Plan:\n"
                "• What was requested\n"
                "• Files to create or modify\n"
                "• Key commands to run\n\n"
                "After writing this summary, proceed immediately with the implementation. "
                "Safe operations (creating files, standard commands) execute automatically. "
                "Only high-risk destructive operations (e.g. rm -rf, rmdir /s) will pause for user approval."
            ),
            "capabilities": CapabilitiesConfig(),
            "hooks": [decide_tool_permission],
        }

        agent_config = LocalAgentConfig(**agent_kwargs)

        try:
            async with Agent(config=agent_config) as agent:
                response = await agent.chat(prompt)

                # Stream thoughts if supported
                if on_thought and hasattr(response, "thoughts"):
                    async def stream_thoughts():
                        try:
                            async for thought in response.thoughts:
                                await on_thought(thought)
                        except Exception:
                            pass
                    asyncio.create_task(stream_thoughts())

                # Collect response text
                final_text = []
                async for token in response:
                    final_text.append(token)
                    if on_token:
                        await on_token(token)

                return "".join(final_text)
        finally:
            self.is_running = False
