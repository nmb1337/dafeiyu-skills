# Windows 上「不想装编译器」的安装绕法

本机没有 MSVC Build Tools、也没有 Docker/conda。凡是需要现场编译的包，按下面顺序绕，而不是去下几个 G 的编译器。

## 1. 先认报错

- `error: Microsoft Visual C++ 14.0 or greater is required` = 这个包要现场编译 C/C++ 扩展。
- 用 uv 装的时候会明确点出失败的包名（`× Failed to build xxx==ver`），只处理它，别整体推倒。

## 2. 逐包绕法（按优先级）

1. **纯 Python 替代 + 垫片包**（不改上游源码，升级不冲突）：在 venv 的 site-packages 里造一个同名包转发到纯 Python 实现。例：`jieba_fast` →
   - `<venv>/Lib/site-packages/jieba_fast/__init__.py`：`import jieba as _jieba` + `from jieba import *` + 显式导出 `cut/lcut/posseg/setLogLevel`
   - `<venv>/Lib/site-packages/jieba_fast/posseg.py`：`from jieba.posseg import *`
   （`jieba` 与 `jieba_fast` API 兼容，代码里 `import jieba_fast.posseg as psg` 照样能跑。）
2. **用不到的包直接跳过**：如 `pyopenjtalk`（只服务日语发音，做中文 TTS 用不上）。
3. **`--no-binary=<pkg>` / 强制源码编译开关**：本地生成一份过滤后的 requirements（如 `requirements.win.txt`）去掉它，改用现成 wheel。
4. 实在绕不开（核心链路必须那个 C 扩展）才考虑装 Build Tools，并先问用户——这是几个 G 的下载。

## 3. torch / torchaudio：**不要装最新版**

- 新版 `torchaudio` 把音频 IO 外包给 `torchcodec`，而 **torchcodec 官方没有 Windows wheel**（只有 manylinux）→ 报 `TorchCodec is required for load_with_torchcodec`，`torchaudio.load()` 直接不可用。
- 解法：按仓库文档「已测试环境」**降级**（GPT-SoVITS 踩过的组合：`torch==2.7.0` + `torchaudio==2.7.0` + `--index-url https://download.pytorch.org/whl/cu128`）。
- 换版本后要**重启推理服务**（旧进程还持有旧 torch）。验证：`python -c "import torchaudio; x,sr=torchaudio.load('x.wav'); print(x.shape,sr)"`。

## 4. 数据/词典资源放对位置

- nltk 资源（cmudict、taggers…）：把官方给的 `nltk_data.zip` 解压到 **venv 前缀**（`<venv>/nltk_data`），这是官方 `install.ps1` 的做法；放到别处会报 `Resource 'cmudict' not found` 并列出它搜过的路径——照着那个列表放最省事。
- ffmpeg：仓库要求 `ffmpeg.exe`/`ffprobe.exe` 在仓库根时，直接从 `$HERMES_HOME/tools/ffmpeg-*/bin/` 复制（本机已有，不必再下）。
- 模型包（几 G）优先 ModelScope 直连（`curl --noproxy '*'`，国内快），下完解压到 installer 脚本指定的目录，然后**删掉 zip** 回收空间。

## 5. 装完看落地

- 显存：`nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader`（6G 卡跑 half 精度 TTS 约 2.9G，视频模型另算）。
- 磁盘：每装一个大件就看一次 `df -h /c`，并告诉用户还剩多少。
