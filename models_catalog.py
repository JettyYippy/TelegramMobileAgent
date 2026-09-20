from typing import Dict, Any, Optional, List

AVAILABLE_MODELS: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------
    # 🌐 GOOGLE GEMINI
    # -------------------------------------------------------------
    "gemini-2.5-flash": {
        "title": "Gemini 2.5 Flash",
        "provider": "google",
        "env_key": "GEMINI_API_KEY",
        "api_model": "gemini-2.5-flash",
        "description": "⚡ High capability & fast agent execution (Best Default)",
        "free_rpm": "15 RPM",
        "paid_rpm": "1,000+ RPM",
        "recommended": True,
        "aliases": ["2.5", "flash", "2.5-flash", "gemini"]
    },
    "gemini-1.5-flash": {
        "title": "Gemini 1.5 Flash",
        "provider": "google",
        "env_key": "GEMINI_API_KEY",
        "api_model": "gemini-1.5-flash",
        "description": "🚀 Fast, rock-solid stability & lightweight tasks",
        "free_rpm": "15 RPM",
        "paid_rpm": "1,000+ RPM",
        "recommended": False,
        "aliases": ["1.5", "1.5-flash"]
    },
    "gemini-2.5-pro": {
        "title": "Gemini 2.5 Pro",
        "provider": "google",
        "env_key": "GEMINI_API_KEY",
        "api_model": "gemini-2.5-pro",
        "description": "🧠 Deep reasoning & multi-file architectural planning",
        "free_rpm": "2 RPM",
        "paid_rpm": "360+ RPM",
        "recommended": False,
        "aliases": ["gemini-pro", "2.5-pro", "pro"]
    },
    "gemini-3.7-flash": {
        "title": "Gemini 3.7 Flash",
        "provider": "google",
        "env_key": "GEMINI_API_KEY",
        "api_model": "gemini-3.7-flash",
        "description": "✨ Hybrid reasoning agent preview",
        "free_rpm": "5 RPM",
        "paid_rpm": "1,000+ RPM",
        "recommended": False,
        "aliases": ["3.7", "3.7-flash"]
    },

    # -------------------------------------------------------------
    # 🟢 OPENAI
    # -------------------------------------------------------------
    "gpt-4o": {
        "title": "GPT-4o",
        "provider": "openai",
        "env_key": "OPENAI_API_KEY",
        "api_model": "gpt-4o",
        "description": "🌟 Flagship multimodal intelligence & general coding",
        "free_rpm": "N/A (Paid only)",
        "paid_rpm": "500 - 10,000 RPM",
        "recommended": False,
        "aliases": ["4o", "gpt4o", "gpt-4"]
    },
    "gpt-4o-mini": {
        "title": "GPT-4o Mini",
        "provider": "openai",
        "env_key": "OPENAI_API_KEY",
        "api_model": "gpt-4o-mini",
        "description": "⚡ Ultra-fast & cost-effective coding daily driver",
        "free_rpm": "N/A (Paid only)",
        "paid_rpm": "500 - 10,000 RPM",
        "recommended": False,
        "aliases": ["4o-mini", "mini", "gpt-mini"]
    },
    "o3-mini": {
        "title": "o3-mini",
        "provider": "openai",
        "env_key": "OPENAI_API_KEY",
        "api_model": "o3-mini",
        "description": "🔬 Advanced STEM, algorithm & deep logic reasoning",
        "free_rpm": "N/A (Paid only)",
        "paid_rpm": "500 - 5,000 RPM",
        "recommended": False,
        "aliases": ["o3", "o3-mini"]
    },
    "o1": {
        "title": "o1",
        "provider": "openai",
        "env_key": "OPENAI_API_KEY",
        "api_model": "o1",
        "description": "🧠 Premier deep-thinking & complex problem solving",
        "free_rpm": "N/A (Paid only)",
        "paid_rpm": "500 - 1,000 RPM",
        "recommended": False,
        "aliases": ["o1"]
    },

    # -------------------------------------------------------------
    # 🟣 ANTHROPIC CLAUDE
    # -------------------------------------------------------------
    "claude-3-7-sonnet": {
        "title": "Claude 3.7 Sonnet",
        "provider": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "api_model": "claude-3-7-sonnet-20250219",
        "description": "👑 SOTA agentic coding flagship with hybrid reasoning",
        "free_rpm": "N/A (Paid only)",
        "paid_rpm": "1,000 - 4,000 RPM",
        "recommended": False,
        "aliases": ["claude-3.7", "sonnet-3.7", "claude-37", "sonnet37"]
    },
    "claude-3-5-sonnet": {
        "title": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "api_model": "claude-3-5-sonnet-20241022",
        "description": "🏆 Industry gold standard for autonomous coding agents",
        "free_rpm": "N/A (Paid only)",
        "paid_rpm": "1,000 - 4,000 RPM",
        "recommended": False,
        "aliases": ["claude-3.5", "sonnet", "claude"]
    },
    "claude-3-5-haiku": {
        "title": "Claude 3.5 Haiku",
        "provider": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "api_model": "claude-3-5-haiku-20241022",
        "description": "⚡ Ultra-fast execution & rapid responsiveness",
        "free_rpm": "N/A (Paid only)",
        "paid_rpm": "1,000 - 4,000 RPM",
        "recommended": False,
        "aliases": ["haiku", "claude-haiku"]
    },

    # -------------------------------------------------------------
    # 🔵 DEEPSEEK
    # -------------------------------------------------------------
    "deepseek-chat": {
        "title": "DeepSeek-V3",
        "provider": "deepseek",
        "env_key": "DEEPSEEK_API_KEY",
        "api_model": "deepseek-chat",
        "api_base": "https://api.deepseek.com",
        "description": "🚀 671B MoE model, top-tier coding at ultra-low cost",
        "free_rpm": "N/A (Pay-as-you-go)",
        "paid_rpm": "60 - 600+ RPM",
        "recommended": False,
        "aliases": ["deepseek", "v3", "deepseek-v3"]
    },
    "deepseek-reasoner": {
        "title": "DeepSeek-R1",
        "provider": "deepseek",
        "env_key": "DEEPSEEK_API_KEY",
        "api_model": "deepseek-reasoner",
        "api_base": "https://api.deepseek.com",
        "description": "🧠 Open reasoning model rivaling OpenAI o1",
        "free_rpm": "N/A (Pay-as-you-go)",
        "paid_rpm": "60 - 600+ RPM",
        "recommended": False,
        "aliases": ["r1", "deepseek-r1", "reasoner"]
    },

    # -------------------------------------------------------------
    # 🌌 xAI (GROK)
    # -------------------------------------------------------------
    "grok-2-latest": {
        "title": "Grok 2",
        "provider": "xai",
        "env_key": "XAI_API_KEY",
        "api_model": "grok-2-latest",
        "api_base": "https://api.x.ai/v1",
        "description": "🌌 Frontier LLM with real-time reasoning capabilities",
        "free_rpm": "N/A (Paid only)",
        "paid_rpm": "600+ RPM",
        "recommended": False,
        "aliases": ["grok", "grok-2"]
    }
}

