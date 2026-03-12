# update-doc 边界

本文件定义 `update-doc` 当前正式支持的 patch 范围和明确不再优化的场景。

## 1. 已支持

- `append`
- 按标题的块级 patch
- 单块 inline patch
- 跨多个顶层块的局部 patch
- `overwrite` 的顶层块级 diff

## 2. 正式边界

如果 selection 无法安全收敛为局部 patch：

- 显式报错
- 不再静默整文重建

## 3. 长文策略

不再继续优化复杂长文的精细 patch。  
对复杂长文更新，正式兜底方案是：

1. 先读取全文
2. 在本地 Markdown 中修改
3. 再执行 `update-doc --mode overwrite`

如果用户坚持复杂局部编辑，要求用户自己拆成更小的标题范围或 selection。

## 4. 原生扩展块边界

以下原生块在局部 patch 场景下不保证细粒度更新：

- `callout`
- `grid / column`
- `whiteboard`
- `plantuml / mermaid` 白板

需要改动时优先走全文 `overwrite`。
