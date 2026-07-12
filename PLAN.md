# Morse Code Decoder — 桌面版摩斯解码翻译器

## 概述

一个本地运行的桌面工具：采集电脑音频（麦克风），实时解码摩斯电码，通过 DeepSeek API 翻译成中文，附带 PCB 电路板风格的动态解码树可视化。

## 技术架构

```
┌──────────────────────────────────────────────────────┐
│                   Frontend (浏览器)                    │
│  HTML + Tailwind CSS + Vanilla JS + SVG + WebSocket  │
│  本地打开 http://localhost:9000                         │
├──────────────────────────────────────────────────────┤
│                   WebSocket (实时通信)                 │
├──────────────────────────────────────────────────────┤
│               Backend (Python + FastAPI)               │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ 音频采集  │→│ 摩斯解码  │→│ DeepSeek 翻译     │  │
│  │ sounddvc │  │ scipy    │  │ httpx             │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────┘
```

**通信协议**：全部通过 WebSocket 实时推送。后端每解码一个字母/翻译完一句就推给前端，前端不做任何信号处理。

---

## 项目结构

```
morse-decoder/
├── requirements.txt           # Python 依赖
├── start.sh                   # 一键启动后端 + 打开浏览器
├── README.md                  # 使用说明
│
├── server/                    # Python 后端
│   ├── main.py                # FastAPI 入口 + WebSocket 路由
│   ├── audio_capture.py       # 音频采集（sounddevice）
│   ├── decoder.py             # 摩斯解码核心算法
│   └── translator.py          # DeepSeek API 翻译
│
└── web/                       # 前端（纯静态，无框架）
    ├── index.html             # 主页面
    ├── css/
    │   └── style.css          # 样式
    └── js/
        ├── app.js             # 主逻辑 + WebSocket 通信
        └── tree.js            # SVG 解码树绘制 + 动效
```

---

## 模块详细规格

### 1. 音频采集 (`server/audio_capture.py`)

**职责**：从默认麦克风采集音频，缓冲最近 3 秒数据供解码。

**接口**：
- `list_devices()` → 列出可用音频设备（含 loopback 设备）
- `AudioCapture(callback, device_id=None)` → 启动采集流
  - `callback(audio_chunk: np.ndarray)` → 每 50ms 回调一次（约 2205 samples @44100Hz）
  - 内部维护一个 3 秒环形缓冲 `RingBuffer`

**注意**：设备系统音频时推荐安装 BlackHole（macOS）或 VB-CABLE（Windows），在后端配置中选择 loopback 设备。

---

### 2. 摩斯解码 (`server/decoder.py`)

#### 信号处理流水线

```
原始音频 (44100Hz)
  │
  ▼
[带通滤波器]  — 巴特沃斯 4 阶，中心频率 800Hz（可调范围 400-1500Hz）
  │
  ▼
[包络检测]  — 全波整流 + 一阶低通滤波（截止 ~50Hz）
  │
  ▼
[自适应阈值]  — 根据噪声基底动态计算信号阈值
             threshold = noise_floor × 1.5 + signal_peak × 0.3
  │
  ▼
[ON/OFF 状态机]  ——  判定信号有无
  │
  ├─ ON 开始 → 计时 → ON > 阈值 → 嗒 (Dah)
  │                   ON ≤ 阈值 → 滴 (Dit)
  │
  └─ OFF 开始 → 计时 → OFF < 滴时长 → 同一字符内
                       OFF < 3×滴时长 → 字符结束
                       OFF > 7×滴时长 → 单词结束
```

#### 自适应 WPM 算法

- 前 5-10 个有效信号自动校准「参考滴时长」
- 滴 = 参考时长以内
- 嗒 = 参考时长 × 2.5 倍以上（可配置）
- 每 20 个字符重新校准一次，适应发报速度变化
- 空闲时保持上次校准值

#### 摩斯表

标准 ITU 摩斯编码表，以 `dict[str, str]` 形式存储（`{".-": "A", "-...": "B", ...}`）。包含：
- A-Z 字母
- 0-9 数字
- 常用标点（`.` `,` `?` `/` `-` 等）
- 常用缩写不在此处理（原样输出，留给 DeepSeek 翻译）

#### 接口

```python
class MorseDecoder:
    def feed_audio(self, samples: np.ndarray) -> None:
        """输入音频块，内部处理"""
    
    class Events:
        def on_letter(self, letter: str):
            """每解码一个字母触发"""
        def on_word(self):
            """每解码一个单词结束触发"""
        def on_error(self, msg: str):
            """出错时触发"""
    
    # 状态
    @property
    def current_wpm(self) -> float:
    @property
    def signal_level(self) -> float:
        """当前信号强度 0.0-1.0"""
```