PROVIDER_HEADERS = {
    "google": "🌐 **Google Gemini Models**",
    "openai": "🟢 **OpenAI Models**",
    "anthropic": "🟣 **Anthropic Claude Models**",
    "deepseek": "🔵 **DeepSeek Models**",
    "xai": "🌌 **xAI (Grok) Models**"
}

def resolve_model_alias(input_name: str) -> Optional[str]:
    """Resolves short aliases (e.g. '4o', 'sonnet', 'deepseek', 'flash') to canonical model identifiers."""
    cleaned = input_name.strip().lower()
    if cleaned in AVAILABLE_MODELS:
        return cleaned
    
    for model_id, info in AVAILABLE_MODELS.items():
        if cleaned in info.get("aliases", []):
            return model_id
            
    return None

def get_model_info(model_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full specification for a model identifier."""
    canonical = resolve_model_alias(model_id)
    if canonical:
        return AVAILABLE_MODELS.get(canonical)
    return None

def format_models_list(active_model_id: str, available_providers: Optional[List[str]] = None) -> str:
    """Formats the models catalog categorized by provider for mobile display."""
    lines = ["🤖 **Supported Multi-Provider Models & Rate Limits**\n"]
    
    # Group by provider
    grouped: Dict[str, List[tuple]] = {}
    for model_id, info in AVAILABLE_MODELS.items():
        provider = info.get("provider", "other")
        grouped.setdefault(provider, []).append((model_id, info))
        
    for provider, header in PROVIDER_HEADERS.items():
        if provider not in grouped:
            continue
            
        lines.append(f"{header}")
        for model_id, info in grouped[provider]:
            is_active = (model_id == active_model_id)
            active_tag = "👉 **[ACTIVE]** " if is_active else ""
            recommended_tag = "⭐ _Recommended_ " if info.get("recommended") else ""
            
            lines.append(
                f"{active_tag}• **{info['title']}** (`{model_id}`) {recommended_tag}\n"
                f"  {info['description']}\n"
                f"  Limits: Free `{info['free_rpm']}` | Paid `{info['paid_rpm']}`"
            )
        lines.append("")
        
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("👉 **Switch model:** `/model <name>` (e.g. `/model 4o`, `/model sonnet`, `/model deepseek`, `/model 2.5-flash`)")
    return "\n".join(lines)
