# 🧠 Cognitive Lab — 思维实验室

> 一个追踪认知基模、支持多模型对比、守护认知发育的开放环境。

---

## 这是什么？

Cognitive Lab 是一款**本地优先、完全开源**的认知发育工具。它不替代你的思考，而是帮你：

- 📊 **看见自己如何思考**——追踪你反复使用的思维框架（认知基模）
- 🔄 **识别重复的推理模式**——在你即将用旧框架得出旧结论时提醒你
- 🧪 **在安全环境中试错**——用不同思维模型并行分析同一问题，事后回溯对比
- 🎮 **你自己掌控一切**——干涉强度、介入领域、数据保留策略，全部由你设定

---

## 为什么需要它？

现有的 AI 工具擅长**帮你执行任务**，但不擅长**帮你看清自己的思维结构**。

Cognitive Lab 在此基础上提供了四层能力：
- **认知镜像**——持续追踪你使用的思维框架，建模你的认知结构
- **模式检测**——在旧框架即将闭合时识别重复的推理路径
- **思维实验室**——在安全环境里用多个模型并行分析同一问题
- **承诺装置**——帮现在的自己约束冲动的自己，对抗跨期选择的短期偏差

---

## 快速开始

### 安装

```bash
git clone https://github.com/cosmicdk/cognitive-lab.git
cd cognitive-lab

python -m venv venv
source venv/bin/activate
pip install -e .
```

### 第一个认知基模

```bash
cognitive-lab schema add
# 输入：名称"零和博弈框架"
# 输入：描述"倾向于把所有竞争理解为一赢一输"
```

### 记录一次推理

```bash
cognitive-lab chain record
# 输入主题，逐步骤描述你的推理过程
```

### 多模型对比

```bash
cognitive-lab sim create        # 创建案例
cognitive-lab sim add-run <id>  # 用不同视角分析
cognitive-lab sim compare <id>  # 对比结果
```

### 查看认知变化

```bash
cognitive-lab report            # 生成认知变化摘要
cognitive-lab export ~/data.json # 导出全部数据
```

---

## 架构

```
cognitive-lab/
├── core/                    # 核心引擎
│   ├── models.py            # 数据模型（基模、推理链、模拟案例）
│   ├── schema_tracker.py    # 认知基模追踪器
│   ├── pattern_detector.py  # 推理模式检测器
│   ├── simulation_engine.py # 思维实验室引擎
│   ├── interference.py      # 干涉决策引擎
│   └── translation.py       # 认知母语适配层
├── storage/
│   └── database.py          # SQLite 本地存储
├── control/                 # 用户控制层
│   ├── preferences.py       # 偏好管理
│   └── commitment.py        # 承诺装置
├── cli/                     # 命令行入口
│   ├── main.py              # CLI 主程序
│   └── reporter.py          # 报告生成器
├── tests/                   # 测试
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖
├── setup.py                 # 安装配置
└── README.md                # 本文件
```

---

## 设计原则

1. **本地优先** — 数据存储在你自己的设备上（SQLite）
2. **开源核心** — 所有建模逻辑完全透明可审计
3. **用户完全控制** — 干涉强度从 0 到 1 可调
4. **只对比不评判** — 不使用"盲区""错误"等规训标签
5. **渐进式干涉** — 从"只在用户要求时分析"逐步开放
6. **多认知母语** — 支持概念型、经验型、类比型、视觉型表达

---

## 认知母语示例

同一个概念，用不同方式表达：

| 概念 | 概念型 | 经验型 | 类比型 |
|------|--------|--------|--------|
| 认知基模 | 思维框架 | 你常用的思考方式 | 脑子里的地图 |
| 推理模式 | 推理模式 | 你反复使用的思路 | 走熟的老路 |
| 干涉 | 认知干涉 | 一个提醒 | 路口的路标 |
| 模拟 | 思维模拟 | 在脑子里试一遍 | 沙盘推演 |

---

## 技术栈

- **语言**: Python 3.8+
- **存储**: SQLite (WAL 模式)
- **依赖**: pyyaml (可选，配置解析)
- **零云端依赖**: 完全可离线运行

---

## 路线图

- [x] MVP: CLI + SQLite + 手动基模注册
- [ ] v0.2: LLM 基模自动提取 + 语义模式检测
- [ ] v0.3: 自动干涉建议 + JSON 导入导出
- [ ] v1.0: Web UI + 实时干涉引擎 + 社区共享协议

---

## 贡献

这是一个开源项目，欢迎贡献代码、想法和反馈。

---

## 许可

MIT License — 详见 [LICENSE](LICENSE) 文件。

---

*"试试看。错了也没关系。我们再看一遍。"*