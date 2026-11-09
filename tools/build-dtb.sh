#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
kernel_tree=${KERNEL_TREE:-"$HOME/linux-rockchip"}
flavor=${1:-6.1-linux}
build_dir="$repo_dir/build"

case "$flavor" in
	5.10-android)
		source_dts="$repo_dir/dts-5.10-android/rk3588-chmayco.dts"
		default_output="$build_dir/rk3588-chmayco-android-5.10.dtb"
		expected_version=5.10
		;;
	6.1-linux)
		source_dts="$repo_dir/dts-6.1-linux/rk3588-chmayco.dts"
		default_output="$build_dir/rk3588-chmayco-linux-6.1.dtb"
		expected_version=6.1
		;;
	7.3-linux)
		source_dts="$repo_dir/dts-7.3-linux/rk3588-chmayco.dts"
		default_output="$build_dir/rk3588-chmayco-linux-7.3.dtb"
		expected_version=7.3
		;;
	*)
		echo "unknown flavor: $flavor (use 5.10-android, 6.1-linux or 7.3-linux)" >&2
		exit 1
		;;
esac

output=${2:-"$default_output"}

if [ ! -f "$kernel_tree/Makefile" ]; then
	echo "kernel tree not found: $kernel_tree" >&2
	echo "set KERNEL_TREE=/path/to/linux-rockchip" >&2
	exit 1
fi
if [ ! -f "$source_dts" ]; then
	echo "device tree not found: $source_dts" >&2
	exit 1
fi

kernel_version=$(awk '
	/^VERSION =/ { version = $3 }
	/^PATCHLEVEL =/ { patchlevel = $3 }
	END { print version "." patchlevel }
' "$kernel_tree/Makefile")
if [ "$kernel_version" != "$expected_version" ]; then
	echo "warning: expected kernel $expected_version, tree reports $kernel_version" >&2
fi

for tool in gcc dtc; do
	command -v "$tool" >/dev/null 2>&1 || {
		echo "missing tool: $tool" >&2
		exit 1
	}
done

mkdir -p "$(dirname -- "$output")"
preprocessed=$(mktemp)
trap 'rm -f "$preprocessed"' EXIT HUP INT TERM

(
	cd "$kernel_tree"
	gcc -E -nostdinc \
		-Iinclude \
		-Iarch/arm64/boot/dts/rockchip \
		-undef -D__DTS__ -x assembler-with-cpp \
		"$source_dts" -o "$preprocessed"
	dtc -I dts -O dtb -o "$output" "$preprocessed"
)

sha256sum "$output"