---

### 3. 翻译 (`server/translator.py`)

**接口**：
```python
class DeepSeekTranslator:
    async def translate(self, text: str) -> str:
        """翻译一段文本"""
```

**API 配置**：
- 端点：`https://api.deepseek.com/v1/chat/completions`
- 模型：`deepseek-chat`
- 从 `server/.env` 读取 `DEEPSEEK_API_KEY`

**系统提示词**（关键设计）：

```
你是无线电摩斯电码翻译助手。请将摩斯解码后的英文内容翻译成中文。

规则：
1. 保留专业术语和呼号不翻译：CQ, QTH, QRM, QRN, 599, 5NN, DE, K, AR, SK, 以及 BA1AA 等格式的呼号
2. 保留信号报告中的数字不翻译
3. 翻译成自然口语化的中文，不要逐字硬译
4. 如果原文是缩写（如 PSE=please, TNX=thanks, HW=how copy），在括号内补充完整

示例：
输入: CQ CQ CQ DE BA1AA PSE K
输出: 呼叫任意台，呼叫任意台，这里是 BA1AA，请回复

输入: UR RST 599 TU
输出: 你的信号报告 599，谢谢
```

**批处理策略**：
- 累积解码出的单词直至遇到单词结束或 3 秒无新输入 → 提交翻译
- 避免每个字母都去调 API（太贵，也太慢）
- 历史翻译记录保留在对话上下文以实现风格一致

---

### 4. 后端 WebSocket 服务 (`server/main.py`)

FastAPI 应用，单一路由：

#### WebSocket `/ws`

**客户端 → 服务端**：
```json
{"type": "start", "frequency": 800, "threshold": null}
{"type": "stop"}
{"type": "set_wpm", "value": 18}
{"type": "config", "api_key": "sk-xxx"}
```

**服务端 → 客户端**：
```json
{"type": "signal_level", "value": 0.75}
{"type": "decoded_letter", "letter": "C"}
{"type": "decoded_word", "word": "CQ"}
{"type": "decoded_text", "text": "CQ CQ DE BA1AA PSE K"}
{"type": "translation", "id": 1, "source": "CQ CQ DE BA1AA PSE K", "target": "呼叫任意台，这里是 BA1AA，请回复"}
{"type": "wpm", "value": 18}
{"type": "status", "state": "listening"}
{"type": "error", "message": "..."}
```

#### 非 WebSocket 路由

- `GET /api/devices` — 列出可用音频设备
- `GET /` — 返回 `web/index.html` 静态文件

---

### 5. 前端 UI (`web/`)

#### 整体布局

```
┌──────────────────────────────────────────────────────────┐
│  [▶ 开始]  [⏹ 停止]     ● 信号强度条    WPM: 18    ● ● │
├──────────────────────────┬───────────────────────────────┤
│                          │                               │
│   摩 斯 解 码 树          │  解码结果                      │
│   SVG 电路板风格          │                              │
│                          │  C                           │
│   ○ 天线                 │  CQ                          │
│    ↓↓                    │  CQ C                        │
│   ○ T    ○ E            │  CQ CQ D                     │
│   ↓ ↘  ↙ ↓              │  CQ CQ DE B                  │
│  ○ M  ○ N ○ A  ○ I     │  CQ CQ DE BA1                │
│  ...                    │  CQ CQ DE BA1AA              │
│                          │  CQ CQ DE BA1AA PSE          │
│                          │                              │
│  当前路径: ●→○→○→○       │                              │
│  当前字母: C    ▓▓▓▓▓▓   │                              │
│                          │                              │
├──────────────────────────┴───────────────────────────────┤
│  📡 翻译记录                                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ CQ CQ DE BA1AA PSE K                                │ │
│  │ → 呼叫任意台，这里是 BA1AA，请回复                     │ │
│  ├─────────────────────────────────────────────────────┤ │
│  │ UR RST 599 K                                        │ │
│  │ → 你的信号报告599，请回复                              │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

#### 页面风格

- **配色**：清新浅色底，PCB 风格的深绿/铜色点缀
  - 主背景：`#F5F5F0`（暖白）
  - 侧栏/卡片：`#FFFFFF`
  - 电路板装饰线：`#2D5A27`（PCB 绿，20% 透明度）
  - 节点焊盘：`#C99E3C`（铜色）
  - 激活路径：`#E8450C`（橙红，电流通过效果）
  - 文字：`#1A1A1A`
