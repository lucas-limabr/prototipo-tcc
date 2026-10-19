from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from psycopg import sql

from index_optimizer.config import load_settings
from index_optimizer.database.connection import connect
from index_optimizer.errors import IndexOptimizerError

SHARE_HOST = "https://arquivos.receitafederal.gov.br"
SHARE_TOKEN = "YggdBLfdninEJX9"
WEBDAV_ROOT = f"{SHARE_HOST}/public.php/webdav"
SCHEMA = "cnpj"
SQL_DIR = Path(__file__).with_name("sql")
LOOKUPS = {
    "Cnaes": "cnae",
    "Motivos": "motivo_situacao",
    "Municipios": "municipio",
    "Naturezas": "natureza_juridica",
    "Paises": "pais",
    "Qualificacoes": "qualificacao_socio",
}
CHUNK = 1 << 20


class DatasetError(IndexOptimizerError):
    pass


@dataclass(frozen=True)
class RemoteFile:
    name: str
    size: int


def file_names(parts: Iterable[int]) -> list[str]:
    selected = sorted(set(parts))
    invalid = [p for p in selected if not 0 <= p <= 9]
    if invalid or not selected:
        raise DatasetError(f"Partições inválidas: {invalid or 'nenhuma'}; use valores de 0 a 9.")
    names = [f"{prefix}.zip" for prefix in LOOKUPS]
    names += [f"Estabelecimentos{p}.zip" for p in selected]
    names += [f"Empresas{i}.zip" for i in range(10)]
    names += [f"Socios{i}.zip" for i in range(10)]
    return names


def download_url(reference: str, name: str) -> str:
    return f"{WEBDAV_ROOT}/{urllib.parse.quote(reference)}/{urllib.parse.quote(name)}"


def _request(url: str, method: str = "GET", headers: dict[str, str] | None = None):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    req.add_header("Authorization", "Basic " + _basic_token())
    return urllib.request.urlopen(req, timeout=60)


def _basic_token() -> str:
    import base64

    return base64.b64encode(f"{SHARE_TOKEN}:".encode()).decode()


