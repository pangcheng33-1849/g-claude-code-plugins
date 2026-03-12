# Reaction Emoji 参考

官方文档：

- [消息表情与 emoji_type 对照](https://open.larkoffice.com/document/server-docs/im-v1/message-reaction/emojis-introduce)

## 默认选择策略

- 如果用户没有明确指定情绪或风格，默认优先选择**活泼、正向、低歧义**的 reaction。
- 推荐优先顺序：
  - `THUMBSUP`
  - `THANKS`
  - `APPLAUSE`
  - `MUSCLE`
  - `FINGERHEART`
  - `DONE`
  - `SMILE`
  - `LOVE`
  - `PARTY`
  - `HEART`

## 推荐用法

### 收到、认可、支持

- `THUMBSUP`
- `OK`
- `DONE`
- `CheckMark`

### 感谢、鼓励、庆祝

- `THANKS`
- `APPLAUSE`
- `MUSCLE`
- `PARTY`
- `Trophy`
- `Fire`
- `GoGoGo`

### 轻松友好

- `SMILE`
- `BLUSH`
- `LAUGH`
- `WINK`
- `FINGERHEART`
- `LOVE`

## 谨慎使用

下列 emoji 更适合用户明确要求时再用，不要默认使用：

- `SCOWL`
- `SOB`
- `CRY`
- `ERROR`
- `HEARTBROKEN`
- `POOP`
- `No`
- `CrossMark`
- `BOMB`

## 常见 emoji_type 清单

以下按用途分组整理，具体以官方文档为准。

### 正向与鼓励

- `THUMBSUP`
- `THANKS`
- `MUSCLE`
- `FINGERHEART`
- `APPLAUSE`
- `FISTBUMP`
- `JIAYI`
- `DONE`
- `SMILE`
- `BLUSH`
- `LAUGH`
- `LOVE`
- `HEART`
- `PARTY`
- `GoGoGo`
- `ThanksFace`
- `SaluteFace`
- `HappyDragon`
- `Trophy`
- `Fire`
- `ROSE`
- `GIFT`
- `FORTUNE`
- `LUCK`

### 轻松与趣味

- `LOL`
- `SMIRK`
- `WINK`
- `PROUD`
- `WITTY`
- `SMART`
- `BeamingFace`
- `Delighted`
- `Partying`
- `ClownFace`

### 思考与提醒

- `OK`
- `CheckMark`
- `Pin`
- `Alarm`
- `Loudspeaker`
- `THINKING`
- `Shrug`

### 负向与风险提示

- `SCOWL`
- `SOB`
- `CRY`
- `ERROR`
- `HEARTBROKEN`
- `POOP`
- `No`
- `CrossMark`
- `BOMB`
- `ColdSweat`
- `FACEPALM`
- `NOSEPICK`
- `HAUGHTY`

### 业务 / 状态类

- `Yes`
- `Hundred`
- `AWESOMEN`
- `REDPACKET`
- `GeneralDoNotDisturb`
- `Status_PrivateMessage`
- `GeneralInMeetingBusy`
- `StatusReading`
- `StatusInFlight`
- `GeneralBusinessTrip`
- `GeneralWorkFromHome`

## 实际建议

- 给正式同步、跨团队沟通、向上汇报场景回复时：
  - 优先 `THUMBSUP`、`THANKS`、`DONE`、`APPLAUSE`
- 给日常协作、小组讨论、轻量确认场景回复时：
  - 可优先 `SMILE`、`BLUSH`、`LAUGH`、`FINGERHEART`
- 对风险、阻塞、告警消息：
  - 按真实语义选择 `ERROR`、`THINKING`、`SCOWL` 等，不要默认用庆祝类 reaction
