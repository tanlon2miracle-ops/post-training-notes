"""
CoPaw Skill 配置 — 将 BI Agent 注册为 CoPaw 的一个 Skill

使用方式：
1. 将整个 bi-agent 目录放到 CoPaw 的 skills 目录下
2. CoPaw 会自动加载这个 skill
3. 用户在对话中发送 CSV + 分析需求即可触发

也可以作为独立 CLI 使用：
    python bi_agent.py --csv data.csv --query "分析销售趋势"
"""

SKILL_META = {
    "name": "bi-analyst",
    "version": "0.1.0",
    "description": "BI 数据分析 Agent — 支持 CSV 解析、统计、异常检测、可视化、LLM 洞察",
    "triggers": [
        "分析数据",
        "数据分析",
        "BI 分析",
        "看看这个 CSV",
        "帮我分析",
    ],
    "supported_file_types": [".csv", ".xlsx", ".tsv"],
    "required_packages": ["pandas", "matplotlib", "seaborn", "openai"],
    "author": "demo",
}