- **字体**：系统字体栈，英文解码用等宽（`JetBrains Mono` / `monospace`）
- **动画**：路径激活用 CSS `stroke-dashoffset` 画线 + 节点呼吸灯效果

#### 左侧：解码树（SVG，`tree.js`）

**树数据**：以对象形式存储完整的摩斯二叉树

```javascript
const morseTree = {
  char: null,
  dit: { char: 'E', dit: { char: 'I', dit: { char: 'S', dit: { char: 'H' }, dah: { char: '5' } }, ... }, ... },
  dah: { char: 'T', ... },
}
```

**绘制方式（`tree.js`）**：
- 纯 SVG 绘制，**径向扇出布局**
- 天线在顶部中央
- 嗒（dah）往左分支，滴（dit）往右分支
- 节点间距逐层递减，形成蝴蝶形
- PCB 视觉效果：节点画成圆形焊盘（外圈铜色 + 中心过孔），连线画成走线（带 45° 转角，像真 PCB）

**动效**：
- 每解码一个滴/嗒，对应的路径高亮（橙色线条像电流流过），节点亮金色
- 到达叶子字母时，字母闪烁 + 波纹扩散动画
- 路径文字标注「当前: T→M→O」

#### 右侧：解码结果

- 等宽字体，终端风格
- 每解码一个字母追加到行尾
- 单词结束自动空格
- 新的句子新起一行
- 不超过 20 行自动滚动

#### 下方：翻译区

- 每一条翻译是一张卡片
- 左上方是源文本（摩斯解码英文），带 📡 图标
- 下方是中文翻译，带 🇨🇳 图标
- 翻译完成后卡片淡入

#### 控制栏

- 开始/停止按钮（图标 + 文字）
- 信号强度指示条（绿色渐变动画）
- WPM 显示
- 设置齿轮图标 → 弹出面板：
  - DeepSeek API Key（保存到 localStorage）
  - 频率设置（400-1500Hz 滑块）
  - 灵敏度（阈值调节滑块）

---

## WebSocket 通信流程

```
客户端                         服务端
  │                              │
  │──── "start" ──────────────→│  ← 开始采集+解码
  │                              │
  │←── "decoded_letter" (C)  ──│  ← 每解码一个字母推一次
  │←── "decoded_letter" (Q)  ──│
  │←── "signal_level" (0.75) ──│  ← 实时信号强度
  │←── "wpm" (18) ────────────│
  │                              │
  │←── "decoded_text" ────────│  ← 句子结束
  │←── "translation" ────────│  ← 翻译结果
  │                              │
  │──── "stop" ───────────────→│  ← 停止解码
```

---

## 实现顺序（建议）

| 步骤 | 内容 | 可验证标志 |
|---|---|---|
| 1 | 搭项目骨架，`requirements.txt`，`server/main.py` FastAPI 空白应用 | `python -m uvicorn server.main:app` 能起来 |
| 2 | 实现 `audio_capture.py`，打印音量到控制台 | 对着麦克风吹气，控制台有波动 |
| 3 | 实现 `decoder.py`，用已知摩斯音频文件测试 | 播放标准 `CQ CQ` 音频能解出字母 |
| 4 | 接入 WebSocket，实时推解码结果 | 浏览器 console.log 能看到字母流 |
| 5 | 实现前端 `index.html` + `tree.js` SVGO树绘制 | 浏览器能看到静态解码树 |
| 6 | 树动效：解码路径高亮 + 节点亮灯 | 解码时树上有走线动画 |
| 7 | 右侧解码结果面板 | 字母逐行显示 |
| 8 | 实现 `translator.py` | 命令行调用能返回翻译 |
| 9 | 翻译区 UI | 翻译结果在页面上显示 |
| 10 | 控制条 + 设置面板 | 能配 API Key、调频率 |
| 11 | 整体打磨：样式、自适应、错误处理 | 完整可用 |

---

## 依赖

```txt
# requirements.txt
fastapi==0.115.*
uvicorn[standard]==0.34.*
sounddevice==0.5.*
numpy==2.4.*
scipy==1.15.*
httpx==0.28.*
python-dotenv==1.1.*
websockets>=14.0
```

---

## 验证方法

1. 安装依赖：`pip install -r requirements.txt`
2. 配置 `server/.env`：写 `DEEPSEEK_API_KEY=sk-xxx`
3. 启动：`python server/main.py`（自动打开浏览器）
4. 测试方法一：用手机播放 YouTube 上的摩斯音频测试视频，贴近麦克风
5. 测试方法二：用在线摩斯生成器（如 morsecode.world）生成音频播放
6. 检查解码树动画是否跟随信号高亮
7. 检查翻译是否准确，术语是否保留
