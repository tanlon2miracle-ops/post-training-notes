"""生成示例 CSV 数据用于测试"""

import csv
import random
import os

def generate_sample_csv(path: str = "sample_sales.csv"):
    regions = ["华东", "华南", "华北", "西南", "华中"]
    products = ["产品A", "产品B", "产品C", "产品D"]
    months = [f"2025-{m:02d}" for m in range(1, 13)]

    random.seed(42)
    rows = []
    for month in months:
        for region in regions:
            for product in products:
                base = random.randint(5000, 50000)
                qty = random.randint(10, 500)
                cost = round(base * random.uniform(0.4, 0.7), 2)
                row = {
                    "月份": month,
                    "区域": region,
                    "产品": product,
                    "销售额": base,
                    "销量": qty,
                    "成本": cost,
                    "利润": round(base - cost, 2),
                    "客户数": random.randint(5, 200),
                }
                rows.append(row)

    # 注入几个异常值
    rows[3]["销售额"] = 999999   # 异常高
    rows[15]["利润"] = -50000    # 异常亏损
    rows[42]["客户数"] = 9999    # 异常高客户数
    rows[100]["销量"] = 0        # 零销量

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ 示例数据已生成: {path} ({len(rows)} 行)")
    return path


if __name__ == "__main__":
    generate_sample_csv()
