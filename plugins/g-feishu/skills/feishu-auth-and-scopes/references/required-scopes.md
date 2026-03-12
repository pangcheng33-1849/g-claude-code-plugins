# 最小必要权限清单

这不是飞书开放平台的全量 scope 表，只是这套 Feishu skills 当前范围内**最常用、且已经验证过或高置信度依赖**的最小权限清单。

如果你要做的是：

- 很少用的 API
- 新接的工作流
- 某个 scope 在控制台里找不到
- 需要更细的读写拆分

就不要继续猜，直接查官方 scope 列表：

- [官方 scope 列表](https://open.larkoffice.com/document/server-docs/application-scope/scope-list)

## 使用原则

- 只申请当前工作流真正需要的最小 scope。
- 先读再写，先最小身份再更高权限。
- 本地文档只保留高价值、常用、稳定的 scope 名。
- 低频或容易变化的 scope，回到官方文档和对应 API 文档确认。

## 核心 OAuth 与应用管理

- `offline_access`
  - user token 设备授权 / OAuth 刷新链路
- `application:application:self_manage`
  - 仅当你要排查应用 owner 侧权限、应用自管理或应用配置问题时使用

## 文档与 Wiki

- `docs:document.content:read`
  - 读取 doc/wiki 正文
- `docs:document.media:download`
  - 下载文档内图片或媒体
- `docs:document:export`
  - 导出文档
- `docs:permission.member:create`
  - 给文档新增协作者
- `docs:permission.member:update`
  - 更新协作者权限
- `docs:permission.member:delete`
  - 移除协作者
- `board:whiteboard:node:read`
  - 读取或下载白板内容

说明：

- 白板节点写入、PlantUML/Mermaid 白板种子创建这类能力还涉及 board 写权限；这部分 scope 容易随 API 能力变化，遇到白板写入时请直接回对应白板 API 文档确认。

## IM

- `im:chat`
  - 群聊基础可见性 / 群元信息相关能力
- `im:chat:create`
  - 创建群聊
- `im:chat:create_by_user`
  - 某些建群路径下的替代权限
- `im:chat.members:write_only`
  - 添加群成员
- `im:message:readonly`
  - 读取消息 / 列消息

说明：

- 发消息、编辑消息、撤回消息、topic/thread 写操作、reaction 写操作都属于 `im:message` 相关权限族，但具体 scope 名建议以对应 IM API 文档为准，不在这里维护一份容易漂移的细表。

## 任务

- `task:task:write`
  - 真实 Task v2 创建 / 更新 / 完成 / 删除

说明：

- task 读、列取、成员、提醒这几类能力在不同 API 文档里的读写拆分可能不同；如果 `task:task:write` 之外还有报错，再回 Task v2 文档核对具体 scope。

## 日程

- `calendar:calendar.event:create`
  - 创建日程时最常见的写权限

说明：

- 读取事件、更新事件、删除事件、查询忙闲、添加参会人，这几类 scope 在控制台里的命名可能和 API 能力细分一致，也可能继续拆分；这里不维护全表，遇到报错时直接回 calendar API 文档确认。

## 多维表格

说明：

- bitable / base 的 app、table、field、record、view 是一组权限族，控制台命名和 API 文档可能按资源域继续拆分。
- 由于这组权限最容易在“看起来像”正确名字时猜错，本地不维护一份伪精确列表。
- 如果 bitable 工作流报 scope 错，直接回对应 API 文档核对 app/table/field/record/view 的具体权限名。

## 搜索与定位

说明：

- `search/v1/user`、文档搜索、wiki 搜索、chat 搜索这类接口所需 scope 以对应搜索 API 文档为准。
- 这类搜索接口的 scope 命名在控制台里不一定按 API 路径直观映射，所以不要在本地硬记。

## 什么时候必须回官方文档

- 控制台里搜不到本地文档里的 scope 名
- 同一工作流里需要更细的读写拆分
- 某个 scope 已加但 API 仍然提示 `invalid_scope`
- 你要接入当前 skill 范围之外的新能力
- 你需要确认白板写入、消息写操作、bitable 细颗粒资源权限
