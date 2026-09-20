import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Callable, Awaitable, Dict, Any, List

from approval_manager import ApprovalManager
from risk_analyzer import is_high_risk
import config

MODIFYING_TOOLS = {
    "run_command",
    "write_to_file",
    "replace_file_content",
    "create_file",
    "edit_file"
}

SYSTEM_INSTRUCTIONS = (
    "You are an expert autonomous software engineer agent controlled remotely via Telegram. "
    "The user is reading your updates on their phone while you build, edit, and test software on their desktop computer.\n\n"
    "WORKSPACE RULES:\n"
    "- You are strictly restricted to working within the configured workspace directory. "
    "Do NOT attempt to read, write, or execute commands outside this workspace.\n"
    "- All new files, code, tests, and scripts must be created inside your active workspace directory.\n\n"
    "MANDATORY PROTOCOL:\n"
    "Before executing any tool calls to write files or run commands, you MUST ALWAYS output a concise "
    "summary of the request and your planned implementation (2-4 bullet points) under the heading:\n"
    "📋 Summary & Implementation Plan:\n"
    "• What was requested\n"
    "• Files to create or modify\n"
    "• Key commands to run\n\n"
    "After writing this summary, proceed immediately with tool calls to implement the solution. "
    "Safe operations (creating files, reading files, standard dev commands) execute automatically. "
    "Only high-risk destructive operations (e.g. rm -rf, rmdir /s) will pause for the user to tap Approve on Telegram."
)

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command inside the workspace directory (e.g. tests, npm install, python scripts, git).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact shell command line string to execute."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_to_file",
            "description": "Write or overwrite content to a file inside the workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path within the workspace directory."
                    },
                    "content": {
                        "type": "string",
                        "description": "The complete text content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents from the workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path to read."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and subdirectories in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path (optional, default is root of workspace)."
                    }
                }
            }
        }
    }
]

CLAUDE_TOOLS = [
    {
        "name": "run_command",
        "description": "Execute a shell command inside the workspace directory (e.g. tests, npm install, python scripts, git).",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The exact shell command line string to execute."
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "write_to_file",
        "description": "Write or overwrite content to a file inside the workspace directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative file path within the workspace directory."
                },
                "content": {
                    "type": "string",
                    "description": "The complete text content to write into the file."
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "Read file contents from the workspace directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative file path to read."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_dir",
        "description": "List files and subdirectories in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path (optional, default is root of workspace)."
                }
            }
        }
    }
]

