# 发布流程

此流程发布当前源码和技能文件，不上传抓取数据或本地运行环境。

## 发布前

- 保留 LICENSE、NOTICE、UPSTREAM.md 与衍生文件修改说明。
- 在 UPSTREAM.md 记录上游基准提交 `f814dcfe209dd7958f4858f9d878d591ee85fb56`；发布仓库不宣称包含完整上游 Git 历史。
- 复查 `git status --short` 和实际暂存区，避免 `git add .` 不加检查。确认 `.env`、`.venv`（包括符号链接）、reports、缓存和本地凭据没有进入提交。
- 扫描工作区、待发布 Git 历史和 ZIP；若发现真实秘密，先撤销，再决定历史清理。忽略规则不能清除已跟踪文件。
- 确认 SKILL.md metadata、`.meta.json`、CITATION、CHANGELOG 和 Git tag 使用同一项目版本；上游能力版本单独记录。
- 按 README 运行编译、离线 smoke tests、Skills CLI 发现和安装隔离审计。标明跳过的实时测试、已验证平台及当前接口限制。
- 更新 CHANGELOG 的衍生版本记录。不要把上游历史版本当成自己的 Release。

```bash
python3 -m compileall -q scripts tools tests
python3 -m unittest discover -s tests -v
npx --yes skills@latest add . --list
```

## 构建

在仓库根目录运行：

```bash
python3 tools/build_release.py
```

输出 `dist/china-market-data.zip` 与 SHA-256 文件。构建使用允许清单，包含技能、运行脚本、reference、环境初始化工具、依赖声明、元数据、许可证和用户文档；不包含 tests、Git 历史、assets、虚拟环境或运行记录。脚本拒绝被选中文件中的符号链接。

解压到新目录验证相对路径和 `--help`；完整取数需要在目标机器准备依赖和网络。不要把本机 `.venv` 一起打包。

## 创建公开仓库与 Release

目标仓库是 `clawyi-com/china-market-data`；不要直接向上游 origin 推送。来源基准与修改范围以 UPSTREAM.md 为准。

正式仓库启用 Issues、选择私有漏洞报告设置，并核对赞助入口和维护者联系方式。当前项目未声明维护者私人邮箱，也不自动开启这些远端设置。

将本地已验证的提交推送后，再从同一提交打标签、创建 Release，附上 `china-market-data.zip` 和 `china-market-data.zip.sha256`。Release 说明应把 `npx skills@latest add clawyi-com/china-market-data -g` 作为首选安装方式，并列出改动、兼容性变化、Python 依赖与验证结果。GitHub 自动源码 ZIP 与技能 ZIP 用途不同：用户安装优先使用 Skills CLI 或正式技能 ZIP。
