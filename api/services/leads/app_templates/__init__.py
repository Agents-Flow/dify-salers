"""
Pre-built app templates for social outreach automation.
These templates can be imported into Dify to quickly set up outreach workflows.
"""

import os
from pathlib import Path
from typing import Any

import yaml

TEMPLATES_DIR = Path(__file__).parent


def get_template_path(template_name: str) -> Path:
    """Get the path to a template file."""
    return TEMPLATES_DIR / f"{template_name}.yaml"


def load_template(template_name: str) -> dict[str, Any]:
    """Load a template YAML file as a dictionary."""
    path = get_template_path(template_name)
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {template_name}")
    
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_template_content(template_name: str) -> str:
    """Get the raw YAML content of a template."""
    path = get_template_path(template_name)
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {template_name}")
    
    return path.read_text(encoding="utf-8")


def list_templates() -> list[dict[str, str]]:
    """List all available templates with their metadata."""
    templates = []
    for file in TEMPLATES_DIR.glob("*.yaml"):
        try:
            data = load_template(file.stem)
            app_info = data.get("app", {})
            templates.append({
                "name": file.stem,
                "title": app_info.get("name", file.stem),
                "mode": app_info.get("mode", "unknown"),
                "description": app_info.get("description", ""),
                "icon": app_info.get("icon", "📦"),
            })
        except Exception:
            continue
    return templates


# Template registry
TEMPLATES = {
    "lead_generation_workflow": {
        "title": "KOL粉丝获客工作流",
        "mode": "workflow",
        "description": "自动化抓取KOL粉丝并创建外展任务",
        "use_case": "获客",
    },
    "dm_chatbot_agent": {
        "title": "AI私信助手",
        "mode": "agent-chat",
        "description": "智能私信助手，自动分析意图并生成回复",
        "use_case": "对话",
    },
    "outreach_chatflow": {
        "title": "智能外展对话流",
        "mode": "advanced-chat",
        "description": "基于SOP的智能外展对话流",
        "use_case": "对话",
    },
    "message_generator": {
        "title": "DM消息生成器",
        "mode": "completion",
        "description": "个性化DM消息生成器",
        "use_case": "内容生成",
    },
    "followback_check_workflow": {
        "title": "互关检测自动化",
        "mode": "workflow",
        "description": "自动检测互关状态并触发后续操作",
        "use_case": "自动化",
    },
    "batch_dm_workflow": {
        "title": "批量DM自动化",
        "mode": "workflow",
        "description": "批量发送个性化DM消息",
        "use_case": "批量操作",
    },
}


def get_templates_by_use_case(use_case: str) -> list[dict[str, str]]:
    """Get templates filtered by use case."""
    return [
        {"name": name, **info}
        for name, info in TEMPLATES.items()
        if info.get("use_case") == use_case
    ]


def get_templates_by_mode(mode: str) -> list[dict[str, str]]:
    """Get templates filtered by app mode."""
    return [
        {"name": name, **info}
        for name, info in TEMPLATES.items()
        if info.get("mode") == mode
    ]
