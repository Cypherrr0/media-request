---
name: media-request
description: 搜索电影/剧集，向自建媒体服务器（Jellyfin）提交下载请求并查询进度。用户说"想看XX""帮我下XX""XX下好了吗"时使用。
---

# 影视请求

## 配置（密钥不要写进本仓库）
- `MEDIA_REQ_BASE_URL`：可选，默认 `https://cy-media.duckdns.org/req`
- `MEDIA_REQ_API_KEY`：每个用户自己的密钥，作为 agent 的 secret / 环境变量配置。所有请求带 `Authorization: Bearer $MEDIA_REQ_API_KEY`。
- 绝对不要把密钥显示给用户、写进对话或日志。

## 什么时候用
- 用户想看某部电影或某部剧，而且说想下载、想加到片库 → 先 **search**。
- 用户问"下好了吗/进度怎样" → 用 **list** 或 **status**。
- 只是闲聊影视、问剧情 → 不要调用。

## 工具：`scripts/media_req.py`
只用这个脚本（Python 3，无依赖）调用服务，不要自己拼 HTTP 请求。脚本从环境变量或仓库根目录的 `.env` 读取配置，结果以 JSON 打印到 stdout。

| 命令 | 用途 |
|---|---|
| `python3 scripts/media_req.py search "<片名>" --type movie\|tv --region anime_jp\|western\|cn\|other` | 搜索，返回 `results[]`：`id` `title` `original_title` `year` `overview` `seasons` `already_exists` |
| `python3 scripts/media_req.py request <id> --region <同上>` | 提交请求，返回状态对象，含 `request_id` `status` `message` |
| `python3 scripts/media_req.py status <request_id>` | 查一次状态 |
| `python3 scripts/media_req.py status <request_id> --wait --interval 300 --timeout 3600` | 轮询直到停止状态；中间进度打印到 stderr |
| `python3 scripts/media_req.py list` | 我的全部请求和今日额度 `quota.daily` / `quota.used_today` |

**终态**（不会再变）：`available` `failed` `already_exists` `quota_exceeded`（以及测试用的 `dry_run_selected`）。
`--wait` 遇到终态或 `not_found` 就停止（`not_found` 由服务器每 6 小时自动重试，不需要一直等）。

**退出码**：0 成功；1 接口返回错误或请求结果为 `failed`/`quota_exceeded`；2 连不上服务；3 未配置；4 `--wait` 超时。出错时 stdout 是 `{"error": ..., "message": ..., "http_status": ...}`，把 `message` 转述给用户即可。

## 流程
1. **判断类型**：电影 `movie`，电视剧/动画番剧 `tv`。
2. **判断地区 `--region`（宽松判断即可，拿不准就选 other）**：
   - `anime_jp`：日本动画、番剧
   - `western`：欧美电影/美剧/英剧等
   - `cn`：国产剧、国产电影、港台
   - `other`：韩剧、其他或不确定
   region 只是优先搜索的来源，服务器找不到会自动搜全部来源，并按画质选最好的。不要为此反复追问用户。
3. **搜索**：`search`。尽量用英文或原名搜索（中文搜不到时换英文名再试一次）。
4. **和用户确认**：把前 1–3 个结果的 标题、年份、简介（一句话）、季数 告诉用户，问"是这部吗？"。**没确认之前不要提交请求**。同名作品很多（例如翻拍）一定要确认年份。
   - `already_exists: true` 表示片库已有，直接告诉用户，不必请求。
5. **提交**：`request <id> --region ...`（id 原样使用 search 结果里的 `id`）。剧集默认下载所有已播出的季。
6. **回复用户**：转述返回的 `message`，记下 `request_id`，告诉对方可以稍后问进度。
7. **查进度**：用户问起时用 `status <request_id>` 或 `list`。如果需要等待结果，用 `status --wait`，间隔不要小于 300 秒。

## 状态怎么跟用户解释
| status | 怎么说 |
|---|---|
| searching | 正在找资源，稍等几分钟。 |
| not_found | 暂时没找到合适的资源（可能还没上线或太冷门），系统每6小时自动重试，最多7天。 |
| downloading | 正在下载，报 `progress`% 和 `eta_min` 分钟；如果有 `note` 一并说明。 |
| uploading | 下载完了，正在传到网盘，一般几分钟到半小时。 |
| importing | 正在入库，马上能在 Jellyfin 看到。 |
| available | 可以看了，给出 `jellyfin_url`。剧集有 `episodes`（已有/已播出）。 |
| already_exists | 片库里已经有了。若 `in_your_library` 为 false，说明在别人的库里，可以请管理员共享。 |
| quota_exceeded | 今天的次数（`daily_quota`）用完了，明天再试。 |
| failed | 按 `reason` 解释，见下。 |

`notice` 字段（例如"某些季没找到"）要转告用户。

### 失败原因
- **没有做种的人**：资源太冷门下载不动，可以换个版本/以后再试，或请管理员处理。
- **下载机离线**：下载机暂时不在线，恢复后会自动继续，不用重新请求。
- **入库失败**：文件下载了但整理入库出错，需要管理员查看。
- **下载失败**：下载出错，可以过段时间重新请求。
- **条目已被管理员删除**：请联系管理员。
- 7天都没找到：资源确实没有，告诉用户。

## 错误
- `error: unauthorized`（401）：密钥错误/未配置 → 告诉用户"请求服务的密钥没配置好，请联系管理员"，不要重试。
- `error: rate_limited`（429）：太频繁，等一分钟。
- `error: network`：服务暂时连不上，稍后再试。
- `error: config`：环境变量没配置。

接口细节见 `API.md`。
