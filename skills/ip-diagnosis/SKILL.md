---
name: ip-diagnosis
description: 在 macOS + Chrome 上排查公网 IPv4/IPv6 出口、国家/地区、ASN/组织、DNS、默认路由、utun 状态，以及浏览器侧 Server Response 与 WebRTC 暴露情况。适用于用户要求检查 IP、地区一致性、VPN/代理接管情况、IPv6 问题或浏览器网络暴露，并输出详细运维报告与复查链接。
argument-hint: [可选：目标问题或补充上下文]
---

# IP Diagnosis

在 `macOS + Chrome` 上做详细网络诊断，并输出固定结构的运维报告。

## 适用场景

当用户要求以下任务时使用本技能：

- 检查当前公网 `IPv4` / `IPv6`
- 判断 `IPv4/IPv6` 是否地区分裂
- 检查 VPN / 代理是否只接管了部分流量
- 检查浏览器侧是否暴露了额外地址
- 比对命令行出口与浏览器页面看到的结果
- 输出一份可复查的详细网络诊断报告

本技能默认针对当前机器执行，不询问是否继续。

## 执行原则

1. 先补依赖，再做诊断
2. 先本地网络栈，再外部出口，再浏览器交叉验证
3. 至少两类外部来源交叉验证，不依赖单一站点
4. 报告里明确区分：
   - 已证实事实
   - 判断
   - 建议
5. `Server Response` 看到公网 IP，本身不等于浏览器泄露
6. 只有 `Via WebRTC` 暴露出额外私网或异常公网地址时，才判浏览器侧泄露风险

如需判读细则，读取 `references/reference.md`。

## 0. 依赖检查与安装

先检查：

```bash
command -v curl
command -v dig
command -v jq
command -v python3
command -v npm
command -v playwright-cli
command -v brew
open -Ra "Google Chrome"
```

默认依赖：

- `curl`
- `dig`
- `jq`
- `python3`
- `npm`
- `playwright-cli`
- `Google Chrome`

安装规则：

- 若 `playwright-cli` 缺失但 `npm` 不存在，且 `brew` 可用：
  ```bash
  brew install node
  ```
- 若 `playwright-cli` 缺失：
  ```bash
  npm install -g playwright-cli
  ```
- 安装后立刻校验：
  ```bash
  playwright-cli open --help
  ```
- 若 `Google Chrome` 不存在，明确写出阻塞项并停止；不要自动降级到其他浏览器
- 若 `playwright-cli` 能运行，但 `chrome` 浏览器通道打不开，再尝试：
  ```bash
  playwright-cli install-browser --browser chrome
  ```
- 若 `jq` 缺失且 `brew` 可用：
  ```bash
  brew install jq
  ```
- 若 `python3` 缺失且 `brew` 可用：
  ```bash
  brew install python
  ```

如果关键依赖无法安装，报告中明确写出阻塞项并停止，不要伪造结论。

## 1. 本地网络栈检查

按顺序执行：

```bash
route -n get default
netstat -rn -f inet6 | sed -n '1,80p'
scutil --dns
ifconfig | grep -E -A3 '^(en0|en1|utun[0-9]+):'
networksetup -getinfo Wi-Fi
```

目标：

- 看默认路由走向
- 看 `IPv6` 默认路由是否经由 `utun`
- 看是否存在活跃 `utun`
- 看本地接口是否带原生 `IPv6`
- 看 `DNS` 是否像隧道私网解析器或本地直连解析器

## 2. 本地命令确认公网出口

至少执行：

```bash
curl -4sS https://api.ipify.org
curl -6sS https://api64.ipify.org
curl -4sS https://ipinfo.io/json
curl -6sS https://ipinfo.io/json
curl -4sS https://ifconfig.co/json
curl -6sS https://ifconfig.co/json
curl -4sS https://api.ip.sb/geoip
curl -6sS https://api.ip.sb/geoip
dig +short txt ch whoami.cloudflare @1.1.1.1
```

要求：

- 分别确认 `IPv4` 和 `IPv6`
- 尽量为两者都拿到：
  - IP
  - 国家 / 地区
  - ASN
  - 组织
- 如果 `-6` 查询失败，不要立刻判“没有 IPv6”
- 如果结果是 `::ffff:x.x.x.x` 这类 `IPv4-mapped IPv6`，不要把它当成独立公网 `IPv6`

## 3. Chrome 浏览器交叉验证

必须使用：

