import json
import sys
from pathlib import Path

if __package__:
    from .state_model import delivery_filenames
else:
    from state_model import delivery_filenames


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：python scripts/delivery_paths.py STATE_PATH", file=sys.stderr)
        return 2
    try:
        state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        json_name, xlsx_name = delivery_filenames(state)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"生成交付路径失败：{error}", file=sys.stderr)
        return 1
    print(Path("outputs") / json_name)
    print(Path("outputs") / xlsx_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
