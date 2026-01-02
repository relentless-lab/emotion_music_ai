## SongGeneration (full-new) 推理 FastAPI 服务（4090 机器用）

这个目录提供一个**独立部署**的推理服务层，用于把已验证可用的：

`bash generate.sh songgeneration_base_new <input_jsonl> <save_dir> --low_mem --not_use_flash_attn`

封装为 HTTP API，并提供：

- `POST /v1/generate`：创建任务（异步、并发限制 1）
- `GET /v1/jobs/{job_id}`：查询任务状态
- `GET /v1/jobs/{job_id}/audio`：下载音频（wav/flac）

并支持在 API 层显式选择：

- `instrumental=true`：纯音乐（强制 `gt_lyric=""`，并在 style/type_info 里附加 `instrumental,no vocals`）
- `instrumental=false`：有人声（优先使用 `lyrics`，空则回退到 `prompt`）

### 运行方式

在 4090 服务器上（已安装并验证 songgeneration 环境），进入本目录：

```bash
pip install -r requirements.txt
export SONGGEN_WORKDIR=/home/featurize/work/songgeneration
export SONGGEN_JOBS_DIR=/tmp/songgen_jobs
export SONGGEN_TIMEOUT_SECONDS=900
uvicorn main:app --host 0.0.0.0 --port 8000
```

> 需要系统安装 `ffmpeg`（当 `format=wav` 时用于转码）。

### API 示例

创建任务：

```bash
curl -X POST http://127.0.0.1:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"一段忧伤的钢琴旋律","style":"piano, sad","duration_sec":30,"format":"wav","seed":123,"separate":false,"instrumental":true}'
```

查询任务：

```bash
curl http://127.0.0.1:8000/v1/jobs/<job_id>
```

下载音频：

```bash
curl -L -o out.wav http://127.0.0.1:8000/v1/jobs/<job_id>/audio
```


