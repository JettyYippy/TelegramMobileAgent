from typing import Dict, Any, Optional

AVAILABLE_MODELS: Dict[str, Dict[str, Any]] = {
    "gemini-2.5-flash": {
        "title": "Gemini 2.5 Flash",
        "description": "⚡ High capability & fast execution (Best Default)",
        "free_rpm": 15,
        "paid_rpm": "1,000+",
        "recommended": True,
        "aliases": ["2.5", "flash", "2.5-flash"]
    },
    "gemini-1.5-flash": {
        "title": "Gemini 1.5 Flash",
        "description": "🚀 Fast, highly stable & lightweight",
        "free_rpm": 15,
        "paid_rpm": "1,000+",
        "recommended": False,
        "aliases": ["1.5", "1.5-flash"]
    },
    "gemini-2.5-pro": {
        "title": "Gemini 2.5 Pro",
        "description": "🧠 Deep reasoning & complex architecture",
        "free_rpm": 2,
        "paid_rpm": "360+",
        "recommended": False,
        "aliases": ["pro", "2.5-pro"]
    },
    "gemini-3.7-flash": {
        "title": "Gemini 3.7 Flash",
        "description": "✨ Hybrid reasoning agent model",
        "free_rpm": 5,
        "paid_rpm": "1,000+",
        "recommended": False,
        "aliases": ["3.7", "3.7-flash"]
    },
    "gemini-3.8-flash": {
        "title": "Gemini 3.8 Flash",
        "description": "🔬 Experimental preview model",
        "free_rpm": 5,
        "paid_rpm": "1,000+",
        "recommended": False,
        "aliases": ["3.8", "3.8-flash"]
    }
}

def resolve_model_alias(input_name: str) -> Optional[str]:
    """Resolves short aliases (e.g. 'flash', '2.5', 'pro') to canonical model identifiers."""
    cleaned = input_name.strip().lower()
    if cleaned in AVAILABLE_MODELS:
        return cleaned
    
    for model_id, info in AVAILABLE_MODELS.items():
        if cleaned in info.get("aliases", []):
            return model_id
            
    return None

def format_models_list(active_model_id: str) -> str:
    """Formats the models catalog and their RPMs for mobile display."""
    lines = ["🤖 **Available Gemini Models & Rate Limits**\n"]
    
    for model_id, info in AVAILABLE_MODELS.items():
        is_active = (model_id == active_model_id)
        active_tag = "👉 **[ACTIVE]** " if is_active else ""
        recommended_tag = "⭐ _Recommended_ " if info.get("recommended") else ""
        
        lines.append(
            f"{active_tag}**{info['title']}** (`{model_id}`) {recommended_tag}\n"
            f"• {info['description']}\n"
            f"• **Free Tier:** `{info['free_rpm']} RPM` | **Paid Tier:** `{info['paid_rpm']} RPM`\n"
        )
        
    lines.append("━━━━━━━━━━━━━━━━━━━")
    lines.append("👉 **Switch model:** `/model <model_id>` (e.g. `/model 2.5-flash` or `/model pro`)")
    return "\n".join(lines)
