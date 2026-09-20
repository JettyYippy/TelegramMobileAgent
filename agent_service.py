import os
import asyncio
from pathlib import Path
from typing import Optional, Callable, Awaitable, Dict, Any

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig, types
from google.antigravity.hooks import hooks

from approval_manager import ApprovalManager
from risk_analyzer import is_high_risk
import config
from models_catalog import get_model_info, resolve_model_alias
from multi_provider_runner import (
    WorkspaceToolExecutor,
    run_openai_compatible_agent,
    run_anthropic_agent
)

# Tool names that modify files or execute terminal commands
MODIFYING_TOOLS = {
    "run_command",
    "write_to_file",
    "replace_file_content",
    "create_file",
    "edit_file",
    "manage_task"
}

PROVIDER_SIGNUP_LINKS = {
    "google": "https://aistudio.google.com/app/api-keys",
    "openai": "https://platform.openai.com/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
    "deepseek": "https://platform.deepseek.com/api_keys",
    "xai": "https://console.x.ai/"
}

class AgentService:
    def __init__(self, approval_manager: ApprovalManager):
        self.approval_manager = approval_manager
        self.workspace_dir = Path(config.DEFAULT_WORKSPACE).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        # Modes: "high_risk_only" (default), "safe" (all modifying), "strict" (all tools)
        self.review_mode = "high_risk_only"
        self.model_name = config.DEFAULT_MODEL
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

    def set_model(self, model_id: str) -> str:
        resolved = resolve_model_alias(model_id)
        if resolved:
            self.model_name = resolved
        else:
            self.model_name = model_id
        return self.model_name

    async def execute_prompt(
        self,
        prompt: str,
        on_thought: Optional[Callable[[str], Awaitable[None]]] = None,
        on_token: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """Executes a user prompt using either Antigravity (Gemini) or Multi-Provider Agent Runner."""
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

        model_info = get_model_info(self.model_name)
        provider = model_info.get("provider", "google") if model_info else "google"
        env_key = model_info.get("env_key", "GEMINI_API_KEY") if model_info else "GEMINI_API_KEY"
        model_title = model_info.get("title", self.model_name) if model_info else self.model_name
        
        api_key = os.getenv(env_key, getattr(config, env_key, "")).strip()

        if not api_key:
            link = PROVIDER_SIGNUP_LINKS.get(provider, "https://aistudio.google.com/app/api-keys")
            return (
                f"⚠️ **{model_title} API Key Missing**\n\n"
                f"To run tasks using `{model_title}`, please add your API key to the `.env` file on your desktop:\n"
                f"`{env_key}=your_api_key_here`\n\n"
                f"👉 Get your key here: {link}\n\n"
                f"Once saved in `.env`, send your prompt again and it will run automatically!"
            )

        self.is_running = True
        try:
            # -------------------------------------------------------------
            # NON-GOOGLE PROVIDERS: OpenAI, DeepSeek, xAI, Anthropic
            # -------------------------------------------------------------
            if provider in ("openai", "deepseek", "xai"):
                executor = WorkspaceToolExecutor(
                    workspace_dir=self.workspace_dir,
                    review_mode=self.review_mode,
                    approval_manager=self.approval_manager,
                    send_telegram_fn=self._send_telegram_fn
                )
                return await run_openai_compatible_agent(
                    model_info=model_info,
                    api_key=api_key,
                    prompt=prompt,
                    executor=executor,
                    on_thought=on_thought,
                    on_token=on_token
                )
            elif provider == "anthropic":
                executor = WorkspaceToolExecutor(
                    workspace_dir=self.workspace_dir,
                    review_mode=self.review_mode,
                    approval_manager=self.approval_manager,
                    send_telegram_fn=self._send_telegram_fn
                )
                return await run_anthropic_agent(
                    model_info=model_info,
                    api_key=api_key,
                    prompt=prompt,
                    executor=executor,
                    on_thought=on_thought,
                    on_token=on_token
                )

            # -------------------------------------------------------------
            # GOOGLE GEMINI: Native Google Antigravity Agent
            # -------------------------------------------------------------
            @hooks.pre_tool_call_decide
            async def decide_tool_permission(tool_call: types.ToolCall) -> types.HookResult:
                tool_name = getattr(tool_call, "name", str(tool_call))
                tool_args = getattr(tool_call, "args", {})

                if self.review_mode == "high_risk_only":
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
                "model": self.model_name,
                "retry_config": types.RetryConfig(
                    api_retry=types.ModelAPIRetryConfig(
                        max_retries=5,
                        initial_sleep_duration_ms=2000,
                        exponential_multiplier=2.0,
                    )
                ),
                "system_instructions": (
                    "You are an expert AI software engineer assistant controlled remotely via Telegram. "
                    "The user is reading your updates on their phone while you build and execute tasks on their desktop.\n\n"
                    "WORKSPACE RULES:\n"
                    "- You are strictly restricted to working within the configured workspace directory. "
                    "Do NOT attempt to read, search, or execute commands in parent directories outside this workspace.\n"
                    "- All new files and scripts must be created inside your active workspace directory.\n\n"
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

            async with Agent(config=agent_config) as agent:
                response = await agent.chat(prompt)

                if on_thought and hasattr(response, "thoughts"):
                    async def stream_thoughts():
                        try:
                            async for thought in response.thoughts:
                                await on_thought(thought)
                        except Exception:
                            pass
                    asyncio.create_task(stream_thoughts())

                final_text = []
                async for token in response:
                    final_text.append(token)
                    if on_token:
                        await on_token(token)

                return "".join(final_text)
        finally:
            self.is_running = False
