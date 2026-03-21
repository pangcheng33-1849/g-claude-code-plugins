# 沙盒测试

## 运行测试

```bash
cd plugins/feishu-channel-sandbox
bash tests/test-sandbox.sh
```

测试使用临时 HOME 目录，不影响真实配置。需要 `jq` 可用。

## 测试结构

`test-sandbox.sh` 分三部分：

1. **安全机制测试**（default profile 下运行）— 验证三层检查和路径边界
2. **glob 路径和扩展名匹配测试** — 验证 glob 模式精确匹配（`.py`/`.js`/`.sh`/`.ts`）和注入防护
3. **DEFAULT profile 行为测试** — 验证只读命令放行、写入命令阻止、scoped 脚本执行
4. **DEV profile 行为测试** — 验证开发命令放行、安全机制仍生效

通过 `switch_profile default/dev` 切换配置集（从 `skills/sandbox-profile/profiles/` 目录复制配置文件）。

## 添加测试用例

使用 `expect_allow` / `expect_block` + `run_bash_hook` / `run_file_hook`：

```bash
# Bash 命令测试
expect_allow '描述' run_bash_hook 'ls -la'
expect_block '描述' run_bash_hook 'rm /etc/passwd'

# 文件路径测试
expect_allow '描述' run_file_hook '/tmp/file.txt'
expect_block '描述' run_file_hook '/etc/passwd'

# 指定 cwd（默认为 /Users/testuser/project）
expect_allow '描述' run_bash_hook 'cat file.txt' '/custom/cwd'
```

## 注意事项

- 路径提取使用词边界匹配，URL 和 git 引用中的路径不会被误提取
- macOS 上 `realpath -m` 不可用，hooks 会自动回退到 `python3 os.path.realpath`
- 测试中的路径引用 `$TEST_CWD` 和 `$TEST_HOME`，不要硬编码真实路径
