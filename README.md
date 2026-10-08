# 衡域：黄金—比特币资产配置与见微问答

这是比赛项目的个性化配置网页。“衡域”根据问卷回答生成参考配置，“见微”负责配置解读和连续投资问答。历史参考方案、回测指标和研究结论来自已经人工确认并冻结的Q1—Q4结果。

个性化层使用投资期限、你能接受的回撤、流动性需求、亏损反应和比特币接受度生成连续风险评分，并在三组历史参考方案之间进行分段线性插值。见微只解释计算结果，不能修改权重。

## 本地运行

```powershell
cd C:\Users\impurity\gold_dashboard
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

未设置大模型环境变量时，见微使用离线说明模式，配置解读与基础问答仍可使用，其他页面功能不受影响。

## 接入OpenAI兼容API

在服务器环境中设置：

```text
LLM_API_BASE=https://provider.example/v1
LLM_API_KEY=your-secret
LLM_MODEL=model-name
```

不要把真实密钥写入代码、`.env.example`或提交附件。当前适配器调用`/chat/completions`，要求模型返回JSON；返回结果会再次校验，模型不能修改量化权重。

## 测试

```powershell
python -m unittest discover -s tests -v
```

## 文件说明

- `app.py`：新版网页入口。
- `gold_dashboard.py`：保留的原始旧版网页。
- `data/app/`：冻结后的可携带数据快照。
- `services/`：数据、配置计算、API和安全校验。
- `static/`：山脉数据流背景、黄金与比特币资产标志。
- `prompts/`：见微配置解读与连续问答的系统提示词。
- `tests/`：权重与响应校验测试。
- `design-qa.md`：最终视觉对照、交互验证和质量结论。

## 声明

本项目用于竞赛研究与方法展示，不构成个人投资建议。历史回测不保证未来表现。
