# 在 VPS 上定时拉取处罚信息的设计

## 目标

本项目要跑在 VPS 上，每天自动从证监会的 searchList 接口拉取最新处罚文书，按现有规则去重、入库，并复用现有清洗链补齐正文、金额、地域和人物。

当前状态是本地手工台。`POST /update` 需要人工传机构和页码，全仓没有调度器，Mongo 写入没有去重。本设计把"拉取"变成一个可定时、可重跑、失败可诊断的独立进程。

## 背景与约束

以下事实来自本次对本机环境的实测，证据在 `artifacts/vps-pull/reachability.txt`。

| 检查项 | 结果 |
| --- | --- |
| 路由 DNS 解析 `www.csrc.gov.cn` | 返回 `198.18.5.181`，属于 fake-IP 段，说明路由器在接管 DNS |
| Cloudflare DoH 解析 | 返回真实地址 `117.59.168.24` 到 `117.59.168.28` |
| TCP 80 和 443 到 `117.59.168.28` | 都通 |
| HTTP 直连真实 IP 请求 searchList | 服务器返回空回复 |
| HTTPS 请求 `www.csrc.gov.cn` | TLS 握手中途被断开 |
| 对照 `https://www.baidu.com` | 200 |

出口网络能连到证监会服务器，但应用层拒绝本次连接。浏览器路径也不可用，本机 Chrome 远程调试端口没有开启。

因此本机不能完成"真实拉到数据"这一验证。编码与离线验证已完成，真实拉取需要在能直连证监会的网络上执行。

## 现状链路

拉取入口是 `backend/web_crawler.py` 的 `get_sumeventdf_backend`。它按 `org2id` 拼接 searchList 地址，带 3 次重试和 1 到 5 秒随机间隔，解析出 `名称`、`文号`、`发文日期`、`序列号`、`链接`、`内容`、`机构` 七列。页面请求失败、JSON 解析失败或响应形状不对时，它记录失败 URL；默认只打印到 stderr 并返回已抓到的行，`raise_on_error=True` 时抛 `CsrcFetchError`。

去重入口是 `backend/web_crawler.py` 的 `update_sumeventdf_backend`。它按 `链接` 字段对旧数据做差集，只写新行，文件名是 `csrcdtlall` 加时间戳。随后级联 `update_csrc2analysis_backend`，同样按 `链接` 差集写 `csrc2analysis` 加时间戳分片。

存储是只追加的 CSV 分片。读取由 `backend/data_service.py:22` 的 `get_csvdf` 全量 glob 合并。展示宽表由 `backend/data_service.py:294` 的三表内连接生成。

清洗分两段。无密钥段是日期归一和空值处理。LLM 富化段由 `backend/classifier.py`、`backend/extractamount.py`、`backend/locationanalysis.py`、`backend/peopleanalysis.py` 处理。

## 实现

新增 `backend/scheduled_pull.py`，一次调用跑一轮然后退出。

### 数据形状

状态模型只有四个字段。

```python
@dataclass
class CrawlState:
    org: str
    channel_id: str
    channel_name: str
    last_link: str = ""
    updated_at: str = ""
```

`last_link` 是该栏目最近一次成功提交的最新链接，也就是水位。状态存 JSON 文件，默认路径 `data/penalty/csrc2/state/crawl_state.json`，键是 `org/channel_id`。写入先写临时文件再 `os.replace` 改名，进程中途被杀不会留下半个文件。

没有页码游标。第一版设计用过 `last_page`，但在水位语义下它和链接水位会互相打架：重跑时页码前进了但差集为空，状态就和事实不一致。去掉后状态只剩一个真值来源。

### 幂等规则

每次运行从每个栏目的第 1 页开始抓取，按 `--max-pages` 页一组向前推进，直到找到水位链接或达到 `--max-fetch-pages` 页上限。找到水位后，截掉水位及其以下的所有行，只提交水位以上的行，并把水位更新为本次提交的第一条链接。

规则的效果如下。

- 连续运行两次，第二次截掉全部行，提交零行。
- 上次运行中途崩溃，重跑时水位还是旧值，已经写入的行在差集里再次被过滤，提交零重复。CSV 分片这一层由 `update_sumeventdf_backend` 按 `链接` 差集保证幂等。
- 水位链接在 `--max-fetch-pages` 页内找不到，说明积压超过本次抓取上限。脚本只提交已经抓到的、位于水位以上的安全前缀，不推进水位，退出码为 1。下次运行从同一水位重新抓取同一区间，不会丢数据，但也不会自动越过上限；需要调大 `--max-fetch-pages` 或做一次性追赶。
- 抓取过程中任意一页失败，同样只提交安全前缀，不推进水位，退出码为 1。

首跑（水位为空）只抓第 1 到 `--max-pages` 页，提交后把水位设为第一条非空链接，不回填更早的历史。需要历史数据时，首跑先用足够大的 `--max-pages` 覆盖目标历史，再切回日常值。

### 流程

