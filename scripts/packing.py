"""Download and package source data without HTTP dependencies or a build framework."""
import datetime as dt
import gzip
import hashlib
import json
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from pathlib import Path
import re
import shutil
import time
import unicodedata
from urllib.parse import urlparse
from urllib.request import Request, urlopen

CHUNK = 30000
RANGE_BYTES = 8 * 1024 * 1024
RANGE_RETRIES = 6


def normalize(*parts):
    text = " ".join(str(part) for part in parts).lower()
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+|_", " ", text).split())


def clean(value):
    return " ".join((value or "").split())


def day(value):
    try:
        return dt.date.fromisoformat(value[:10]).isoformat()
    except (TypeError, ValueError):
        return ""


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def download(source, path, local):
    """Fetch an immutable CSV in verified segments, with an ordinary GET fallback."""
    if local:
        staged = local / path.name
        if not staged.is_file():
            raise ValueError(f"Missing local source: {staged}")
        return staged, None

    offset, total, failures = 0, None, 0
    validator, modified = None, None
    version_changes = 0
    while total is None or offset < total:
        end = offset + RANGE_BYTES - 1
        headers = {
            "User-Agent": "CoolCode archive snapshot builder/1.0",
            "Accept-Encoding": "identity",
            "Range": f"bytes={offset}-{end}",
        }
        if validator:
            headers["If-Range"] = validator
        try:
            with urlopen(Request(source, headers=headers), timeout=70) as response:
                if urlparse(response.url).scheme != "https" or response.headers.get_content_type().startswith("text/html"):
                    raise ValueError("Unexpected CSV download response.")
                if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                    raise ValueError("Range response is unexpectedly content-encoded.")
                current_modified = response.headers.get("Last-Modified")
                if response.status == 200:
                    # A server can ignore Range or return the entire new version for If-Range.
                    # Do not append such a response to old bytes.
                    staged = path.with_name(f"{path.name}.full")
                    expected = int(response.headers.get("Content-Length", "0"))
                    with staged.open("wb") as stream:
                        shutil.copyfileobj(response, stream, length=1024 * 1024)
                    actual = staged.stat().st_size
                    if expected <= 0 or actual != expected:
                        raise ValueError(f"Full response had {actual:,} of {expected:,} expected bytes.")
                    staged.replace(path)
                    offset = total = expected
                    modified = current_modified
                    break
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                if response.status != 206 or not match:
                    raise ValueError(f"Invalid byte-range response (HTTP {response.status}).")
                begin, stop, current_total = map(int, match.groups())
                if begin != offset or stop != min(end, current_total - 1) or stop < begin:
                    raise ValueError(f"Unexpected byte range {begin}-{stop}/{current_total}.")
                etag = response.headers.get("ETag", "")
                current_validator = etag if etag.startswith('"') else current_modified
                if total is not None and (total != current_total or validator != current_validator):
                    version_changes += 1
                    if version_changes > 2:
                        raise RuntimeError(f"CSV source kept changing during download: {source}")
                    offset, total, validator = 0, None, None
                    raise ValueError("CSV version changed between byte ranges. Starting over.")
                if stop + 1 < current_total and not current_validator:
                    raise ValueError("The source did not publish a version validator for this multi-part CSV.")
                expected = stop - begin + 1
                data = response.read(expected + 1)
                if len(data) != expected:
                    raise ValueError(f"Range had {len(data):,} of {expected:,} expected bytes.")
                with path.open("r+b" if offset else "wb") as stream:
                    stream.seek(offset)
                    stream.write(data)
                    stream.truncate()
                offset, total = stop + 1, current_total
                validator, modified = current_validator, current_modified
                failures = 0
        except (OSError, ValueError, HTTPException) as error:
            failures += 1
            if failures == RANGE_RETRIES:
                raise RuntimeError(f"Could not fetch {source} at byte {offset:,}: {error}") from error
            print(f"Retrying {source} at byte {offset:,}: {error}", flush=True)
            time.sleep(min(16, 2 ** (failures - 1)))
    if path.stat().st_size != total:
        raise ValueError(f"Completed file size does not match the source: {source}")
    updated = parsedate_to_datetime(modified).date().isoformat() if modified else None
    return path, updated


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(root, staging):
    shutil.copytree(root / "web", staging)
    (staging / "data").mkdir()


def pack(staging, group, label, rows):
    files = []
    for offset in range(0, len(rows), CHUNK):
        payload = json.dumps(rows[offset:offset + CHUNK], ensure_ascii=False, separators=(",", ":"))
        version = hashlib.sha256(payload.encode()).hexdigest()[:16]
        name = f"{group}-{offset // CHUNK + 1:03d}-{version}.json.gz"
        with (staging / "data" / name).open("wb") as out:
            out.write(gzip.compress(payload.encode(), compresslevel=5, mtime=0))
        files.append(name)
    return {"id": group, "label": label, "count": len(rows), "shards": files}


def version_assets(staging):
    """Keep modules, styles, data manifests and provincial data in one release graph."""
    hash = hashlib.sha256()
    for path in sorted(staging.rglob("*")):
        if path.is_file():
            hash.update(path.relative_to(staging).as_posix().encode())
            hash.update(digest(path).encode())
    version = hash.hexdigest()[:16]
    def rewrite(match):
        quote, relative = match.group(1), match.group(2)
        target = staging / relative.removeprefix("./")
        if target.is_file() and target.suffix in {".js", ".mjs", ".css", ".json"}:
            return f"{quote}{relative}?v={version}{quote}"
        return match.group(0)
    refs = re.compile(r"([\"'])(\./[^\"'?]+)\1")
    for path in staging.iterdir():
        if path.suffix in {".html", ".js", ".mjs"}:
            path.write_text(refs.sub(rewrite, path.read_text(encoding="utf-8")), encoding="utf-8")
    return version


def finish(output, staging, groups, types, sources, extra=None):
    total = sum(group["count"] for group in groups)
    if total == 0:
        raise ValueError("The source contained no usable records.")
    manifest = {"version": 1, "count": total, "groups": groups, "types": sorted(types, key=str.casefold),
                "sources": sources, "built": dt.datetime.now(dt.timezone.utc).isoformat()}
    if extra:
        manifest.update(extra)
    write(staging / "data" / "manifest.json", manifest)
    version_assets(staging)
    (staging / ".nojekyll").touch()
    if output.exists():
        shutil.rmtree(output)
    staging.replace(output)
    size = sum(p.stat().st_size for p in (output / "data").glob("*.gz"))
    print(f"{total:,} records · {len(groups)} groups · {size / 2**20:.1f} MiB compressed")


def output_path(argument, root):
    result = argument.resolve()
    # Only replace a dedicated build directory. Protect project source and download inputs.
    if result == root or result in root.parents or result == root / "web" or root / "web" in result.parents:
        raise ValueError("Choose a dedicated output directory outside web/.")
    result.parent.mkdir(parents=True, exist_ok=True)
    return result
