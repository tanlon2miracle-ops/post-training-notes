"""异常检测 Skill — IQR + Z-score 双重检测"""

import pandas as pd
import numpy as np


class AnomalyDetectionSkill:
    """
    输入 ctx: 包含 df, statistics.numeric_columns
    输出: {
        "total_anomalies": int,
        "by_column": {
            "col_name": {
                "count": int,
                "indices": list[int],
                "lower": float,
                "upper": float,
                "method": "IQR",
            }
        },
        "summary_text": str,  # 给 LLM 消费的文本摘要
    }
    """

    def execute(self, ctx: dict, iqr_factor: float = 1.5,
                zscore_threshold: float = 3.0) -> dict:
        df: pd.DataFrame = ctx["df"]
        numeric_cols = ctx["statistics"]["numeric_columns"]

        by_column = {}
        total = 0

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 10:
                continue

            # IQR 方法
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - iqr_factor * iqr
            upper = q3 + iqr_factor * iqr

            mask_iqr = (df[col] < lower) | (df[col] > upper)

            # Z-score 方法
            mean = series.mean()
            std = series.std()
            if std > 0:
                z = ((df[col] - mean) / std).abs()
                mask_z = z > zscore_threshold
            else:
                mask_z = pd.Series(False, index=df.index)

            # 取并集
            mask = mask_iqr | mask_z
            indices = df.index[mask].tolist()

            if indices:
                by_column[col] = {
                    "count": len(indices),
                    "indices": indices[:50],  # 截断避免太大
                    "lower": float(lower),
                    "upper": float(upper),
                    "method": "IQR+Z-score",
                }
                total += len(indices)

        summary_parts = []
        for col, detail in by_column.items():
            summary_parts.append(
                f"列 [{col}] 发现 {detail['count']} 个异常值 "
                f"(正常范围: {detail['lower']:.2f} ~ {detail['upper']:.2f})"
            )
        summary_text = "\n".join(summary_parts) if summary_parts else "未发现明显异常"

        return {
            "total_anomalies": total,
            "by_column": by_column,
            "summary_text": summary_text,
        }
