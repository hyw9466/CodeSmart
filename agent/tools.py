"""Agent 工具定义：桥接到 Skill 插件系统。

所有工具通过 skills/loader 动态加载，不再硬编码。
如需添加新工具，在 skills/ 目录下创建 skill.yaml 即可。
"""

from __future__ import annotations

from skills.loader import get_skill_loader


def get_all_tools() -> list:
    """返回所有可用的 Agent 工具列表（从 Skill 插件系统动态加载）。"""
    loader = get_skill_loader()
    return loader.get_all_tools()