- [webbrowsertools IP Address](https://webbrowsertools.com/ip-address/)

推荐顺序：

```bash
playwright-cli open --browser=chrome https://webbrowsertools.com/ip-address/
playwright-cli eval "document.body.innerText"
playwright-cli snapshot
```

如需要，可再读取：

```bash
playwright-cli console
playwright-cli network
```

报告里尽量详细记录这些动态结果分组：

- `IP Addresses`
- `From Server Response`
- `Remote Data`
- `Remote IP Services`
- `Via WebRTC`

如果页面上能看到具体行，尽量逐项列出，不要简单摘要。

重点字段通常包括：

- `HTTP_CLIENT_IP`
- `HTTP_CONNECTING_IP`
- `HTTP_COUNTRY_CODE`
- `HTTP_X_FORWARDED`
- `HTTP_X_CLUSTER_CLIENT_IP`
- `HTTP_FORWARDED_FOR`
- `HTTP_FORWARDED`
- `ipapi.co`
- `hostip.info`
- `ipify.org [IPv4]`
- `ipify.org [IPv6]`
- `ipecho.net`
- 各类 `STUN/WebRTC` 行

## 4. 报告输出格式

必须按以下结构输出。

### 结论

- 网络状态：`正常 / 有保留风险 / 明显异常`
- 一句话总结最关键问题

### 证据

#### 本地检查

- `IPv4`：`<ip 或 未确认>`
- `IPv6`：`<ip 或 未确认>`
- `DNS`：`<解析器摘要>`
- `Default route`：`<网关 / 接口>`
- `utun`：`<存在 / 不存在 + 简述>`
- 本地接口 `IPv6`：`<摘要>`

#### 外部出口

- `IPv4`
  - IP
  - 国家 / 地区
  - ASN
  - 组织
  - 来源 1
  - 来源 2
- `IPv6`
  - IP
  - 国家 / 地区
  - ASN
  - 组织
  - 来源 1
  - 来源 2

如果某个来源失败，明确写：

- `Failed to fetch`
- `timeout`
- `blocked`
- `无独立公网 IPv6 证据`
- `待核实`

#### 浏览器交叉验证

- 页面： [webbrowsertools IP Address](https://webbrowsertools.com/ip-address/)
- `IP Addresses`
- `From Server Response` 各项
- `Remote IP Services` 各项
- `Via WebRTC` 各项

### 判断

必须显式回答：

- 是否存在 `IPv4/IPv6` 地区分裂：`是 / 否 / 待核实`
- 命令行出口与浏览器侧是否一致：`是 / 否 / 部分一致`
- 是否存在浏览器侧 `WebRTC` 泄露：`是 / 否 / 待核实`
- `Server Response` 中看到的公网地址是否只是直连网站的正常现象：`是 / 否`
- 是否确认存在独立公网 `IPv6`：`是 / 否 / 待核实`

### 解决方案

每条建议都要写：

- 适用条件
- 动作
- 为什么有效

建议顺序按优先级从高到低排列。

### 复查链接

至少包含：

- [webbrowsertools IP Address](https://webbrowsertools.com/ip-address/)
- 本次用到的外部查询源链接或域名

## 5. 判读规则

- `From Server Response` 看见公网 IP：
  - 这是网站直连天然可见，不自动判浏览器泄露
- 只有 `Via WebRTC` 暴露额外私网或异常公网地址：
  - 才判为浏览器侧泄露风险
- `IPv4` 和 `IPv6` 国家/地区不同：
  - 判为地区分裂风险
- `IPv6` 查询失败，但本地接口和路由表显示仍有 `IPv6`：
  - 写成 `IPv6 状态待核实`
- 多个来源在 ASN / 组织 / 地区上冲突：
  - 明确写 `来源不一致，需复查`
- 没有独立公网 `IPv6` 证据：
  - 只能写 `未确认独立公网 IPv6`
  - 不要写成 `IPv6 正常`

## 6. 推荐外部来源

优先用这些来源做交叉验证：

- [ipinfo](https://ipinfo.io/json)
- [ifconfig.co](https://ifconfig.co/json)
- [api.ip.sb](https://api.ip.sb/geoip)
- [Cloudflare whoami TXT](https://1.1.1.1/help)

其中 `webbrowsertools` 只作为浏览器交叉验证页，不作为唯一真值来源。

## 7. 禁止事项

- 不要只引用一个 IP 查询站点
- 不要只看 `IPv4`
- 不要跳过浏览器交叉验证
- 不要把 `Server Response` 直接写成浏览器泄露
- 不要把单个外部站点失败当成最终结论
- 不要在未确认 `IPv6` 状态前草率下结论
