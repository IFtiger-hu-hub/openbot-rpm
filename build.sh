#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_FILE="${SCRIPT_DIR}/openbot.spec"
BUILD_TOPDIR="${SCRIPT_DIR}/build"
DIST_DIR="${SCRIPT_DIR}/dist"

APPIMAGE_PATH=""
APPIMAGE_GIVEN=false
RELEASE="1"
KEEP_BUILD=false
AUTO_INSTALL=false

usage() {
    cat <<'EOF'
Usage: ./build.sh [options] [path/to/OpenBot-<version>-x86_64.AppImage]

Options:
  -r, --release <num>   RPM release number (default: 1)
  -k, --keep-build      Keep the intermediate build/ directory
  -i, --install         Install the built RPM with zypper after packaging
  -h, --help            Show this help message

If no AppImage path is given, the newest
~/Downloads/OpenBot-*-x86_64.AppImage is used.

The AppImage is extracted with unsquashfs during rpmbuild. FUSE is not
required. Only the official x86_64 AppImage filename is accepted; the RPM
version is taken from that filename.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--release)
            RELEASE="${2:-}"
            shift 2
            ;;
        -k|--keep-build)
            KEEP_BUILD=true
            shift
            ;;
        -i|--install)
            AUTO_INSTALL=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
        *)
            if [[ -n "$APPIMAGE_PATH" ]]; then
                echo "ERROR: Only one AppImage path is accepted." >&2
                usage
                exit 1
            fi
            APPIMAGE_PATH="$1"
            APPIMAGE_GIVEN=true
            shift
            ;;
    esac
done

if [[ ! "$RELEASE" =~ ^[0-9]+$ ]]; then
    echo "ERROR: RPM release must be an integer, got '${RELEASE}'." >&2
    exit 1
fi

for cmd in unsquashfs od rpmbuild grep install chmod sed; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: Required command '$cmd' not found." >&2
        echo "On openSUSE Tumbleweed: sudo zypper install rpm-build squashfs binutils coreutils grep" >&2
        exit 1
    fi
done

if [[ -z "$APPIMAGE_PATH" && -d "${HOME}/Downloads" ]]; then
    APPIMAGE_PATH="$(
        find "${HOME}/Downloads" -maxdepth 1 -type f -name 'OpenBot-*-x86_64.AppImage' -printf '%T@ %p\n' 2>/dev/null \
            | sort -nr \
            | head -n 1 \
            | cut -d' ' -f2- \
            || true
    )"
fi
if [[ -z "$APPIMAGE_PATH" ]]; then
    echo "ERROR: No AppImage path given and none found in ~/Downloads." >&2
    usage
    exit 1
fi
if [[ "$APPIMAGE_GIVEN" == "false" ]]; then
    echo "==> Auto-detected AppImage: ${APPIMAGE_PATH}"
fi

if [[ ! -f "$APPIMAGE_PATH" ]]; then
    echo "ERROR: File not found: ${APPIMAGE_PATH}" >&2
    exit 1
fi

APPIMAGE_ABS="$(readlink -f "$APPIMAGE_PATH")"
APPIMAGE_NAME="$(basename "$APPIMAGE_ABS")"

if [[ ! "$APPIMAGE_NAME" =~ ^OpenBot-([0-9]+\.[0-9]+\.[0-9]+)-x86_64\.AppImage$ ]]; then
    echo "ERROR: Expected OpenBot-<version>-x86_64.AppImage, got '${APPIMAGE_NAME}'." >&2
    echo "aarch64 is not packaged by this repository." >&2
    exit 1
fi
PKG_VERSION="${BASH_REMATCH[1]}"

echo "==> Version: ${PKG_VERSION}-${RELEASE}"
echo "==> Source:  ${APPIMAGE_NAME}"

cleanup() {
    if [[ "$KEEP_BUILD" == "false" ]]; then
        rm -rf "$BUILD_TOPDIR"
    fi
}
trap cleanup EXIT

rm -rf "$BUILD_TOPDIR"
mkdir -p "${BUILD_TOPDIR}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} "$DIST_DIR"
ln -sfn "$APPIMAGE_ABS" "${BUILD_TOPDIR}/SOURCES/${APPIMAGE_NAME}"

echo "==> Running rpmbuild..."
rpmbuild \
    --define "_topdir ${BUILD_TOPDIR}" \
    --define "pkg_version ${PKG_VERSION}" \
    --define "pkg_release ${RELEASE}" \
    --define "appimage_filename ${APPIMAGE_NAME}" \
    -bb "$SPEC_FILE"

BUILT_RPM="${BUILD_TOPDIR}/RPMS/x86_64/openbot-${PKG_VERSION}-${RELEASE}.x86_64.rpm"
if [[ ! -f "$BUILT_RPM" ]]; then
    echo "ERROR: rpmbuild did not produce ${BUILT_RPM}" >&2
    exit 1
fi

OUT_RPM="${DIST_DIR}/$(basename "$BUILT_RPM")"
mv -f "$BUILT_RPM" "$OUT_RPM"
chmod 644 "$OUT_RPM"

echo ""
echo "==> Done! Built RPM:"
echo "    ${OUT_RPM}"
ls -lh "$OUT_RPM"

if [[ "$AUTO_INSTALL" == "true" ]]; then
    echo "==> Installing via zypper..."
    sudo zypper --allow-unsigned-rpm install "$OUT_RPM"
else
    echo ""
    echo "Install with:"
    echo "    sudo zypper --allow-unsigned-rpm install \"${OUT_RPM}\""
fi
