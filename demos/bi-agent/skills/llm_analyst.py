"""LLM 分析 Skill — 调用 OpenAI 兼容 API 生成数据洞察"""

from openai import OpenAI


class LLMAnalystSkill:
    """
    输入 ctx: query, head_text, schema, statistics, anomalies
    输出: {
        "insight": str,        # Markdown 格式的分析文本
        "raw_response": str,   # 原始 LLM 回复
    }

    支持 Kimi 2.5 / GLM5 / Qwen3 等 OpenAI 兼容 API。
    云端不联网场景下，将 base_url 指向本地或内网模型服务即可。
    """

    SYSTEM_PROMPT = """你是一位资深数据分析师。根据提供的数据摘要信息，给出专业的分析洞察。

要求：
1. 先给出 2-3 条核心发现（用 ### 标题）
2. 每条发现配合具体数值佐证
3. 如果有异常数据，分析可能的原因
4. 最后给出 1-2 条可执行的建议
5. 语言简洁专业，避免空泛描述
6. 使用 Markdown 格式"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def execute(self, ctx: dict) -> dict:
        user_prompt = self._build_prompt(ctx)

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            content = resp.choices[0].message.content
            return {"insight": content, "raw_response": content}

        except Exception as e:
            fallback = (
                f"⚠️ LLM 调用失败: {e}\n\n"
                f"**统计摘要**:\n```\n{ctx['statistics'].get('describe_text', 'N/A')}\n```\n\n"
                f"**异常检测**: {ctx['anomalies'].get('summary_text', 'N/A')}"
            )
            return {"insight": fallback, "raw_response": str(e)}

    def _build_prompt(self, ctx: dict) -> str:
        parts = [
            f"## 分析需求\n{ctx['query']}",
            f"\n## 数据概览\n- 行数: {ctx['row_count']}, 列数: {ctx['col_count']}",
            f"- 列: {ctx['columns']}",
            f"\n## 数据样本（前 10 行）\n```\n{ctx['head_text']}\n```",
            f"\n## 描述性统计\n```\n{ctx['statistics']['describe_text']}\n```",
        ]

        # 相关矩阵
        corr = ctx["statistics"].get("correlations")
        if corr:
            # 只列出高相关性对
            high_corr = []
            cols = list(corr.keys())
            for i, c1 in enumerate(cols):
                for c2 in cols[i + 1:]:
                    val = corr[c1].get(c2, 0)
                    if abs(val) > 0.5:
                        high_corr.append(f"  {c1} ↔ {c2}: {val:.3f}")
            if high_corr:
                parts.append(f"\n## 高相关性列对\n" + "\n".join(high_corr))

        # 分组统计
        group = ctx["statistics"].get("group_stats")
        if group:
            parts.append(
                f"\n## 分组统计 (按 {group['group_by']})\n"
                f"```\n{group['text']}\n```"
            )

        # 异常
        parts.append(f"\n## 异常检测结果\n{ctx['anomalies']['summary_text']}")

        return "\n".join(parts)
