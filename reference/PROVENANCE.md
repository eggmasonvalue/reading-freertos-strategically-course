# Reference provenance

The kernel and book under `reference/` are **vendored pinned snapshots** of upstream FreeRTOS
repositories, committed here (with their upstream `.git` history stripped) so this archive is
self-contained and the exact source lines cited by the lessons never drift. Both are MIT-licensed;
their `LICENSE*` files are retained in each directory.

| Directory | Upstream | Pinned commit | Commit date |
|---|---|---|---|
| `FreeRTOS-Kernel/` | https://github.com/FreeRTOS/FreeRTOS-Kernel | `4269c69a16f924c11adeedbb31591f6fad9f41b2` | 2026-07-23 |
| `FreeRTOS-Kernel-Book/` | https://github.com/FreeRTOS/FreeRTOS-Kernel-Book | `ba20b2f820926587d5ee20ce312b3789d63f795c` | 2026-04-03 |

## Re-fetching the exact snapshot
```sh
git clone https://github.com/FreeRTOS/FreeRTOS-Kernel
git -C FreeRTOS-Kernel checkout 4269c69a16f924c11adeedbb31591f6fad9f41b2

git clone https://github.com/FreeRTOS/FreeRTOS-Kernel-Book
git -C FreeRTOS-Kernel-Book checkout ba20b2f820926587d5ee20ce312b3789d63f795c
```

## Note for ROADMAP lesson E22
E22 ("Modifying Code Without Rotting It") calls for walking a slice of the kernel's git history,
which these stripped snapshots do not carry. When that lesson is authored, re-clone the kernel with
full history (command above, minus the `checkout`) rather than embedding ~255 MB of history here.
