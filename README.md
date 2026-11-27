# openbot-rpm

[![Build OpenBot RPM](https://github.com/IFtiger-hu-hub/openbot-rpm/actions/workflows/build-rpm.yml/badge.svg)](https://github.com/IFtiger-hu-hub/openbot-rpm/actions/workflows/build-rpm.yml)
[![Latest Release](https://img.shields.io/github/v/release/IFtiger-hu-hub/openbot-rpm?label=release)](https://github.com/IFtiger-hu-hub/openbot-rpm/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

非官方仓库：把 [OpenBot](https://github.com/nightly-labs/openbot) 官方 Linux `x86_64` AppImage 重新打包为适用于 **openSUSE Tumbleweed** 的 RPM，并用 GitHub Actions 自动跟踪上游稳定版、发布 GitHub Release，以及在 GitHub Pages 上托管可用 `zypper` 添加的 `rpm-md` 软件源。

仓库简介（可填到 GitHub About）：**非官方 openSUSE Tumbleweed RPM：跟踪 OpenBot 官方 Linux AppImage，自动构建并发布 zypper 软件源。**

本仓库与 Synthetify Labs、nightly-labs **没有隶属或背书关系**。OpenBot 客户端版权归 Synthetify Labs，许可为 [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)；商业使用需要向 Synthetify Labs 另行取得授权。上面的 MIT 徽章只覆盖本仓库的打包脚本、spec 和工作流，不覆盖 OpenBot 本体。详见 [NOTICE](NOTICE)。

建议主题：`opensuse`、`opensuse-tumbleweed`、`rpm`、`github-actions`、`openbot`。

## 快速安装

### 方式一：通过 Zypper 添加软件源（推荐，支持自动更新）

GitHub Pages 托管标准 `rpm-md` 软件源（`https://iftiger-hu-hub.github.io/openbot-rpm/`）。流水线打出新版本后会更新源索引。软件源未签名（`gpgcheck=0`），因为打包流程只使用 `GITHUB_TOKEN`，没有单独的签名密钥。

```bash
# 添加源并刷新
sudo zypper ar https://iftiger-hu-hub.github.io/openbot-rpm/openbot.repo
sudo zypper ref

# 安装 OpenBot
sudo zypper install openbot

# 之后随系统更新升级
sudo zypper dup
```

> 启动方式：在应用菜单搜索 “OpenBot”，或终端运行 `openbot`。
> 卸载方式：`sudo zypper remove openbot`（如需一并移除源：`sudo zypper rr openbot-rpm`）。

软件源只保留当前最新的 RPM。历史版本仍可在 [Releases](https://github.com/IFtiger-hu-hub/openbot-rpm/releases) 里下载。

### 方式二：从 Releases 手动下载安装

前往 [Releases](https://github.com/IFtiger-hu-hub/openbot-rpm/releases/latest) 下载最新的 `.x86_64.rpm`，然后执行：

```bash
sudo zypper --allow-unsigned-rpm install openbot-*-x86_64.rpm
```

## 特性

- **自动跟随上游版本**：从 `nightly-labs/openbot` 的稳定 Release 里找带 `OpenBot-<version>-x86_64.AppImage` 的最新版本。spec 不写死某一个版本号。
- **构建时解包，运行时不用 FUSE**：官方 AppImage 运行时要靠 `fusermount3` 挂载。Tumbleweed 上 FUSE 经常不可用，也不适合作为桌面软件的安装方式。打包时用 `unsquashfs` 按 squashfs 偏移把载荷解出来，装到 `/usr/lib/openbot`，`/usr/bin/openbot` 直接 exec 里面的二进制。
- **保留 Electron 沙箱**：AppImage 挂载点通常是 `nosuid`，所以上游 `AppRun` 在用户命名空间不可用时会加上 `--no-sandbox`。解包安装到普通根文件系统后，`chrome-sandbox` 以 `4755` 安装，启动器不传 `--no-sandbox`。
- **规范的 RPM 打包**：
  - 关闭 `AutoReqProv` 和二进制 strip，避免拆坏捆绑的 Electron / AppImage 载荷；
  - 只拥有 `/usr/lib/openbot`、桌面项、图标和 `/usr/bin/openbot`，不占用 `/opt`、`/usr/lib`、`/usr/share` 等系统目录；
  - 运行依赖使用 openSUSE Tumbleweed 的包名（例如 `mozilla-nss`、`libgtk-3-0`、`libsecret-1-0`），不用 Fedora 或 electron-builder 的默认名；
  - 使用 `zstd` 压缩载荷。
- **桌面入口**：`/usr/share/applications/openbot.desktop`，包含 `openbot://` 协议。图标沿用上游唯一的 1600×1600 PNG，装到 `/usr/share/pixmaps/openbot.png`（hicolor 主题不收录这个尺寸）。

## 本地打包

### 依赖

在 openSUSE Tumbleweed 上：

```bash
sudo zypper install rpm-build squashfs binutils coreutils grep
```

### 使用方法

1. 从 [OpenBot Releases](https://github.com/nightly-labs/openbot/releases/latest) 下载官方 `OpenBot-<version>-x86_64.AppImage`。不要下载源码树。
2. 运行：

```bash
# 自动使用 ~/Downloads 里最新的 OpenBot-*-x86_64.AppImage
./build.sh

# 或指定路径
./build.sh /path/to/OpenBot-0.80.0-x86_64.AppImage

# 打包后直接安装
./build.sh --install
```

RPM 输出在 `dist/`。版本号来自文件名 `OpenBot-<version>-x86_64.AppImage`，因此下一次上游发布不需要改 spec。

本仓库的 Actions 只发布 `x86_64`。官方另有 arm64 AppImage，但在 x86_64 的 Tumbleweed 构建路径里再加一套 aarch64 会把流水线变复杂，所以没有做。

## GitHub Actions 自动打包

[build-rpm.yml](.github/workflows/build-rpm.yml) 在 `opensuse/tumbleweed` 容器里用 `rpmbuild` 构建，生成 `.rpm` 和 `SHA256SUMS`，发布到 **GitHub Releases**，并把 `rpm-md` 源部署到 **GitHub Pages**。只使用 `GITHUB_TOKEN`，不需要额外 secret。

合并到 `main` 之后**不会**因为 push 立刻构建。定时任务也只在默认分支上调度。第一次请手动跑：

1. 确认仓库 **Settings → Actions → General** 允许 GitHub Actions（公开仓库通常默认开启）。
2. 打开 **Settings → Pages → Build and deployment**，把 **Source** 设为 **GitHub Actions**。本仓库当前 `has_pages=false`，这一步 Actions 自己点不了，必须人工选一次。
3. 打开 **Actions → Build OpenBot RPM → Run workflow**。`version` 留空（自动检测最新稳定版），`force` 保持关闭。
4. 成功后即可使用上面的 `zypper ar` 命令。

如果 Release 已经发出、只有 Pages 部署失败：先完成第 2 步，再对该次运行使用 **Re-run failed jobs**。不要直接新开一次不带 `force` 的运行，已存在的 Release 会被跳过。需要整包重做时，把 `force` 打开。

之后流水线会在这些情况下运行：

1. **每日定时检查**：每天 UTC 02:00（北京时间 10:00）查看上游最新稳定版。对应的 `v<版本>` Release 还不存在，且不是比已发布版本更旧的版本时，才下载官方 AppImage、校验 `SHA256SUMS-linux.txt`、构建并发布。GitHub 可能把 schedule 推迟几分钟到几十分钟。
2. **手动触发（Run workflow）**：
   - 不填参数：检测最新稳定版并打包；
   - `version`：指定版本，例如 `0.80.0`；
   - `appimage_url`：必须是 `nightly-labs/openbot` 上对应版本的官方 `x86_64` AppImage 地址；
   - `release`：RPM release 号，默认 `1`；
   - `force`：Release 已存在时也重新构建并覆盖。
3. **打 Tag 触发**：推送 `v<版本号>`（例如 `git tag v0.80.0 && git push origin v0.80.0`）会构建这个版本。标签必须是 `v<major>.<minor>.<patch>`。

跳过预发布标签（例如 Android 的 `android-v*`）。已有更新版本时，不会自动降级。

## 已知限制

- 软件源和 RPM 都没有 GPG 签名。
- x86_64 载荷里的远程桌面组件链接 `libminiupnpc.so.17`。当前 Tumbleweed 提供的是 `libminiupnpc.so.21`，这个可选组件可能起不来。主程序不依赖它，包里仍保留上游文件，没有改 AppImage 内容。
- 上游包是 AppImage，内置更新器仍可能提示下载新的 AppImage。系统里的升级请用 `zypper dup`。启动器会清掉 `APPIMAGE`，避免它把这次安装误当成 AppImage 去替换。
- 沙箱依赖 `chrome-sandbox` 的 setuid，或内核允许的非特权用户命名空间。根文件系统不要把 `/usr` 挂成 `nosuid`。
- 不发布 aarch64 RPM。

## 许可

打包脚本、`openbot.spec` 和 workflow 使用 [MIT License](LICENSE)。

OpenBot 客户端及其二进制的版权归 Synthetify Labs 所有，许可为 PolyForm Noncommercial 1.0.0。详见 [NOTICE](NOTICE)。
