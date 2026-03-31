"""
BI Agent Demo - Skill-based data analysis agent
适用于 CoPaw / OpenCode 等 agent 框架的 skill 插件化 BI 分析
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Skills registry
from skills.csv_parser import CSVParserSkill
from skills.statistics import StatisticsSkill
from skills.anomaly import AnomalyDetectionSkill
from skills.chart import ChartSkill
from skills.llm_analyst import LLMAnalystSkill


class BIAgent:
    """
    核心编排器。接收 CSV + 自然语言需求，拆解为 skill 调用链。

    设计原则：
    1. Skill 即插即用 —— 新增能力只需加一个 skill 文件
    2. Pipeline 可配置 —— 通过 LLM 或规则决定调用哪些 skill
    3. 中间结果透传 —— 每个 skill 输入/输出都是 dict，方便调试
    """

    def __init__(self, llm_base_url: str = "http://localhost:8000/v1",
                 llm_api_key: str = "EMPTY",
                 llm_model: str = "qwen3"):
        self.skills = {
            "csv_parser": CSVParserSkill(),
            "statistics": StatisticsSkill(),
            "anomaly": AnomalyDetectionSkill(),
            "chart": ChartSkill(),
            "llm_analyst": LLMAnalystSkill(
                base_url=llm_base_url,
                api_key=llm_api_key,
                model=llm_model,
            ),
        }

    def run(self, csv_path: str, query: str, output_dir: str = "./output") -> dict:
        """
        主 pipeline：
        1. 解析 CSV → DataFrame + schema
        2. 统计分析 → 描述性统计 + 分组聚合
        3. 异常检测 → IQR / Z-score
        4. 作图 → 自动选图 + 保存
        5. LLM 总结 → 结合以上结果给出洞察
        """
        os.makedirs(output_dir, exist_ok=True)
        ctx = {"query": query, "output_dir": output_dir}

        # Step 1: Parse
        print("[1/5] 解析 CSV ...")
        parse_result = self.skills["csv_parser"].execute(csv_path)
        ctx.update(parse_result)
        print(f"  → {parse_result['row_count']} 行, {parse_result['col_count']} 列")
        print(f"  → 列: {parse_result['columns']}")

        # Step 2: Statistics
        print("[2/5] 统计分析 ...")
        stats_result = self.skills["statistics"].execute(ctx)
        ctx["statistics"] = stats_result
        print(f"  → 数值列: {stats_result['numeric_columns']}")

        # Step 3: Anomaly detection
        print("[3/5] 异常检测 ...")
        anomaly_result = self.skills["anomaly"].execute(ctx)
        ctx["anomalies"] = anomaly_result
        print(f"  → 发现 {anomaly_result['total_anomalies']} 个异常点")

        # Step 4: Charts
        print("[4/5] 生成图表 ...")
        chart_result = self.skills["chart"].execute(ctx)
        ctx["charts"] = chart_result
        print(f"  → 生成 {len(chart_result['files'])} 张图表")

        # Step 5: LLM analysis
        print("[5/5] LLM 智能分析 ...")
        analysis = self.skills["llm_analyst"].execute(ctx)
        ctx["analysis"] = analysis

        # 格式化输出
        report = self._format_report(ctx)
        report_path = Path(output_dir) / "report.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"\n✅ 分析完成，报告已保存: {report_path}")
        return ctx

    def _format_report(self, ctx: dict) -> str:
        lines = [
            f"# BI 分析报告",
            f"",
            f"**数据**: {ctx.get('csv_path', 'N/A')} ({ctx['row_count']} 行 × {ctx['col_count']} 列)",
            f"**分析需求**: {ctx['query']}",
            f"",
            f"---",
            f"## 1. 数据概览",
            f"",
            f"| 列名 | 类型 | 非空数 | 唯一值数 |",
            f"|------|------|--------|---------|",
        ]
        for col_info in ctx.get("schema", []):
            lines.append(
                f"| {col_info['name']} | {col_info['dtype']} "
                f"| {col_info['non_null']} | {col_info['unique']} |"
            )

        lines.extend([
            f"",
            f"## 2. 描述性统计",
            f"",
            f"```",
            ctx["statistics"].get("describe_text", "N/A"),
            f"```",
            f"",
            f"## 3. 异常检测",
            f"",
            f"共发现 **{ctx['anomalies']['total_anomalies']}** 个异常数据点。",
            f"",
        ])
        for col, detail in ctx["anomalies"].get("by_column", {}).items():
            lines.append(f"- **{col}**: {detail['count']} 个异常 "
                         f"(阈值: [{detail['lower']:.2f}, {detail['upper']:.2f}])")

        lines.extend([
            f"",
            f"## 4. 图表",
            f"",
        ])
        for f in ctx.get("charts", {}).get("files", []):
            lines.append(f"![{f}]({f})")

        lines.extend([
            f"",
            f"## 5. AI 分析与洞察",
            f"",
            ctx.get("analysis", {}).get("insight", "（分析失败）"),
            f"",
            f"---",
            f"*由 BI Agent 自动生成*",
        ])
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="BI Agent - CSV 数据分析")
    parser.add_argument("--csv", required=True, help="CSV 文件路径")
    parser.add_argument("--query", required=True, help="分析需求（自然语言）")
    parser.add_argument("--output", default="./output", help="输出目录")
    parser.add_argument("--llm-url", default="http://localhost:8000/v1",
                        help="LLM API base URL (OpenAI 兼容)")
    parser.add_argument("--llm-key", default="EMPTY", help="LLM API key")
    parser.add_argument("--llm-model", default="qwen3", help="模型名")
    args = parser.parse_args()

    agent = BIAgent(
        llm_base_url=args.llm_url,
        llm_api_key=args.llm_key,
        llm_model=args.llm_model,
    )
    agent.run(args.csv, args.query, args.output)


if __name__ == "__main__":
    main()
