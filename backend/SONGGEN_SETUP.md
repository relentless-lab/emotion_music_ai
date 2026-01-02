## 用 4090 的 SongGeneration(full-new) 替换 MusicGen（主后端配置）

主后端会在生成时**优先调用 4090 上的 `songgen_infer_service`**（job_id -> 轮询 -> 下载 wav -> 落盘到 `static/audio/` -> 继续走原有“入库/可选 OSS 上传/前端轮询”流程）。

### 1) 4090 机器：启动推理服务

在 4090 机器上进入本仓库的 `songgen_infer_service/`：

```bash
pip install -r requirements.txt
export SONGGEN_WORKDIR=/home/featurize/work/songgeneration
export SONGGEN_JOBS_DIR=/tmp/songgen_jobs
export SONGGEN_TIMEOUT_SECONDS=900
# 可选：确保 generate.sh 命中正确环境
export SONGGEN_ENV_BIN=/home/featurize/work/songgen_env/bin
cd /home/featurize/work/songgeneration
uvicorn songgen_infer_service.main:app --host 0.0.0.0 --port 8000
```

如果你要用 `featurize port export` 暴露公网（推荐）：

```bash
featurize port export 8000
```

它会输出类似：`workspace.featurize.cn:18856`，后续主后端就用这个地址调用。

快速自测：

```bash
curl -X POST http://127.0.0.1:8000/v1/generate -H "Content-Type: application/json" \
  -d '{"prompt":"忧伤钢琴配器","style":"piano, sad","duration_sec":30,"format":"wav","instrumental":true}'
```

### 2) 主后端：指向 4090 推理服务

在主后端环境变量/`.env` 里配置：

```bash
# 这里填 4090 上的 songgen_infer_service 地址：
# - 如果用 featurize 端口转发：填 http://workspace.featurize.cn:18856
# - 如果走内网/公网直连：填 http://<4090 IP>:8000
SONGGEN_REMOTE_URL=http://workspace.featurize.cn:18856
SONGGEN_TOTAL_TIMEOUT_SECONDS=900
SONGGEN_POLL_INTERVAL_SECONDS=2
SONGGEN_REQUEST_TIMEOUT_SECONDS=60
```

然后重启主后端 `uvicorn app.main:app ...`。

> 注意：`SONGGEN_REMOTE_URL`（SongGen）与 `REMOTE_INFERENCE_URL`（旧 MusicGen）不是一个东西。
> 配置了 `SONGGEN_REMOTE_URL` 后，生成会优先走 SongGen。

#### （可选）启用 Qwen2.5-7B-Instruct 做“提示词工程 + 自动写歌词”

如果你希望：
- 用户描述很“泛/口语化”时，后端用 LLM 把需求转换成 SongGeneration 更稳定可控的英文 tags（`descriptions`）
- 用户选择“有人声/歌曲”但不填写歌词时，后端用 LLM **生成原创、结构化歌词**（`gt_lyric`）

在主后端 `.env` 增加：

```bash
SONGGEN_LLM_ENABLED=true
SONGGEN_LLM_TIMEOUT_SECONDS=40
SONGGEN_LLM_MAX_LYRIC_CHARS=1200
```

> 说明：LLM 调用失败会自动回退到规则抽取器（不会让生成直接失败）。

#### （推荐）默认禁用负向 tags（no drums/no vocals）

部分音乐模型会误解 “no drums/no vocals”，反而更容易生成 drums/vocals。
我们默认不把 `no ...` 类 tag 发给模型。

```bash
SONGGEN_ALLOW_NEGATIVE_TAGS=false
```

### 3) 前端使用方式

在“音乐生成”页面：

- 选择 **纯音乐**：只填“描述”，不填歌词
- 选择 **有人声/歌曲**：可额外填“歌词”
  - 如果启用了 `SONGGEN_LLM_ENABLED=true`：不填歌词则由 LLM 自动生成歌词
  - 如果未启用：不填歌词则会回退到“用描述当歌词”（不推荐）

### 4) 4090 侧排查：确认 JSONL 字段符合官方读取口径

在 4090 上找最近一次 job 的输入：

```bash
cat /tmp/songgen_jobs/<job_id>/input.jsonl
```

你应该能看到（至少包含）：
- `idx`
- `gt_lyric`（vocal 场景）
- `descriptions`（英文 tags；SongGeneration 官方字段名）

如果缺少 `descriptions`，说明 4090 推理服务仍在跑旧代码，需要更新并重启。


