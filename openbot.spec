%global debug_package %{nil}
%global _build_id_links none
%global __os_install_post %{nil}
%global __strip /bin/true
%global _binary_payload w3.zstdio

# Versions are injected by build.sh from the official AppImage filename.
# Do not hardcode an upstream version here; that would freeze the package
# on one OpenBot release.
%{!?pkg_version: %{error: pkg_version is unset; run ./build.sh}}
%{!?pkg_release: %{error: pkg_release is unset; run ./build.sh}}
%{!?appimage_filename: %{error: appimage_filename is unset; run ./build.sh}}

Name:           openbot
Version:        %{pkg_version}
Release:        %{pkg_release}
Summary:        OpenBot desktop workspace (unofficial Tumbleweed package)
License:        PolyForm-Noncommercial-1.0.0
URL:            https://github.com/nightly-labs/openbot
Source0:        %{appimage_filename}
ExclusiveArch:  x86_64
AutoReqProv:    no

# Direct NEEDED / dlopen libraries of the official x86_64 build, using
# openSUSE Tumbleweed package names (verified against Factory primary data).
# libgtk-3-0 already pulls most of the GTK/X11/Wayland stack.
Requires:       glibc
Requires:       libgcc_s1
Requires:       libstdc++6
Requires:       libgtk-3-0
Requires:       libglib-2_0-0
Requires:       libgobject-2_0-0
Requires:       libgio-2_0-0
Requires:       libatk-1_0-0
Requires:       libatk-bridge-2_0-0
Requires:       libatspi0
Requires:       libcairo2
Requires:       libpango-1_0-0
Requires:       libX11-6
Requires:       libXcomposite1
Requires:       libXdamage1
Requires:       libXext6
Requires:       libXfixes3
Requires:       libXrandr2
Requires:       libXi6
Requires:       libxcb1
Requires:       libxkbcommon0
Requires:       libxkbcommon-x11-0
Requires:       libexpat1
Requires:       libdbus-1-3
Requires:       libudev1
Requires:       libasound2
Requires:       libcups2
Requires:       mozilla-nspr
Requires:       mozilla-nss
Requires:       libgbm1
Requires:       libdrm2
Requires:       libglvnd
Requires:       Mesa-libGL1
Requires:       Mesa-libEGL1
Requires:       libxshmfence1
Requires:       libnotify4
Requires:       libsecret-1-0
Requires:       libXss1
Requires:       libXtst6
Requires:       xdg-utils
Requires:       desktop-file-utils
# Optional remote-desktop helper bundled in the x86_64 AppImage.
# libminiupnpc.so.17 is not shipped by current Tumbleweed (soname is .21),
# so that one library is intentionally not required.
Requires:       libcap2
Requires:       libopenssl3
Requires:       libcurl4
Requires:       libevdev2
Requires:       libnuma1
Requires:       libpulse0
Requires:       libva2

%description
Unofficial openSUSE Tumbleweed package of the official OpenBot Linux
AppImage. OpenBot is copyright Synthetify Labs and licensed under the
PolyForm Noncommercial License 1.0.0. This package is not affiliated with
Synthetify Labs or nightly-labs.

The AppImage is extracted at build time. The installed tree does not need
FUSE. /usr/bin/openbot execs the extracted binary, and chrome-sandbox is
shipped setuid so the Electron sandbox can start without an AppImage mount.

%prep
set -e
APPIMAGE="%{SOURCE0}"
OFFSETS="%{_builddir}/hsqs.offsets"
grep -aob 'hsqs' "$APPIMAGE" > "$OFFSETS" || true
if [ ! -s "$OFFSETS" ]; then
    echo "ERROR: squashfs magic not found in %{appimage_filename}" >&2
    exit 1
fi

OFFSET=""
while IFS=: read -r off rest; do
    block=$(od -An -t u4 -j $((off + 12)) -N 4 "$APPIMAGE" | tr -d '[:space:]')
    major=$(od -An -t u2 -j $((off + 28)) -N 2 "$APPIMAGE" | tr -d '[:space:]')
    case "$major:$block" in
        4:4096|4:8192|4:16384|4:32768|4:65536|4:131072|4:262144|4:524288|4:1048576)
            OFFSET=$off
            break
            ;;
    esac
