"""图表生成 Skill — 根据数据自动选择合适的图表类型"""

import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # 无头模式
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 尝试设置中文字体
for font_name in ["SimHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Arial Unicode MS"]:
    if any(font_name in f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [font_name]
        plt.rcParams["axes.unicode_minus"] = False
        break


class ChartSkill:
    """
    输入 ctx: df, statistics, anomalies, output_dir
    输出: {
        "files": list[str],   # 图表文件路径
        "types": list[str],   # 图表类型
    }
    """

    def execute(self, ctx: dict) -> dict:
        df: pd.DataFrame = ctx["df"]
        stats = ctx["statistics"]
        output_dir = ctx.get("output_dir", "./output")
        os.makedirs(output_dir, exist_ok=True)

        files = []
        types = []

        numeric_cols = stats["numeric_columns"]
        cat_cols = stats["categorical_columns"]

        # 1. 数值分布直方图（最多 4 列）
        plot_cols = numeric_cols[:4]
        if plot_cols:
            fig, axes = plt.subplots(1, len(plot_cols),
                                     figsize=(5 * len(plot_cols), 4))
            if len(plot_cols) == 1:
                axes = [axes]
            for ax, col in zip(axes, plot_cols):
                df[col].dropna().hist(ax=ax, bins=30, edgecolor="black", alpha=0.7)
                ax.set_title(f"{col} 分布")
                ax.set_xlabel(col)
                ax.set_ylabel("频次")
            plt.tight_layout()
            path = os.path.join(output_dir, "distributions.png")
            fig.savefig(path, dpi=120)
            plt.close(fig)
            files.append(path)
            types.append("histogram")

        # 2. 分组柱状图
        group_stats = stats.get("group_stats")
        if group_stats and numeric_cols:
            group_col = group_stats["group_by"]
            value_col = numeric_cols[0]
            grouped = df.groupby(group_col)[value_col].sum().sort_values(ascending=False)
            fig, ax = plt.subplots(figsize=(max(8, len(grouped) * 0.8), 5))
            grouped.plot(kind="bar", ax=ax, color="steelblue", edgecolor="black")
            ax.set_title(f"{value_col} by {group_col}")
            ax.set_ylabel(value_col)
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            path = os.path.join(output_dir, "group_bar.png")
            fig.savefig(path, dpi=120)
            plt.close(fig)
            files.append(path)
            types.append("bar")

        # 3. 相关性热力图（数值列 >= 3）
        if len(numeric_cols) >= 3:
            corr = df[numeric_cols].corr()
            fig, ax = plt.subplots(figsize=(8, 6))
            im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr.columns)))
            ax.set_yticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=45, ha="right")
            ax.set_yticklabels(corr.columns)
            for i in range(len(corr)):
                for j in range(len(corr)):
                    ax.text(j, i, f"{corr.values[i, j]:.2f}",
                            ha="center", va="center", fontsize=8)
            fig.colorbar(im)
            ax.set_title("相关性矩阵")
            plt.tight_layout()
            path = os.path.join(output_dir, "correlation.png")
            fig.savefig(path, dpi=120)
            plt.close(fig)
            files.append(path)
            types.append("heatmap")

        # 4. 异常值标注散点图
        anomalies = ctx.get("anomalies", {})
        anomaly_cols = list(anomalies.get("by_column", {}).keys())[:2]
        if len(anomaly_cols) >= 1 and len(numeric_cols) >= 2:
            x_col = anomaly_cols[0]
            y_col = numeric_cols[1] if numeric_cols[1] != x_col else numeric_cols[0]
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.scatter(df[x_col], df[y_col], alpha=0.5, s=20, label="正常")
            anom_idx = anomalies["by_column"][x_col]["indices"]
            if anom_idx:
                ax.scatter(df.loc[anom_idx, x_col], df.loc[anom_idx, y_col],
                           color="red", s=40, label="异常", zorder=5)
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title(f"异常检测: {x_col}")
            ax.legend()
            plt.tight_layout()
            path = os.path.join(output_dir, "anomaly_scatter.png")
            fig.savefig(path, dpi=120)
            plt.close(fig)
            files.append(path)
            types.append("scatter_anomaly")

        return {"files": files, "types": types}
