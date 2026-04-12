# IP Diagnosis Reference

本参考只用于排查以下问题：

- 公网 `IPv4` / `IPv6` 出口
- 地区与 ASN 一致性
- VPN / 代理是否完整接管
- 浏览器侧 `Server Response` 与 `WebRTC` 暴露
- `IPv4/IPv6` 是否分裂

不要把任意单一查询站点当作唯一真值。

## Required Output

每次结论都必须尽量给出：

- `IPv4` 出口 IP、国家/地区、ASN/组织
- `IPv6` 出口 IP、国家/地区、ASN/组织
- `DNS` 解析器
- `default route` 和 `utun` 状态
- 是否存在 `IPv4/IPv6` 地区分裂
- 浏览器侧 `WebRTC` 是否泄漏私网或异常公网地址
- 总体判断：`正常 / 有保留风险 / 明显异常`
- 剩余风险：`地区分裂 / ASN 不一致 / 浏览器泄漏 / IPv6 待核实 / 非网络问题`

## Standard Workflow

### 1. Check External Egress

至少使用两类来源交叉验证：

```bash
curl -4sS https://ipinfo.io/json
curl -6sS https://ipinfo.io/json
curl -4sS https://ifconfig.co/json
curl -6sS https://ifconfig.co/json
curl -4sS https://api.ip.sb/geoip
curl -6sS https://api.ip.sb/geoip
dig +short txt ch whoami.cloudflare @1.1.1.1
```

目标：

- 明确 `IPv4` 和 `IPv6` 是否都存在
- 明确两者地区是否一致
- 明确 ASN 是否像住宅、运营商、机房或典型 VPN 段
- 区分独立公网 `IPv6` 与被映射的 `IPv4-mapped IPv6`

### 2. Check Local Network State

```bash
route -n get default
netstat -rn -f inet6 | sed -n '1,80p'
scutil --dns
ifconfig | grep -E -A3 '^(en0|en1|utun[0-9]+):'
networksetup -getinfo Wi-Fi
```


重点看：

- 默认 `IPv4` 路由是否仍挂在物理网卡
- `IPv6` 默认路由是否通过 `utun`
- `DNS` 是否像隧道私网解析器
- 是否存在活跃 `utun`
- Wi-Fi 自身是否带原生 `IPv6`

### 3. Judge Consistency

高优先级判断规则：

- 如果 `IPv4` 与 `IPv6` 地区不同，优先判为地区分裂风险
- 如果两者都在同一地区，地区层面基本一致
- 如果某个 `-6` 来源把结果错误回退成 `IPv4`，继续换源验证
- 如果没有独立公网 `IPv6`，不要直接写成地区分裂；应写“无独立 IPv6 证据 / 待核实”

### 4. Check Browser-Side Exposure

必须补一轮浏览器侧检查，不能只看命令行网络栈。

推荐方式：

- 用 `playwright-cli` 拉起 Chrome
- 访问 [webbrowsertools IP Address](https://webbrowsertools.com/ip-address/)
- 读取：
  - `IP Addresses`
  - `From Server Response`
  - `Remote IP Services`
  - `Via WebRTC`

判读规则：

- 只看到网站服务器返回的公网地址：正常直连现象
- `Via WebRTC` 只看到 `-`：未见额外暴露
- `Via WebRTC` 暴露真实私网 IP：存在浏览器侧私网泄露
- `Via WebRTC` 暴露异常公网地址或异常 `IPv6`：存在浏览器侧额外暴露风险

## Reporting Template

写报告时，明确区分“已证实事实”和“推测风险”。`IP`、`DNS`、路由、`WebRTC` 观测属于事实；`IP reputation`、站点策略、账号限制属于推测风险。

```md
结论：
- 网络状态：正常 / 有保留风险 / 明显异常

证据：
- IPv4：<ip>，<country/region>，<asn/org>
- IPv6：<ip>，<country/region>，<asn/org>
- DNS：<resolver>
- Default route：<interface/gateway>
- utun：<present/absent + note>
- WebRTC：<clean / private leak / extra public exposure / uncertain>

判断：
- 是否存在 IPv4/IPv6 地区分裂：是 / 否 / 待核实
- 是否命令行与浏览器侧一致：是 / 否 / 部分一致
- 已证实事实：<直接观测到的结果>
- 推测剩余风险：<剩余风险列表>

解决方案：
- <条件> → <动作> → <理由>
```

## Prohibitions

- 不要只引用一个 IP 查询站点
- 不要只看 `IPv4`
- 不要跳过 `WebRTC`
- 不要把“网页能打开”直接等同于“网络没有问题”
- 不要在没做本机路由和 DNS 检查前，草率判断成非网络问题
