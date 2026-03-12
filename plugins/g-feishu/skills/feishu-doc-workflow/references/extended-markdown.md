# 飞书扩展 Markdown 写法

这些写法属于飞书扩展语法，不是通用 Markdown 标准。  
只在“Agent 直接生成内容并马上写入飞书”时推荐使用；如果用户要求“本地 Markdown 也能正常预览”，应退回普通 Markdown。

## 1. Callout

```md
<callout type="info" title="注意事项" emoji="gift">
这是正文第一行。

这是正文第二段。
</callout>
```

也支持：

```md
:::callout type=info title="注意事项" emoji="gift"
这是正文第一行。

这是正文第二段。
:::
```

当前状态：

- `create-doc` 和 `update-doc --mode overwrite` 支持原生 callout
- 局部 patch 场景遇到原生 callout，会显式切到整文重写

## 2. Grid / Column

```md
<grid>
  <column title="左栏">
  左边内容第一段

  左边内容第二段
  </column>
  <column title="右栏">
  右边内容第一段

  右边内容第二段
  </column>
</grid>
```

当前状态：

- `create-doc` 和 `update-doc --mode overwrite` 支持原生分栏
- `title` 会折叠进列内第一行文本，不会变成独立列标题字段

## 3. Table

标准 Markdown table：

```md
| 列1 | 列2 |
| --- | --- |
| A | B |
| C | D |
```

扩展 `<lark-table>`：

```md
<lark-table header-row="true" header-column="false">
  <row><cell>姓名</cell><cell>角色</cell></row>
  <row><cell>张三</cell><cell>Owner</cell></row>
  <row><cell>李四</cell><cell>Reviewer</cell></row>
</lark-table>
```

当前 `<lark-table>` 只支持：

- `header-row`
- `header-column`
- 普通 `row/cell`

当前不支持：

- 合并单元格
- 自定义列宽
- 更复杂表格属性

## 4. Whiteboard

```md
<whiteboard align="center" width="900" height="520">
这是白板里的初始文本
第二行内容
</whiteboard>
```

也支持：

```md
<whiteboard align="center" width="900" height="520"/>
```

当前状态：

- `create-doc` 和 `update-doc --mode overwrite` 支持原生白板块
- 标签体是纯文本时，会自动写入初始 `text_shape`
- 白板局部 patch 不支持

## 5. PlantUML / Mermaid -> Whiteboard

PlantUML：

````md
```plantuml align="center" width="960" height="560" syntax-type=1
@startuml
Alice -> Bob: hello
Bob --> Alice: ok
@enduml
```
````

Mermaid：

````md
```mermaid align="center" width="960" height="560"
flowchart LR
  A[Start] --> B[Review]
  B --> C[Done]
```
````

当前状态：

- 两者都会创建原生白板块
- 都通过官方白板语法接口写入图形
- 白板局部 patch 不支持，改图统一走全文 `overwrite`

## 6. 图片与附件写法

当前支持的图片来源包括：

- 本地相对路径
- 本地绝对路径
- `@相对路径`
- `@/绝对路径`
- `attachment://绝对路径`
- `file://绝对路径`
- `http(s)`
- `data:`
- HTML `<img src="...">`
- 自定义 `<image .../>`

`<file .../>` 当前只保留为读取侧结构化语法，不支持写成飞书原生附件块。  
如果目标是把现有文件整体放进飞书文档，改用 `import-doc`。
