from functools import wraps
from pathlib import Path

import polars as pl


def project_root(marker: str | Path = "pyproject.toml") -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / marker).exists():
            return parent
    raise FileNotFoundError(f"No {marker} found above {current}")


def _is_simple(value) -> bool:
    return isinstance(value, (str, int, float, bool)) and not isinstance(
        value, pl.DataFrame
    )


def save_fig(ext: str = "png"):
    """Decorator that saves the fig returned by a plotting function.

    The wrapped function must return (fig, ax) or fig alone.

    Filename defaults to func.__name__, plus any str/int/float/bool
    args/kwargs appended (so calls with different scalar params don't
    overwrite each other's saved figure).
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            fig = result[0] if isinstance(result, tuple) else result

            parts = [func.__name__]

            for a in args:
                if _is_simple(a):
                    parts.append(str(a))

            for k, v in kwargs.items():
                if _is_simple(v):
                    parts.append(f"{k}-{v}")

            stem = "_".join(parts)
            file_path = project_root() / "figures" / f"{stem}.{ext}"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(file_path)

            return result

        return wrapper

    return decorator
