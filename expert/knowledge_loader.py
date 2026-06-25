"""启动时自动加载预置知识库到向量库（含 Skill 插件知识库）。"""

from __future__ import annotations

import os

from document.loader import load_file, split_documents
from vectorstore.store import async_add_documents
from vectorstore.registry import compute_hash, is_duplicate, register_file
from expert.profile import load_profile


async def load_knowledge_base() -> dict:
    """加载专家配置中指定的知识库文件 + Skill 插件知识库到基础知识库（所有用户共享）。

    已入库的文件（内容未变）会自动跳过，支持增量更新。
    返回加载统计信息。
    """
    profile = load_profile()
    paths = profile.get_knowledge_paths()

    loaded = []
    skipped = []

    # 1. 加载 expert_profile.yaml 中配置的知识库
    for path in paths:
        filename = os.path.basename(path)
        kb_filename = f"kb:{filename}"

        if not os.path.exists(path):
            skipped.append({"file": filename, "source": "expert", "reason": "文件不存在"})
            continue

        with open(path, "rb") as f:
            content_hash = compute_hash(f.read())

        if is_duplicate(kb_filename, content_hash, user_id=None):
            skipped.append({"file": filename, "source": "expert", "reason": "已入库且未变化"})
            continue

        text = load_file(path)
        docs = split_documents(text, kb_filename)
        count = await async_add_documents(docs, user_id=None)
        register_file(kb_filename, content_hash, user_id=None)
        loaded.append({"file": filename, "source": "expert", "chunks": count})

    # 2. 加载 Skill 插件的知识库
    try:
        from skills.loader import get_skill_loader
        loader = get_skill_loader()
        loader.load_all()
        skill_result = await loader.load_knowledge_bases()
        for item in skill_result.get("loaded", []):
            loaded.append({"file": item["file"], "source": f"skill:{item['skill']}", "chunks": item["chunks"]})
        for item in skill_result.get("skipped", []):
            skipped.append({"file": item["file"], "source": f"skill:{item['skill']}", "reason": item["reason"]})
    except Exception as e:
        skipped.append({"file": "skills/*", "source": "skill", "reason": f"加载失败: {e}"})

    return {
        "loaded": loaded,
        "skipped": skipped,
        "total_loaded": len(loaded),
        "total_skipped": len(skipped),
    }
