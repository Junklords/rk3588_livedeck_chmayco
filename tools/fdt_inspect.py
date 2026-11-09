#!/usr/bin/env python3
"""Inspect a flattened device tree without requiring the dtc userspace tools."""

from __future__ import annotations

import argparse
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path


FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9


@dataclass
class Property:
    name: str
    value: bytes


@dataclass
class Node:
    name: str
    path: str
    properties: dict[str, Property] = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)
    parent: "Node | None" = None

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


def align4(value: int) -> int:
    return (value + 3) & ~3


def read_cstring(data: bytes, offset: int) -> tuple[str, int]:
    end = data.find(b"\0", offset)
    if end < 0:
        raise ValueError(f"unterminated string at struct offset {offset:#x}")
    return data[offset:end].decode("utf-8", "replace"), end + 1


def parse_fdt(data: bytes) -> tuple[Node, list[tuple[int, int]], dict[int, str]]:
    if len(data) < 40:
        raise ValueError("file is too short to be a flattened device tree")
    header = struct.unpack_from(">10I", data, 0)
    magic, total_size, off_struct, off_strings, off_rsv, version = header[:6]
    if magic != 0xD00DFEED:
        raise ValueError(f"bad FDT magic {magic:#010x}")
    if total_size > len(data):
        raise ValueError(f"truncated FDT: header says {total_size}, file has {len(data)}")
    if version < 16:
        raise ValueError(f"unsupported FDT version {version}")

    reserve_entries: list[tuple[int, int]] = []
    cursor = off_rsv
    while cursor + 16 <= off_struct:
        address, size = struct.unpack_from(">QQ", data, cursor)
        cursor += 16
        if address == 0 and size == 0:
            break
        reserve_entries.append((address, size))

    root = Node("", "/")
    current = root
    cursor = off_struct
    while cursor < len(data):
        token = struct.unpack_from(">I", data, cursor)[0]
        cursor += 4
        if token == FDT_BEGIN_NODE:
            name, cursor = read_cstring(data, cursor)
            cursor = align4(cursor)
            if current is root and not name:
                continue
            path = current.path.rstrip("/") + "/" + name
            node = Node(name, path, parent=current)
            current.children.append(node)
            current = node
        elif token == FDT_END_NODE:
            if current.parent is None:
                if current is not root:
                    raise ValueError("unbalanced FDT_END_NODE")
            else:
                current = current.parent
        elif token == FDT_PROP:
            length, name_offset = struct.unpack_from(">II", data, cursor)
            cursor += 8
            end = cursor + length
            if end > len(data):
                raise ValueError("property extends beyond FDT")
            name, _ = read_cstring(data, off_strings + name_offset)
            current.properties[name] = Property(name, data[cursor:end])
            cursor = align4(end)
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            break
        else:
            raise ValueError(f"unknown FDT token {token:#x} at {cursor - 4:#x}")

    if current is not root:
        raise ValueError("unbalanced FDT node tree")

    phandles: dict[int, str] = {}
    for node in root.walk():
        for prop_name in ("phandle", "linux,phandle"):
            prop = node.properties.get(prop_name)
            if prop and len(prop.value) == 4:
                phandles[struct.unpack(">I", prop.value)[0]] = node.path
    return root, reserve_entries, phandles


def is_text(value: bytes) -> bool:
    if not value:
        return True
    if value[-1] != 0:
        return False
    chunks = value[:-1].split(b"\0")
    if not any(chunks):
        return False
    return all(
        chunk and all(byte in b"\t\n\r" or 0x20 <= byte <= 0x7E for byte in chunk)
        for chunk in chunks
    )


def format_cells(value: bytes) -> list[str]:
    words = [struct.unpack_from(">I", value, offset)[0] for offset in range(0, len(value) - 3, 4)]
    tail = value[len(words) * 4 :]
    result = [f"{word:#010x}" for word in words]
    if tail:
        result.append("bytes:" + tail.hex())
    return result


def can_reference_phandle(prop_name: str) -> bool:
    return (
        prop_name in {"phandle", "linux,phandle", "interrupt-parent", "next-level-cache"}
        or prop_name.endswith(("-supply", "-gpios", "-gpio", "-handle", "-parent", "-endpoint"))
        or prop_name
        in {
            "clocks",
            "dmas",
            "gpios",
            "iommus",
            "memory-region",
            "msi-parent",
            "phys",
            "power-domains",
            "pwms",
            "resets",
            "sound-dai",
        }
    )


def format_value(prop: Property, phandles: dict[int, str], raw: bool) -> str:
    value = prop.value
    if raw:
        return value.hex()
    if is_text(value):
        strings = value[:-1].decode("utf-8", "replace").split("\0")
        return " | ".join(repr(item) for item in strings)
    if len(value) % 4 == 0:
        cells = format_cells(value)
        resolved: list[str] = []
        for cell in cells:
            if not can_reference_phandle(prop.name):
                resolved.append(cell)
                continue
            try:
                handle = int(cell, 16)
            except ValueError:
                resolved.append(cell)
                continue
            target = phandles.get(handle)
            resolved.append(f"{cell} (&{target})" if target else cell)
        return ", ".join(resolved)
    return "bytes:" + value.hex()


def matches(path: str, patterns: list[re.Pattern[str]]) -> bool:
    return not patterns or any(pattern.search(path) for pattern in patterns)


def print_node(node: Node, phandles: dict[int, str], raw: bool, recursive: bool, depth: int = 0) -> None:
    print(f"{'  ' * depth}{node.name or '/'} {{")
    for name in sorted(node.properties):
        prop = node.properties[name]
        print(f"{'  ' * (depth + 1)}{name} = <{format_value(prop, phandles, raw)}>;")
    if recursive:
        for child in node.children:
            print_node(child, phandles, raw, True, depth + 1)
    elif node.children:
        names = ", ".join(child.name for child in node.children)
        print(f"{'  ' * (depth + 1)}// children: {names}")
    print(f"{'  ' * depth}}}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dtb", type=Path)
    parser.add_argument("-p", "--path", action="append", default=[], help="regex matched against node path")
    parser.add_argument("-r", "--recursive", action="store_true", help="print matching descendants recursively")
    parser.add_argument("--raw", action="store_true", help="print property payloads as hexadecimal")
    parser.add_argument("--phandles", action="store_true", help="print the phandle-to-node mapping")
    parser.add_argument("--reserved", action="store_true", help="print reserved-memory entries")
    parser.add_argument("--count", action="store_true", help="only print node/property counts")
    args = parser.parse_args()

    try:
        root, reserved, phandles = parse_fdt(args.dtb.read_bytes())
    except (OSError, ValueError, struct.error) as error:
        print(f"{args.dtb}: {error}", file=sys.stderr)
        return 1

    if args.count:
        nodes = list(root.walk())
        print(f"nodes={len(nodes)} properties={sum(len(node.properties) for node in nodes)} phandles={len(phandles)}")
        return 0
    if args.reserved:
        for address, size in reserved:
            print(f"{address:#018x} size {size:#x}")
        return 0
    if args.phandles:
        for handle, path in sorted(phandles.items()):
            print(f"{handle:#010x} {path}")
        return 0

    patterns = [re.compile(pattern) for pattern in args.path]
    matched = [node for node in root.walk() if matches(node.path, patterns)]
    for node in matched:
        print_node(node, phandles, args.raw, args.recursive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
