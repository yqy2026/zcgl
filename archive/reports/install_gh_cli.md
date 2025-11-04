# GitHub CLI 安装指南

## Windows 安装方法

### 方法1: 通过包管理器安装 (推荐)

#### 使用 Chocolatey
```bash
# 如果已安装 Chocolatey
choco install gh

# 如果未安装 Chocolatey，先安装 Chocolatey
# 以管理员身份运行 PowerShell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
choco install gh
```

#### 使用 Scoop
```bash
# 如果已安装 Scoop
scoop install gh

# 如果未安装 Scoop，先安装 Scoop
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
scoop install gh
```

#### 使用 Winget (Windows 10/11)
```bash
winget install GitHub.cli
```

### 方法2: 直接下载安装

1. 访问 GitHub CLI 官方发布页面: https://github.com/cli/cli/releases
2. 下载最新的 Windows 安装包 (`.msi` 文件)
3. 双击运行安装程序
4. 按照提示完成安装

### 方法3: 使用 npm (Node.js 环境)

```bash
npm install -g @github/cli
```

## 验证安装

安装完成后，打开新的命令行窗口并运行:

```bash
gh --version
```

## 认证

首次使用时需要进行认证:

```bash
gh auth login
```

这将打开浏览器进行GitHub认证。

## 使用示例

创建 Pull Request:
```bash
gh pr create --title "Your PR Title" --body "Your PR description"
```

查看仓库信息:
```bash
gh repo view
```

查看 Pull Requests:
```bash
gh pr list
```

## 更多信息

- 官方文档: https://cli.github.com/manual/
- GitHub CLI 仓库: https://github.com/cli/cli