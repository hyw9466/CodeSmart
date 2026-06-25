"""Skill 配置数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Dict


@dataclass
class SkillParameter:
    """工具参数定义。"""
    name: str
    type: str = "string"          # string / int / float / bool
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class SkillTrigger:
    """触发规则：关键词 + 正则模式。"""
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)


@dataclass
class SkillLLMConfig:
    """LLM 调用配置。"""
    temperature: float = 0.0


@dataclass
class SkillConfig:
    """单个 Skill 的完整配置。"""
    name: str                             # 唯一标识，用作 function name
    display_name: str                     # 前端展示名称
    version: str = "1.0.0"
    description: str = ""                 # 工具描述 → function description
    parameters: List[SkillParameter] = field(default_factory=list)
    system_prompt: str = ""               # System Prompt 模板（支持 {param} 占位）
    user_prompt: str = ""                 # User Prompt 模板（支持 {param} 占位）
    trigger: SkillTrigger = field(default_factory=SkillTrigger)
    llm: SkillLLMConfig = field(default_factory=SkillLLMConfig)
    knowledge_base: List[str] = field(default_factory=list)
    enabled: bool = True
    skill_dir: str = ""                   # 运行时注入：skill 目录绝对路径

    def get_knowledge_paths(self) -> List[str]:
        """返回该 Skill 知识库文件的绝对路径。"""
        import os
        kb_dir = os.path.join(self.skill_dir, "knowledge")
        return [os.path.join(kb_dir, f) for f in self.knowledge_base]

    def get_param_schema(self) -> Dict[str, Any]:
        """生成 LangChain Tool 的 args_schema。"""
        from pydantic import create_model, Field
        
        fields = {}
        for p in self.parameters:
            if p.required:
                fields[p.name] = (str, Field(description=p.description))
            else:
                fields[p.name] = (str, Field(default=p.default, description=p.description))
        
        return create_model(f"{self.name}_args", **fields)