def list_remote(reference: str) -> dict[str, RemoteFile]:
    url = f"{WEBDAV_ROOT}/{urllib.parse.quote(reference)}/"
    try:
        with _request(url, "PROPFIND", {"Depth": "1"}) as resp:
            body = resp.read()
    except OSError as exc:
        raise DatasetError(f"Falha ao listar {url}: {exc}") from exc
    ns = {"d": "DAV:"}
    files: dict[str, RemoteFile] = {}
    for node in ET.fromstring(body).findall("d:response", ns):
        size = node.find(".//d:getcontentlength", ns)
        href = node.find("d:href", ns)
        if size is None or href is None or href.text is None:
            continue
        name = urllib.parse.unquote(href.text.rstrip("/").rsplit("/", 1)[-1])
        files[name] = RemoteFile(name, int(size.text or 0))
    if not files:
        raise DatasetError(f"Nenhum arquivo encontrado na referência {reference!r}.")
    return files


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _fetch(url: str, target: Path, expected: int) -> None:
    partial = target.with_suffix(target.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    with _request(url, headers=headers) as resp, partial.open("ab" if offset else "wb") as out:
        if offset and resp.status != 206:
            out.truncate(0)
        while block := resp.read(CHUNK):
            out.write(block)
    if partial.stat().st_size != expected:
        raise DatasetError(
            f"Tamanho divergente em {target.name}: {partial.stat().st_size} != {expected}."
        )
    partial.rename(target)


def download(reference: str, parts: Sequence[int], data_dir: Path) -> Path:
    target_dir = data_dir / reference
    target_dir.mkdir(parents=True, exist_ok=True)
    remote = list_remote(reference)
    manifest: dict[str, dict[str, object]] = {}
    for name in file_names(parts):
        if name not in remote:
            raise DatasetError(f"{name} não existe na referência {reference}.")
        path = target_dir / name
        expected = remote[name].size
        if path.exists() and path.stat().st_size == expected:
            print(f"[ok] {name} já baixado")
        else:
            print(f"[download] {name} ({expected / 1e6:.1f} MB)", flush=True)
            _fetch(download_url(reference, name), path, expected)
        manifest[name] = {"bytes": expected, "sha256": sha256_of(path)}
    meta = {
        "fonte": "Receita Federal do Brasil — Dados Abertos do CNPJ",
        "licenca": "CC-BY",
        "referencia": reference,
        "url": f"{SHARE_HOST}/index.php/s/{SHARE_TOKEN}?dir=/{reference}",
        "obtido_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "particoes_estabelecimentos": sorted(set(parts)),
        "arquivos": manifest,
    }
    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifesto: {manifest_path}")
    return manifest_path


def _copy_zip(cur, zip_path: Path, staging: str) -> int:
    with zipfile.ZipFile(zip_path) as archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        if len(members) != 1:
            raise DatasetError(f"{zip_path.name} deveria conter um único arquivo.")
        statement = sql.SQL(
            "COPY {} FROM STDIN WITH (FORMAT csv, DELIMITER ';', QUOTE '\"', ENCODING 'LATIN1')"
        ).format(sql.Identifier(staging))
        with archive.open(members[0]) as src, cur.copy(statement) as copy:
            while block := src.read(CHUNK):
                copy.write(block.replace(b"\x00", b""))
    return cur.rowcount


def _run_sql(cur, name: str) -> None:
    cur.execute((SQL_DIR / name).read_text(encoding="utf-8"))


def _staging(cur, name: str, columns: int) -> None:
    cols = sql.SQL(", ").join(sql.SQL("c{} text").format(sql.Literal(i)) for i in range(columns))
    cur.execute(
        sql.SQL("CREATE TEMP TABLE IF NOT EXISTS {} ({}) ON COMMIT DELETE ROWS").format(
            sql.Identifier(name), cols
        )
    )


def _register(cur, table: str, files: list[Path], rows: int, manifest: dict) -> None:
    hashes = {f.name: manifest.get("arquivos", {}).get(f.name, {}).get("sha256") for f in files}
    cur.execute(
        "INSERT INTO cnpj.carga (tabela, referencia, arquivos, linhas) VALUES (%s, %s, %s, %s)",
        (table, manifest.get("referencia"), json.dumps(hashes), rows),
    )


def load(
    reference: str,
    data_dir: Path,
    resume: bool = False,
    max_companies: int | None = None,
    max_establishments: int | None = None,
) -> None:
    source = data_dir / reference
    manifest_path = source / "manifest.json"
    if not manifest_path.exists():
        raise DatasetError(f"Manifesto ausente em {source}; execute o download primeiro.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    parts = manifest["particoes_estabelecimentos"]
    settings = load_settings()
    with connect(settings) as conn:
        conn.autocommit = True
        conn.execute("SET statement_timeout = 0")
        with conn.transaction(), conn.cursor() as cur:
            _run_sql(cur, "schema.sql")
        for prefix, table in LOOKUPS.items():
            with conn.transaction(), conn.cursor() as cur:
                _staging(cur, "stg_lookup", 2)
                rows = _copy_zip(cur, source / f"{prefix}.zip", "stg_lookup")
                if not resume:
                    cur.execute(sql.SQL("TRUNCATE cnpj.{} CASCADE").format(sql.Identifier(table)))
                cur.execute(
                    sql.SQL(
                        "INSERT INTO cnpj.{} (codigo, descricao) "
                        "SELECT DISTINCT ON (c0::int) c0::int, c1 FROM stg_lookup "
                        "WHERE c0 ~ '^[0-9]+$' ORDER BY c0::int "
                        "ON CONFLICT (codigo) DO UPDATE SET descricao = EXCLUDED.descricao"
                    ).format(sql.Identifier(table))
                )
                _register(cur, table, [source / f"{prefix}.zip"], cur.rowcount, manifest)
                print(f"[carga] {table}: {cur.rowcount} linhas (lidas {rows})", flush=True)
        with conn.transaction(), conn.cursor() as cur:
            if not resume:
                cur.execute("TRUNCATE cnpj.socio, cnpj.estabelecimento, cnpj.empresa")
        if max_companies is not None or max_establishments is not None:
            if max_companies is None or max_establishments is None:
                raise DatasetError(
                    "Os limites de empresa e estabelecimento devem ser informados juntos."
                )
            _load_limited(
                conn,
                source,
                manifest,
                parts,
                max_companies,
                max_establishments,
            )
        else:
            _load_main(
                conn,
                source,
                manifest,
                "empresa",
                7,
                [f"Empresas{i}.zip" for i in range(10)],
                "insert_empresa.sql",
            )
            _load_main(
                conn,
                source,
                manifest,
                "estabelecimento",
                30,
                [f"Estabelecimentos{p}.zip" for p in parts],
                "insert_estabelecimento.sql",
            )
        with conn.transaction(), conn.cursor() as cur:
            _run_sql(cur, "finalize.sql")
        conn.autocommit = True
        conn.execute("VACUUM ANALYZE")
    print("Carga concluída. Execute 'validate' para conferir contagens e integridade.")


def _load_main(conn, source, manifest, table, columns, files, insert_sql) -> None:
    total = 0
    for name in files:
        with conn.transaction(), conn.cursor() as cur:
            _staging(cur, f"stg_{table}", columns)
            read = _copy_zip(cur, source / name, f"stg_{table}")
            _run_sql(cur, insert_sql)
            total += cur.rowcount
            print(f"[carga] {table} <- {name}: {cur.rowcount} inseridas (lidas {read})", flush=True)
    with conn.transaction(), conn.cursor() as cur:
        _register(cur, table, [source / f for f in files], total, manifest)


def _load_limited(conn, source, manifest, parts, max_companies, max_establishments) -> None:
    if max_companies <= 0 or max_establishments <= 0:
        raise DatasetError("Os limites de carga devem ser maiores que zero.")
    with conn.transaction(), conn.cursor() as cur:
        _staging(cur, "stg_establishment_source", 30)
        read = sum(
            _copy_zip(cur, source / f"Estabelecimentos{part}.zip", "stg_establishment_source")
            for part in parts
        )
        cur.execute(
            """
            CREATE TEMP TABLE selected_cnpj ON COMMIT PRESERVE ROWS AS
            SELECT DISTINCT c0 AS cnpj_basico
            FROM stg_establishment_source
            WHERE NULLIF(trim(c0), '') IS NOT NULL
            ORDER BY c0
            LIMIT %s
            """,
            (max_companies,),
        )
        cur.execute("CREATE UNIQUE INDEX selected_cnpj_pk ON selected_cnpj (cnpj_basico)")
        selected = cur.execute("SELECT count(*) FROM selected_cnpj").fetchone()[0]
        cur.execute(
            """
            CREATE TEMP TABLE selected_establishment ON COMMIT PRESERVE ROWS AS
            SELECT source.*
            FROM stg_establishment_source source
            JOIN selected_cnpj selected ON selected.cnpj_basico = source.c0
            ORDER BY source.c0, source.c1, source.c2
            LIMIT %s
            """,
            (max_establishments,),
        )
        cur.execute("CREATE INDEX selected_establishment_cnpj_idx ON selected_establishment (c0)")
        print(f"[seleção] {selected} empresas com estabelecimento (lidas {read})", flush=True)

    _load_main(
        conn,
        source,
        manifest,
        "empresa",
        7,
        [f"Empresas{i}.zip" for i in range(10)],
        "insert_empresa_limited.sql",
    )
    total = 0
    with conn.transaction(), conn.cursor() as cur:
        _run_sql(cur, "insert_estabelecimento_limited.sql")
        total = cur.rowcount
        print(
            f"[carga] estabelecimento: {total} inseridas (limite {max_establishments})",
            flush=True,
        )
    with conn.transaction(), conn.cursor() as cur:
        _register(
            cur,
            "estabelecimento",
            [source / f"Estabelecimentos{p}.zip" for p in parts],
            total,
            manifest,
        )


def validate() -> int:
    settings = load_settings()
    with connect(settings) as conn:
        cur = conn.execute((SQL_DIR / "validate.sql").read_text(encoding="utf-8"))
        rows = cur.fetchall()
    failures = 0
    for check, value, ok in rows:
        failures += 0 if ok else 1
        print(f"[{'ok' if ok else 'FALHA'}] {check}: {value}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m index_optimizer.datasets.cnpj")
    parser.add_argument("--data-dir", type=Path, default=Path("data/cnpj"))
    sub = parser.add_subparsers(dest="command", required=True)
    down = sub.add_parser("download", help="Baixa os arquivos e gera manifest.json com SHA-256.")
    down.add_argument("--reference", required=True, help="Pasta mensal, ex.: 2026-10.")
    down.add_argument("--parts", type=int, nargs="+", default=[1])
    loader = sub.add_parser("load", help="Carrega (idempotente) os arquivos no schema cnpj.")
    loader.add_argument("--reference", required=True)
    loader.add_argument(
        "--resume",
        action="store_true",
        help="Retoma sem truncar tabelas já carregadas (reprocessa arquivos com upsert).",
    )
    loader.add_argument("--max-companies", type=int, help="Limite de empresas no modo limitado.")
    loader.add_argument(
        "--max-establishments",
        type=int,
        help="Limite de estabelecimentos no modo limitado.",
    )
    sub.add_parser("validate", help="Confere contagens e integridade da carga.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "download":
            download(args.reference, args.parts, args.data_dir)
            return 0
        if args.command == "load":
            load(
                args.reference,
                args.data_dir,
                args.resume,
                args.max_companies,
                args.max_establishments,
            )
            return 0
        return validate()
    except IndexOptimizerError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return int(exc.exit_code)


if __name__ == "__main__":
    sys.exit(main())
