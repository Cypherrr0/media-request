# /req API 参考

推荐通过 `scripts/media_req.py` 调用（见 README）；下面是底层 HTTP 接口。

Base: `https://cy-media.duckdns.org/req`· Header: `Authorization: Bearer $MEDIA_REQ_API_KEY` · JSON · 限速 30 次/分钟/人

## GET /search
参数：`query`（必填）、`type`=`movie|tv`（默认 movie）、`region`=`anime_jp|western|cn|other`（默认 other）
```json
{"query":"Silo","type":"tv","region":"western","results":[
 {"id":"tv:tvdb:403245","title":"Silo","original_title":null,"year":2023,"overview":"...","seasons":4,
  "network":"Apple TV","poster":"https://...","already_exists":false}]}
```

## POST /request
Body：`{"id":"movie:tmdb:872585","region":"western","dry_run":false}`（`dry_run` 只对允许测试的密钥有效：选出资源但不下载，状态为 `dry_run_selected`）
id 格式：`movie:tmdb:<n>` 或 `tv:tvdb:<n>`（直接用 search 返回的 id）。
返回一个状态对象（见下），包含 `request_id`。已存在/超额度时直接返回对应状态。
文件只会进入请求人自己的片库。每日次数有上限（已存在和超额度的请求不计数）。

## GET /status/{request_id}
只能看自己的请求。

## GET /list
```json
{"quota":{"daily":5,"used_today":1},"requests":[<状态对象>...]}
```

## 状态对象
```json
{"request_id":"r_xxx","title":"Oppenheimer (2023)","type":"movie",
 "status":"downloading","message":"正在下载 37.0%，预计还需约 8 分钟",
 "created":"2026-10-28T22:29:31+08:00",
 "release":[{"title":"...","quality":"Bluray-2160p","size_gb":5.1,"seeders":526,"indexer":"1337x","routing":"preferred"}],
 "progress":37.0,"eta_min":8,"seeders":1}
```
`status`：searching | not_found | downloading | uploading | importing | available | failed | already_exists | quota_exceeded | dry_run_selected（仅测试模式）
可选字段：`progress` `eta_min` `seeders` `episodes` `jellyfin_url` `reason` `detail` `notice` `note` `next_retry` `in_your_library` `daily_quota` `files`（上传中：已到网盘的文件数/总数） `tracking`（同一资源已有别人的请求在处理时，附上那条请求的进度）`message_detail`。
`not_found` 会自动重试（最多 7 天），`next_retry` 是下次重试时间；搜索结果异常为空或剧集资料尚未加载时 30 分钟后重试。
`message` 永远是可以直接给用户看的中文。

## 示例
```bash
curl -H "Authorization: Bearer $MEDIA_REQ_API_KEY" "https://cy-media.duckdns.org/req/search?query=Oppenheimer&type=movie&region=western"
curl -H "Authorization: Bearer $MEDIA_REQ_API_KEY" -H 'Content-Type: application/json' \
     -d '{"id":"movie:tmdb:872585","region":"western"}' "https://cy-media.duckdns.org/req/request"
curl -H "Authorization: Bearer $MEDIA_REQ_API_KEY" "https://cy-media.duckdns.org/req/status/r_xxx"
```