done < "$OFFSETS"
rm -f "$OFFSETS"

if [ -z "$OFFSET" ]; then
    echo "ERROR: no squashfs 4.x superblock in %{appimage_filename}" >&2
    exit 1
fi
echo "Using squashfs offset ${OFFSET}"

rm -rf "%{_builddir}/%{name}-%{version}"
unsquashfs -no-progress -o "$OFFSET" -d "%{_builddir}/%{name}-%{version}" "$APPIMAGE"
test -x "%{_builddir}/%{name}-%{version}/openbot"
test -f "%{_builddir}/%{name}-%{version}/chrome-sandbox"
test -f "%{_builddir}/%{name}-%{version}/openbot.desktop"
test -f "%{_builddir}/%{name}-%{version}/usr/share/icons/hicolor/1600x1600/apps/openbot.png"

%build
# Prebuilt upstream binary. Nothing to compile.

%install
set -e
APP_SRC="%{_builddir}/%{name}-%{version}"
APP_DST="%{buildroot}/usr/lib/openbot"

rm -rf "%{buildroot}"
mkdir -p "$APP_DST"
cp -a "$APP_SRC"/. "$APP_DST"/

# FUSE mounts ignore setuid, which is why the upstream AppRun falls back to
# --no-sandbox when user namespaces are unavailable. On a normal Tumbleweed
# root filesystem chrome-sandbox can be setuid, so the launcher must not
# pass --no-sandbox.
chmod 4755 "$APP_DST/chrome-sandbox"

install -dm755 "%{buildroot}/usr/bin"
cat > "%{buildroot}/usr/bin/openbot" <<'EOF'
#!/bin/sh
# Private extracted AppImage tree. $ORIGIN in the binary finds libffmpeg
# and libvulkan. Do not export LD_LIBRARY_PATH: OpenBot launches other
# CLIs, and the AppImage's bundled usr/lib copies must not leak into them.
unset APPIMAGE
unset APPDIR
exec /usr/lib/openbot/openbot "$@"
EOF
chmod 755 "%{buildroot}/usr/bin/openbot"

install -dm755 "%{buildroot}/usr/share/applications"
# %% is an RPM escape; the shell sees a single %.
sed -e 's|^Exec=.*|Exec=openbot %%U|' \
    -e '/^X-AppImage-/d' \
    -e 's|^Icon=.*|Icon=openbot|' \
    "$APP_SRC/openbot.desktop" \
    > "%{buildroot}/usr/share/applications/openbot.desktop"
chmod 644 "%{buildroot}/usr/share/applications/openbot.desktop"
grep -q '^Exec=openbot %%U$' "%{buildroot}/usr/share/applications/openbot.desktop"
if grep -q -- '--no-sandbox' "%{buildroot}/usr/share/applications/openbot.desktop"; then
    echo "ERROR: desktop entry still passes --no-sandbox" >&2
    exit 1
fi

# Upstream ships a single 1600x1600 icon. hicolor does not list that size,
# so install the same PNG as a pixmap (the Nix package does this too).
install -dm755 "%{buildroot}/usr/share/pixmaps"
install -m644 "$APP_SRC/usr/share/icons/hicolor/1600x1600/apps/openbot.png" \
    "%{buildroot}/usr/share/pixmaps/openbot.png"

%post
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || :
fi

%postun
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || :
fi

%files
/usr/lib/openbot
# Listed again so the setuid bit is recorded. rpmbuild warns
# "File listed twice"; the explicit attributes are the ones packaged.
%attr(4755, root, root) /usr/lib/openbot/chrome-sandbox
/usr/bin/openbot
/usr/share/applications/openbot.desktop
/usr/share/pixmaps/openbot.png

%changelog
* Fri Nov 27 2026 openbot-rpm maintainers <builder@localhost> - %{version}-%{release}
- Unofficial Tumbleweed package of the official OpenBot x86_64 AppImage
