"""统计分析 Skill — 描述性统计 + 分组聚合"""

import pandas as pd
import numpy as np


class StatisticsSkill:
    """
    输入 ctx: 包含 df (DataFrame), columns
    输出: {
        "numeric_columns": list,
        "categorical_columns": list,
        "describe_text": str,
        "describe_dict": dict,
        "group_stats": dict | None,   # 若检测到分类列则自动分组
        "correlations": dict | None,  # 数值列相关矩阵
    }
    """

    def execute(self, ctx: dict) -> dict:
        df: pd.DataFrame = ctx["df"]

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        # 描述性统计
        desc = df.describe(include="all")
        describe_text = desc.to_string()
        describe_dict = desc.to_dict()

        # 相关矩阵（数值列 >= 2 时）
        correlations = None
        if len(numeric_cols) >= 2:
            corr = df[numeric_cols].corr()
            correlations = corr.to_dict()

        # 自动分组聚合：选第一个低基数分类列
        group_stats = None
        for col in cat_cols:
            if 2 <= df[col].nunique() <= 20:
                agg = df.groupby(col)[numeric_cols].agg(["mean", "sum", "count"])
                group_stats = {
                    "group_by": col,
                    "text": agg.to_string(),
                    "dict": {str(k): v for k, v in agg.to_dict().items()},
                }
                break

        return {
            "numeric_columns": numeric_cols,
            "categorical_columns": cat_cols,
            "describe_text": describe_text,
            "describe_dict": describe_dict,
            "correlations": correlations,
            "group_stats": group_stats,
        }