1. 预检。拉指定机构第一个栏目的第 1 页。失败则退出码 2，不写任何文件。
2. 对每个机构的每个栏目，从第 1 页开始按 `--max-pages` 页一组抓取，直到找到水位链接或达到 `--max-fetch-pages` 页上限。首跑只在第一组内取数。
3. 每抓到一组，用 `_append_unique` 按 `链接` 去重后交给 `trim_to_new`。找到水位时保留水位以上的行；找不到则继续下一组。
4. 找到水位后，把剩余行交给 `update_sumeventdf_backend`，沿用现有差集和分片写入，并把水位更新为本次提交的第一条链接。
5. 抓取失败、空页提前结束或达到上限时，只提交累计的安全前缀，水位保持不变，该栏目记为失败，退出码为 1。
6. 每个栏目完成后更新状态文件。
7. 打印每个栏目的新增数与结果。

可选步骤不在第一版里，理由见"后续"一节。附件下载、文本抽取和 LLM 富化各有外部依赖，默认开启会让定时任务被最脆弱的环节拖垮。

### 文件改动

| 文件 | 改动 |
| --- | --- |
| `backend/scheduled_pull.py` | 新增。预检、水位、按组抓到水位、抓取上限、安全前缀提交、状态写入、退出码 |
| `backend/scheduled_pull_test.py` | 新增。二十个离线测试，覆盖首跑、重跑、增量、抓取直到水位、上限与部分抓取不推进水位、`trim_to_new` 契约、空链接处理、预检失败、栏目失败和真实差集写入 |
| `backend/web_crawler_fetch_test.py` | 新增。十一个离线用例，覆盖严格与宽松两种模式：分页失败、JSON 解析失败、形状失败、空 `results`、失败页不复用上一页响应、`get_sumeventdf_backend_selective` 委托 |
| `backend/web_crawler.py` | `get_sumeventdf_backend` 增加 `raise_on_error` 关键字。页面失败时打印一行 stderr；严格模式抛 `CsrcFetchError`，携带机构名和按首次出现顺序去重的失败 URL 元组。缺少 `data.results` 或 `results` 不是列表按页失败处理，空 `results` 仍是合法空页。失败请求不再解析上一页的响应。`get_sumeventdf_backend_selective` 改为委托同一实现。`pencsrc2` 支持 `DBCSRC_DATA_DIR` 环境变量覆盖 |
| `compact` 命令 | `scheduled_pull.py --compact`。合并 `csrcdtlall` 和 `csrc2analysis` 分片，按 `链接` 保留最新行，旧分片移入 `archive/`。单分片或空目录时不写文件，重跑是 no-op |
| `docs/vps-scheduled-pull.md` | 本文件 |

`update_sumeventdf_backend` 不改，`/update` 的宽松抓取语义保持不变。

### 退出码与告警

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部栏目成功 |
| 1 | 部分栏目失败、抓取上限被触发或抓取中途失败；已抓到的安全前缀（如有）已写入，水位未推进 |
| 2 | 预检失败，未写入任何文件 |

cron 的退出码交给外部监控，例如 healthchecks.io 的 URL，或一个 `curl` 回调。仓库内不新增监控组件。

### 定时方式

用宿主 crontab 调独立进程，不把调度器塞进 API。API 用 4 个 uvicorn worker，进程内调度会触发 4 次。

```cron
30 2 * * * cd /srv/dbcsrc/backend && /usr/bin/python3 scheduled_pull.py --org 总部 >> /srv/dbcsrc/logs/pull.log 2>&1
```

`cd` 不能省。`web_crawler.pencsrc2` 的默认值是相对路径 `../data/penalty/csrc2`。

`--max-pages` 默认 3，是每组抓取的页数。`--max-fetch-pages` 默认 100，是单次运行每个栏目最多抓取的页数；实际生效上限取两者较大值，所以上限不会小于首个窗口。追积压时这两个值决定单次运行的耗时。

### 部署步骤

1. 把仓库放到 VPS，装 `backend/requirements.txt` 的依赖。
2. 确认出口网络能访问 `www.csrc.gov.cn`。先跑 `python3 scheduled_pull.py --org 总部 --dry-run`，退出码 0 才继续。
3. 用 `--org` 选定首批机构，跑一次 `--max-pages 1`，确认新分片行数大于 0。
4. 再跑一次同样命令，确认新分片行数为 0。这一步验证幂等。
5. 把第 3 步的命令写进 crontab，先在 1 个机构上跑一周。
6. 稳定后把 `--org` 逐个加上，或改成脚本循环全部机构。

`docker-compose.enhanced.yml` 若继续使用，需要补挂载 `data/` 目录和 `state/` 目录。

## 验证结果

本次改动的离线测试全部通过。命令在 `backend/` 下执行。

```text
python3 -m pytest scheduled_pull_test.py web_crawler_fetch_test.py -q
31 passed
```

覆盖的断言如下。

