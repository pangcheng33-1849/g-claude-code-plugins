---
name: feishu-api-diagnose
description: 当用户提出“诊断飞书 API 问题”“分析 Feishu 请求失败”“排查 token 或 scope 错误”“检查对象 ID 是否正确”，或需要独立的 Feishu/Lark API 故障排查时，应使用此 skill。
---

# 飞书 API 诊断

## 目的

在环境里没有预装飞书诊断工具时，仍然能够定位 Feishu/Lark API 执行失败的原因。

适用场景：

- 请求失败分析
- token 或 scope 失败
- ID 形态混淆
- 接口路径不匹配
- 限流或分页错误
- 对象类型不匹配

## 执行模式

### 模式 A：已有诊断工具或请求上下文

如果当前环境已经有：

- 带日志的 API 封装
- 请求 trace
- curl 历史
- 失败响应体
- 上下文日志

优先直接使用它们。

### 模式 B：没有现成诊断工具

按下面顺序建立诊断路径：

1. 先用自然语言对错误做第一轮归类
2. 检查凭证
3. 检查 token 类型
4. 检查所需 scope
5. 检查 endpoint 路径
6. 检查对象标识符格式
7. 检查请求 payload 结构
8. 检查限流或分页行为

## 核心工作流

### 1. 从失败表象开始

先收集最小但有用的上下文：

- 尝试执行的操作
- endpoint 或对象类型
- 使用的请求身份
- 原始错误文本或错误码

### 2. 对失败进行归类

优先按大类判断：

- 鉴权失败
- scope 失败
- 对象 ID 非法
- payload 结构不匹配
- 资源不存在
- 被限流
- 分页或 cursor 使用错误

### 3. 给出分层诊断结果

回答时按层次展开：

- 失败点是什么
- 最可能的根因是什么
- 下一步该核对什么
- 重试前应该改什么

### 4. 生成最小复现路径

有帮助时，补充：

- 最小 curl 请求
- 最小 Python 片段
- 需要打印或检查的值清单

## 失败处理

如果诊断依赖缺失的 token 或凭证，切换到 `feishu-auth-and-scopes`。

本仓库 Feishu skills 的统一环境变量标准也以 `feishu-auth-and-scopes` 为准，核心命名是：

- `MY_LARK_APP_ID`
- `MY_LARK_APP_SECRET`
- `MY_LARK_EMAIL`

详细说明见 `feishu-auth-and-scopes` 的：

- `references/env-standards.md`
- `references/required-scopes.md`
- `references/cli-scope-matrix.md`

如果后续还要继续调用其他 Feishu workflow skill，应优先把新拿到的 token 交给 `feishu-auth-and-scopes` 维护，并由 Agent 以内部运行时变量或显式参数的方式继续传递，不要求用户手工配置 token 环境变量。

如果真正的问题是目标对象无法定位，切换到 `feishu-search-and-locate`。

## 正式边界

- 这个 skill 现在不再依赖独立诊断脚本。
- 归因、分层判断、重试建议，都由 Agent 基于原始报错文本和请求上下文做自然语言诊断。
- 如果环境里已经存在项目自带 trace、curl 历史、错误响应体或日志，应优先用这些原始证据，而不是额外生成分类结果。

## 附加资源

- `references/diagnosis-order.md`
- `references/common-failures.md`
- `examples/sample-prompts.md`
