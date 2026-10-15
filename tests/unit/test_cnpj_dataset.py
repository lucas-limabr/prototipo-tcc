import json

import pytest

from index_optimizer.datasets.cnpj import (
    DatasetError,
    download_url,
    file_names,
    sha256_of,
)


def test_file_names_deduplicates_and_sorts_establishment_parts():
    names = file_names([3, 1, 3])

    assert names[:6] == [
        "Cnaes.zip",
        "Motivos.zip",
        "Municipios.zip",
        "Naturezas.zip",
        "Paises.zip",
        "Qualificacoes.zip",
    ]
    assert "Estabelecimentos1.zip" in names
    assert "Estabelecimentos3.zip" in names
    assert "Estabelecimentos2.zip" not in names
    assert names.count("Empresas0.zip") == 1


@pytest.mark.parametrize("parts", [[], [-1], [10], [1, 10]])
def test_file_names_rejects_invalid_parts(parts):
    with pytest.raises(DatasetError):
        file_names(parts)


def test_download_url_quotes_reference_and_filename():
    url = download_url("2026-10/uma pasta", "Estabelecimentos 1.zip")

    assert url.endswith("/2026-10/uma%20pasta/Estabelecimentos%201.zip")


def test_sha256_of_and_manifest_are_reproducible(tmp_path):
    payload = b"cnpj fixture\n"
    path = tmp_path / "fixture.zip"
    path.write_bytes(payload)

    assert sha256_of(path) == "3d12d16fd29130e83e8e2887d1791a71cb7267b38480a85dbded354bdb25d15f"
    manifest = {"arquivos": {path.name: {"bytes": len(payload), "sha256": sha256_of(path)}}}
    assert json.loads(json.dumps(manifest)) == manifest
