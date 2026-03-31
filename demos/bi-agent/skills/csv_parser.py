"""CSV 解析 Skill — 读取 CSV，输出 DataFrame + schema 信息"""

import pandas as pd


class CSVParserSkill:
    """
    输入: csv 文件路径
    输出: {
        "df": DataFrame,
        "csv_path": str,
        "row_count": int,
        "col_count": int,
        "columns": list[str],
        "schema": list[dict],   # name, dtype, non_null, unique
        "head_text": str,       # 前 5 行文本（喂给 LLM）
    }
    """

    SUPPORTED_ENCODINGS = ["utf-8", "gbk", "gb2312", "latin-1"]

    def execute(self, csv_path: str) -> dict:
        df = self._read_csv(csv_path)

        schema = []
        for col in df.columns:
            schema.append({
                "name": col,
                "dtype": str(df[col].dtype),
                "non_null": int(df[col].notna().sum()),
                "unique": int(df[col].nunique()),
            })

        return {
            "df": df,
            "csv_path": csv_path,
            "row_count": len(df),
            "col_count": len(df.columns),
            "columns": list(df.columns),
            "schema": schema,
            "head_text": df.head(10).to_string(),
        }

    def _read_csv(self, path: str) -> pd.DataFrame:
        for enc in self.SUPPORTED_ENCODINGS:
            try:
                return pd.read_csv(path, encoding=enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError(f"无法解析 CSV 编码，尝试过: {self.SUPPORTED_ENCODINGS}")