- 首跑提交全部行并把水位设成第一条非空链接。
- 用同样数据重跑，提交批次数量不增加。
- 新数据出现时只提交水位以上的部分。
- 积压超过首个窗口时按组继续抓取，直到找到水位。
- 达到 `--max-fetch-pages` 上限或抓取中途失败时，只提交安全前缀，水位不前进，退出码 1。
- 首跑抓取失败时不提交、不设水位。
- 水位位于首条时不提交，且只抓一组。
- 已有水位但返回空页时退出码 1，不提交，水位不变。
- 抓取上限不会小于首个窗口（`max_pages=5`、`max_fetch_pages=3` 时首组仍抓 5 页）。
- `trim_to_new` 的三态契约：空水位原样返回、水位在首条返回空帧、水位缺失返回 `None`。
- 空链接行不会被去重，也不会成为水位。
- 真实 `update_sumeventdf_backend` 在临时目录写出分片，去重键是 `链接`。
- 离线抓取测试覆盖严格与宽松两种模式：分页失败、JSON 解析失败、形状失败、空 `results`、失败页不复用上一页响应、`get_sumeventdf_backend_selective` 委托。
- `main` 的 dry-run 在预检失败时返回退出码 2。

未验证的部分是真实网络下的首次拉取，因为本机被阻断。上线时的第 2 到 4 步就是现场验证。

仓库里既有的测试失败与本次改动无关，例如 `consolidated_test_suite.py` 期望 `get_url_backend` 返回字符串，而该函数早已改成返回列表。

## 后续

按依赖从轻到重排列。

1. 分片合并。已实现，见上表 `compact` 命令。建议每月跑一次，或在分片数超过 30 个时跑。
2. Mongo 去重。已实现。`insert_online_data` 改为按 `链接` 的 `bulk_write` upsert，重跑不重复。新增 `ensure_online_index`，优先建唯一索引 `uniq_link`，已有重复数据时降级为非唯一索引 `idx_link` 并记录告警。`POST /api/ensure-mongo-index` 可手动触发。五个离线测试在 `backend/mongo_upsert_test.py`。
3. 附件与文本抽取。走现有 `download_attachment` 和 `extract-text`，需要 Chrome、LibreOffice、poppler 和中文字体。`backend/Dockerfile.enhanced` 的 slim 镜像缺这些依赖。
4. LLM 富化。第一阶段已实现。新增 `backend/llm_client.py`，统一 client 构造，默认超时 60 秒、重试 3 次，可用 `OPENAI_TIMEOUT_SECONDS` 和 `OPENAI_MAX_RETRIES` 覆盖。模型分三档，`OPENAI_MODEL` 用于罚单抽取，`OPENAI_LIGHT_MODEL` 用于分类、地点、人物和金额，默认回落到 `OPENAI_MODEL`，`OPENAI_VISION_MODEL` 用于 OCR。分类和罚单抽取请求加了 `response_format` JSON 约束。五个模块改为共用同一 client。SDK 升级仍待做。
5. OCR 管线。第一阶段已实现。新增 `text_layer_ok` 按汉字数量判断文本层是否可用，替换了原来用 raw string 删字符的错误实现。`pdfurl2ocr` 改为页级并发，默认 4 个 worker，可用 `OCR_MAX_WORKERS` 覆盖，输出保持页序。七个离线测试在 `backend/doc2text_ocr_test.py`。第二阶段仍待评估，用 PaddleOCR-VL 或 MinerU 替换 Vision 内核。
6. 金额链路。已修复。`nlp_input` 现在每块返回 `{key: [金额串]}`，偏移由本地 `find` 计算。句子与金额统一取自原文坐标。`get_number` 改为纯函数，用正则抽取金额串并支持中文数字。`extract_money` 在文书没有"综上/合计/其中"层次词时把整句当作金额句。五个离线测试在 `backend/extractamount_test.py`。

## 风险

- 证监会反爬。VPS 出口 IP 可能被拒。预检就是为此设计的，失败时退出码 2 且不写文件。脚本内置随机间隔，不要调低。
- 积压超过抓取上限。`--max-fetch-pages` 是单次运行最多抓取的页数，默认 100，且实际生效值不小于 `--max-pages`。超过上限时脚本只提交安全前缀，不推进水位，退出码 1；下次运行从同一水位重新抓取同一区间，不丢数据，但不会自动越过上限。持续积压时调大 `--max-fetch-pages` 或做一次性追赶。
- 条目级解析异常。当前实现只把页面级失败视为错误；单个条目缺少字段或结构异常时仍会静默跳过该条，页面其余行照常提交。被跳过的条目如果位于水位之上，水位前移后不会再回头抓取，因此这是残留的丢数据风险。新增栏目或上游改版后应抽样核对条数与页面总数。
- 密钥。`backend/.env` 里有真实密钥，VPS 上改用环境变量或 secret 文件，并轮换已暴露的凭证。

## 待定决策

1. 首批上线机构。建议总部加两三个辖区，稳定一周再扩到全国。
2. 附件下载的启用时机。附件依赖最重，建议放在分片合并和 Mongo 去重之后。
3. 数据是否自动同步到 Mongo。这决定第 2 项后续工作的优先级。