class WorkspaceToolExecutor:
    """Safely executes workspace tools with permission gating and boundary protection."""

    def __init__(
        self,
        workspace_dir: Path,
        review_mode: str,
        approval_manager: ApprovalManager,
        send_telegram_fn: Optional[Callable[[str, str, str], Awaitable[None]]] = None
    ):
        self.workspace_dir = workspace_dir.resolve()
        self.review_mode = review_mode
        self.approval_manager = approval_manager
        self.send_telegram_fn = send_telegram_fn

    def _resolve_safe_path(self, relative_path: str) -> Optional[Path]:
        target = (self.workspace_dir / relative_path).resolve()
        try:
            target.relative_to(self.workspace_dir)
            return target
        except ValueError:
            return None

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Dispatches tool execution with review mode and approval checks."""
        # 1. Approval gating
        if self.review_mode == "high_risk_only":
            if tool_name == "run_command":
                cmd = args.get("command", "")
                high_risk, reason = is_high_risk("run_command", {"CommandLine": cmd})
                if high_risk:
                    if not self.send_telegram_fn:
                        return "Error: Action blocked (no Telegram approval sender available)."
                    approved = await self.approval_manager.request_approval(
                        tool_name="run_command",
                        args={"CommandLine": cmd, "Cwd": str(self.workspace_dir)},
                        send_prompt_fn=self.send_telegram_fn,
                        risk_reason=reason
                    )
                    if not approved:
                        return "Action aborted: Denied by user tap or timed out."
        elif self.review_mode == "safe":
            if tool_name in MODIFYING_TOOLS:
                if not self.send_telegram_fn:
                    return "Error: Action blocked (no Telegram approval sender available)."
                approved = await self.approval_manager.request_approval(
                    tool_name=tool_name,
                    args=args,
                    send_prompt_fn=self.send_telegram_fn
                )
                if not approved:
                    return "Action aborted: Denied by user tap or timed out."
        else:  # strict mode
            if not self.send_telegram_fn:
                return "Error: Action blocked (no Telegram approval sender available)."
            approved = await self.approval_manager.request_approval(
                tool_name=tool_name,
                args=args,
                send_prompt_fn=self.send_telegram_fn
            )
            if not approved:
                return "Action aborted: Denied by user tap or timed out."

        # 2. Tool dispatch
        if tool_name == "run_command":
            return await self._run_command(args.get("command", ""))
        elif tool_name == "write_to_file":
            return await self._write_to_file(args.get("path", ""), args.get("content", ""))
        elif tool_name == "read_file":
            return await self._read_file(args.get("path", ""))
        elif tool_name == "list_dir":
            return await self._list_dir(args.get("path", "."))
        else:
            return f"Error: Unknown tool '{tool_name}'."

    async def _run_command(self, command: str) -> str:
        if not command.strip():
            return "Error: Empty command."
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.workspace_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
            out_str = stdout.decode("utf-8", errors="replace").strip()
            err_str = stderr.decode("utf-8", errors="replace").strip()
            code = process.returncode
            
            output_parts = [f"Exit Code: {code}"]
            if out_str:
                output_parts.append(f"STDOUT:\n{out_str[:4000]}")
            if err_str:
                output_parts.append(f"STDERR:\n{err_str[:4000]}")
            return "\n\n".join(output_parts)
        except asyncio.TimeoutError:
            return "Error: Command timed out after 120 seconds."
        except Exception as e:
            return f"Error executing command: {str(e)}"

    async def _write_to_file(self, rel_path: str, content: str) -> str:
        target = self._resolve_safe_path(rel_path)
        if not target:
            return f"Access Denied: Path '{rel_path}' is outside active workspace."
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Success: File '{rel_path}' written successfully ({len(content)} characters)."
        except Exception as e:
            return f"Error writing file: {str(e)}"

    async def _read_file(self, rel_path: str) -> str:
        target = self._resolve_safe_path(rel_path)
        if not target:
            return f"Access Denied: Path '{rel_path}' is outside active workspace."
        if not target.exists():
            return f"Error: File '{rel_path}' not found."
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            if len(content) > 10000:
                return content[:10000] + f"\n\n... [Truncated, total {len(content)} characters]"
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"

    async def _list_dir(self, rel_path: str = ".") -> str:
        target = self._resolve_safe_path(rel_path)
        if not target:
            return f"Access Denied: Path '{rel_path}' is outside active workspace."
        if not target.exists():
            return f"Error: Directory '{rel_path}' does not exist."
        try:
            entries = []
            for item in sorted(target.iterdir()):
                prefix = "📁 " if item.is_dir() else "📄 "
                entries.append(f"{prefix}{item.name}")
            return "\n".join(entries) if entries else "(Empty directory)"
        except Exception as e:
            return f"Error listing directory: {str(e)}"


async def run_openai_compatible_agent(
    model_info: Dict[str, Any],
    api_key: str,
    prompt: str,
    executor: WorkspaceToolExecutor,
    on_thought: Optional[Callable[[str], Awaitable[None]]] = None,
    on_token: Optional[Callable[[str], Awaitable[None]]] = None
) -> str:
    """Runs autonomous agent loop using OpenAI standard API (OpenAI, DeepSeek, xAI)."""
    from openai import AsyncOpenAI
    
    base_url = model_info.get("api_base")
    api_model = model_info.get("api_model", model_info.get("title", "gpt-4o"))
    
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": prompt}
    ]
    
    max_turns = 15
    current_turn = 0
    
    while current_turn < max_turns:
        current_turn += 1
        try:
            response = await client.chat.completions.create(
                model=api_model,
                messages=messages,
                tools=OPENAI_TOOLS,
                tool_choice="auto"
            )
        except Exception as e:
            return f"❌ API Error from {model_info.get('title', 'AI Provider')}: {str(e)}"
            
        choice = response.choices[0]
        msg = choice.message
        
        # Check tool calls
        if msg.tool_calls:
            assistant_msg = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in msg.tool_calls
                ]
            }
            messages.append(assistant_msg)
            
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except Exception:
                    fn_args = {}
                    
                if on_thought:
                    cmd_detail = fn_args.get("command") or fn_args.get("path") or ""
                    await on_thought(f"Running `{fn_name}`: {cmd_detail}")
                    
                tool_output = await executor.execute_tool(fn_name, fn_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_output
                })
        else:
            # Final text response
            content = msg.content or ""
            if on_token:
                await on_token(content)
            return content
            
    return "Agent completed multi-turn workflow."


async def run_anthropic_agent(
    model_info: Dict[str, Any],
    api_key: str,
    prompt: str,
    executor: WorkspaceToolExecutor,
    on_thought: Optional[Callable[[str], Awaitable[None]]] = None,
    on_token: Optional[Callable[[str], Awaitable[None]]] = None
) -> str:
    """Runs autonomous agent loop using Anthropic Claude API."""
    import anthropic
    
    api_model = model_info.get("api_model", "claude-3-7-sonnet-20250219")
    client = anthropic.AsyncAnthropic(api_key=api_key)
    
    messages = [
        {"role": "user", "content": prompt}
    ]
    
    max_turns = 15
    current_turn = 0
    
    while current_turn < max_turns:
        current_turn += 1
        try:
            response = await client.messages.create(
                model=api_model,
                max_tokens=4096,
                system=SYSTEM_INSTRUCTIONS,
                messages=messages,
                tools=CLAUDE_TOOLS
            )
        except Exception as e:
            return f"❌ Anthropic API Error: {str(e)}"
            
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b.text for b in response.content if b.type == "text"]
        
        if tool_uses:
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            
            for tu in tool_uses:
                fn_name = tu.name
                fn_args = tu.input
                
                if on_thought:
                    cmd_detail = fn_args.get("command") or fn_args.get("path") or ""
                    await on_thought(f"Running `{fn_name}`: {cmd_detail}")
                    
                tool_output = await executor.execute_tool(fn_name, fn_args)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": tool_output
                })
                
            messages.append({"role": "user", "content": tool_results})
        else:
            final_text = "".join(text_blocks)
            if on_token:
                await on_token(final_text)
            return final_text
            
    return "Agent completed multi-turn workflow."
