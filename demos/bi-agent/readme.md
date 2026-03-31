# BI Agent Demo

基于 CoPaw Skill 架构的 BI 分析 Agent Demo。

## 约束
- 云端部署，默认不联网
- 模型：Kimi 2.5 / GLM5 / Qwen3（OpenAI 兼容 API）
- 数据量：几 MB 级 CSV
- 扩展方式：Skill 插件化

## 架构

```
用户输入 CSV + 分析需求
        │
        ▼
┌─────────────────┐
│  bi_agent.py    │  主入口：解析意图、编排 pipeline
│  (Orchestrator) │
└────────┬────────┘
         │
    ┌────┼────┬────────┬──────────┐
    ▼    ▼    ▼        ▼          ▼
 解析  计算  作图    异常检测   LLM 总结
 skill skill skill   skill     skill
```

## 运行

```bash
pip install pandas matplotlib seaborn openai
python bi_agent.py --csv sample_sales.csv --query "分析各区域销售趋势，找出异常"
```
