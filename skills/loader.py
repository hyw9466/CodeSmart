"""Skill 加载引擎：发现、解析、注册 Skill。"""

from __future__ import annotations

import os
import yaml
from typing import Dict, List, Optional

from langchain_core.tools import tool as langchain_tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from skills.schema import SkillConfig, SkillParameter, SkillTrigger, SkillLLMConfig

_loader_instance: Optional["SkillLoader"] = None


class SkillLoader:
    """Skill 发现、加载、注册引擎。"""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self._skills: Dict[str, SkillConfig] = {}
        self._tools: List = []

    # ── 发现 ──

    def discover(self) -> List[str]:
        """扫描 skills/ 目录，发现所有包含 skill.yaml 的子目录。"""
        if not os.path.isdir(self.skills_dir):
            return []

        skill_dirs = []
        for entry in os.listdir(self.skills_dir):
            full_path = os.path.join(self.skills_dir, entry)
            if os.path.isdir(full_path) and os.path.isfile(
                os.path.join(full_path, "skill.yaml")
            ):
                skill_dirs.append(full_path)
        return sorted(skill_dirs)

    # ── 加载 ──

    def load_skill(self, skill_dir: str) -> SkillConfig:
        """加载单个 skill.yaml → SkillConfig 对象。"""
        yaml_path = os.path.join(skill_dir, "skill.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 解析参数
        params = []
        for p in data.get("parameters", []):
            params.append(SkillParameter(
                name=p["name"],
                type=p.get("type", "string"),
                description=p.get("description", ""),
                required=p.get("required", True),
                default=p.get("default"),
            ))

        # 解析触发规则
        trigger_data = data.get("trigger", {})
        trigger = SkillTrigger(
            keywords=trigger_data.get("keywords", []),
            patterns=trigger_data.get("patterns", []),
        )

        # 解析 LLM 配置
        llm_data = data.get("llm", {})
        llm = SkillLLMConfig(
            temperature=llm_data.get("temperature", 0.0),
        )

        return SkillConfig(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            parameters=params,
            system_prompt=data.get("system_prompt", ""),
            user_prompt=data.get("user_prompt", ""),
            trigger=trigger,
            llm=llm,
            knowledge_base=data.get("knowledge_base", []),
            enabled=data.get("enabled", True),
            skill_dir=skill_dir,
        )

    def load_all(self) -> Dict[str, SkillConfig]:
        """加载所有 Skill。"""
        self._skills.clear()
        self._tools.clear()

        for skill_dir in self.discover():
            try:
                skill = self.load_skill(skill_dir)
                if skill.enabled:
                    self._skills[skill.name] = skill
                    self._tools.append(self._create_tool(skill))
            except Exception as e:
                name = os.path.basename(skill_dir)
                print(f"[SkillLoader] 加载 Skill '{name}' 失败: {e}")

        return self._skills

    # ── 工具创建 ──

    def _create_tool(self, skill: SkillConfig):
        """从 SkillConfig 动态创建 LangChain Tool。

        优先使用 skill 目录下的 tool.py 自定义实现（create_tool 函数），
        否则使用 YAML 配置的 system_prompt + user_prompt 自动生成 LLM Chain。
        """
        # 1. 尝试加载自定义 tool.py
        custom_tool_path = os.path.join(skill.skill_dir, "tool.py")
        if os.path.isfile(custom_tool_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                f"skill_{skill.name}", custom_tool_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "create_tool"):
                return module.create_tool(skill)

        # 2. 默认：用 YAML 配置的 Prompt 自动生成 LLM Chain
        prompt = ChatPromptTemplate.from_messages([
            ("system", skill.system_prompt),
            ("user", skill.user_prompt),
        ])

        from models.llm import get_llm

        def tool_func(**kwargs):
            llm = get_llm(temperature=skill.llm.temperature)
            chain = prompt | llm | StrOutputParser()
            return chain.invoke(kwargs)

        tool_func.__name__ = skill.name
        tool_func.__doc__ = skill.description
        tool_func.__annotations__ = {p.name: p.type for p in skill.parameters}

        return langchain_tool(tool_func)

    # ── 工具列表 ──

    def get_all_tools(self) -> List:
        """返回所有已加载 Skill 对应的 LangChain Tool 列表。"""
        if not self._tools:
            self.load_all()
        return self._tools

    def get_skill(self, name: str) -> Optional[SkillConfig]:
        """按名称获取 Skill 配置。"""
        return self._skills.get(name)

    def get_all_skills(self) -> Dict[str, SkillConfig]:
        """获取所有已加载的 Skill 配置。"""
        if not self._skills:
            self.load_all()
        return self._skills

    # ── 知识库加载 ──

    async def load_knowledge_bases(self) -> dict:
        """加载所有 Skill 的知识库到 FAISS 向量库。"""
        from document.loader import load_file, split_documents
        from vectorstore.store import async_add_documents
        from vectorstore.registry import compute_hash, is_duplicate, register_file

        loaded = []
        skipped = []

        for skill in self._skills.values():
            for path in skill.get_knowledge_paths():
                filename = os.path.basename(path)
                kb_filename = f"skill:{skill.name}:{filename}"

                if not os.path.exists(path):
                    skipped.append({"file": filename, "skill": skill.name, "reason": "文件不存在"})
                    continue

                with open(path, "rb") as f:
                    content_hash = compute_hash(f.read())

                if is_duplicate(kb_filename, content_hash, user_id=None):
                    skipped.append({"file": filename, "skill": skill.name, "reason": "已入库且未变化"})
                    continue

                text = load_file(path)
                docs = split_documents(text, kb_filename)
                count = await async_add_documents(docs, user_id=None)
                register_file(kb_filename, content_hash, user_id=None)
                loaded.append({"file": filename, "skill": skill.name, "chunks": count})

        return {
            "loaded": loaded,
            "skipped": skipped,
            "total_loaded": len(loaded),
            "total_skipped": len(skipped),
        }

    # ── 工具指令生成 ──

    def _generate_tool_table(self) -> str:
        """根据已加载 Skill 自动生成 Markdown 工具表。"""
        if not self._skills:
            self.load_all()

        lines = ["## 🛠️ 可用工具\n", "| 工具名称 | 使用场景 |", "|---------|---------|"]
        for skill in self._skills.values():
            desc = skill.description.split("\n")[0] if skill.description else skill.display_name
            lines.append(f"| {skill.name} | {desc} |")
        return "\n".join(lines) + "\n"

    def _generate_decision_guide(self) -> str:
        """根据每个 Skill 的 trigger.keywords 自动生成决策指南。"""
        if not self._skills:
            self.load_all()

        lines = ["## 🤔 工具调用决策指南\n"]

        lines.append('**✅ 直接回答（不需要工具）**：')
        lines.append('- 简单问候或闲聊（如\u201c你好\u201d、\u201c今天天气\u201d）')
        lines.append('- 一般性知识问答（如\u201c什么是 Python\u201d、\u201c解释什么是 REST API\u201d）')
        lines.append('- 概念解释（如\u201c什么是 SQL 注入\u201d、\u201c什么是异步编程\u201d）')
        lines.append('- 不需要外部知识的问题')
        lines.append('- 简短的技术问题（如\u201cPython 中如何读取文件\u201d）\n')

        lines.append("**🔧 调用工具**：")
        for skill in self._skills.values():
            if skill.trigger.keywords:
                kw = "、".join(f'"{k}"' for k in skill.trigger.keywords[:4])
                lines.append(f"- **{skill.name}**：用户提及 {kw} 等关键词时")
            else:
                lines.append(f"- **{skill.name}**：{skill.description.split(chr(10))[0]}")

        lines.append("")
        lines.append("**💡 思考过程**：")
        lines.append("1. 先理解用户的核心需求")
        lines.append("2. 判断是否需要外部工具获取信息")
        lines.append("3. 如果需要，选择最合适的工具")
        lines.append("4. 如果不确定，尝试直接回答（保守策略）")

        return "\n".join(lines)

    def generate_tool_instructions(self) -> str:
        """生成完整的工具指令文本（替换旧的 _TOOL_INSTRUCTIONS）。"""
        return "\n" + self._generate_tool_table() + "\n" + self._generate_decision_guide()


def get_skill_loader(skills_dir: str = "skills") -> SkillLoader:
    """获取 SkillLoader 单例。"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = SkillLoader(skills_dir)
    return _loader_instance


def reset_skill_loader():
    """重置 SkillLoader 单例（用于测试或热加载）。"""
    global _loader_instance
    _loader_instance = None