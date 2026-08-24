"""Motor determinístico de compilação clínica SASI."""

from __future__ import annotations

import math
import unicodedata
from typing import Any, Iterable

PERDAS = (
    "diurese",
    "diur",
    "urina",
    "svd",
    "sng",
    "gastric",
    "residuo",
    "dreno",
    "penrose",
    "torax",
    "evacuac",
    "fezes",
    "fistula",
    "vomito",
    "emese",
    "aspirado",
    "sangramento",
    "ultrafiltr",
    "uf",
)
GANHOS = (
    "dieta",
    "nutren",
    "diamax",
    "proline",
    "nutri",
    "tne",
    "npt",
    "enteral",
    "agua",
    "hidrat",
    "soro",
    "sf",
    "sg",
    "ringer",
    "endovenoso",
    "bomba",
    "bic",
    "diluic",
    "medicac",
    "hemocomp",
    "plasma",
    "albumina",
    "ingesta",
    "vo",
)

LIMITES = {
    "PAS": (("lt", 90, "< 90"),),
    "PAD": (("lt", 50, "< 50"),),
    "PAM": (("lt", 65, "< 65"),),
    "FC": (("gt", 100, "> 100"),),
    "FR": (("gt", 20, "> 20"),),
    "SpO2": (("lt", 92, "< 92"),),
    "TAX": (("lt", 35.5, "< 35,5"), ("gt", 37.8, "> 37,8")),
    "Dx": (("lt", 70, "< 70"), ("gt", 180, "> 180")),
}
UNIDADES = {
    "PAS": "mmHg",
    "PAD": "mmHg",
    "PAM": "mmHg",
    "FC": "bpm",
    "FR": "rpm",
    "SpO2": "%",
    "TAX": "ºC",
    "Dx": "mg/dl",
}
ORDEM_VITAIS = ("PAS", "PAD", "PAM", "FC", "FR", "SpO2", "TAX", "Dx")
FAIXAS_FISIOLOGICAS = {
    "PAS": (40, 280),
    "PAD": (20, 160),
    "PAM": (30, 180),
    "FC": (20, 250),
    "FR": (4, 80),
    "SpO2": (0, 100),
    "TAX": (32, 42),
}


def _normalizar(texto: Any) -> str:
    base = unicodedata.normalize("NFKD", str(texto).strip().lower())
    return "".join(char for char in base if not unicodedata.combining(char))


def _casa(nome: str, radical: str) -> bool:
    if radical in {"uf", "sf", "sg", "vo"}:
        return nome == radical or nome.startswith(radical + " ") or f" {radical} " in f" {nome} "
    return nome.startswith(radical) or radical in nome


def classificar_item(nome: Any) -> str | None:
    normalizado = _normalizar(nome)
    for radical in PERDAS:
        if _casa(normalizado, radical):
            return "perda"
    for radical in GANHOS:
        if _casa(normalizado, radical):
            return "ganho"
    return None


def _volume_item(item: dict[str, Any], warnings: list[str]) -> tuple[float | None, bool]:
    nome = item.get("nome", "?")
    if "serie" in item:
        serie = item.get("serie")
        if not isinstance(serie, list):
            warnings.append(f"'{nome}': série inválida — NÃO SOMADO")
            return None, False
        if not serie:
            warnings.append(f"'{nome}': série vazia — NÃO SOMADO")
            return None, False
        valores: list[float] = []
        invalidos = 0
        for valor in serie:
            if (
                not isinstance(valor, bool)
                and isinstance(valor, (int, float))
                and math.isfinite(float(valor))
                and float(valor) >= 0
            ):
                valores.append(float(valor))
            else:
                invalidos += 1
        if invalidos:
            warnings.append(
                f"'{nome}': {invalidos} célula(s) ilegível(is) ou não fisiológica(s) — "
                "soma parcial; revisão humana obrigatória"
            )
        return sum(valores), not invalidos
    valor = item.get("ml")
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        warnings.append(f"'{nome}': volume ausente ou inválido — NÃO SOMADO")
        return None, False
    if not math.isfinite(float(valor)) or float(valor) < 0:
        warnings.append(f"'{nome}': volume não fisiológico — NÃO SOMADO")
        return None, False
    return float(valor), True


def calcular_balanco(
    ganhos: Iterable[dict[str, Any]] | None,
    perdas: Iterable[dict[str, Any]] | None,
) -> dict[str, Any]:
    warnings: list[str] = []
    ganhos_ml = 0.0
    perdas_ml = 0.0
    itens_ganho: list[tuple[str, float]] = []
    itens_perda: list[tuple[str, float]] = []
    completos = {"ganho": ganhos is not None, "perda": perdas is not None}
    if ganhos is None:
        warnings.append("ganhos ausentes — BH não calculado; revisão humana obrigatória")
    if perdas is None:
        warnings.append("perdas ausentes — BH não calculado; revisão humana obrigatória")

    for itens, lado_informado in ((ganhos, "ganho"), (perdas, "perda")):
        if itens is None:
            continue
        if not isinstance(itens, list):
            warnings.append(f"lista de {lado_informado}s inválida — NÃO SOMADA")
            completos[lado_informado] = False
            continue
        for item in itens:
            if not isinstance(item, dict):
                warnings.append("item de balanço inválido — NÃO SOMADO")
                completos[lado_informado] = False
                continue
            nome = str(item.get("nome", "?"))
            categoria = classificar_item(nome)
            if categoria is None:
                warnings.append(f"item '{nome}' desconhecido — NÃO SOMADO")
                completos[lado_informado] = False
                continue
            volume, completo = _volume_item(item, warnings)
            if not completo:
                completos[categoria] = False
            if volume is None:
                continue
            if categoria != lado_informado:
                warnings.append(
                    f"RECLASSIFICADO: '{nome}' veio como {lado_informado.upper()}, é {categoria.upper()}"
                )
            if categoria == "ganho":
                ganhos_ml += volume
                itens_ganho.append((nome, volume))
            else:
                perdas_ml += volume
                itens_perda.append((nome, volume))

    return {
        "ganhos_ml": ganhos_ml,
        "perdas_ml": perdas_ml,
        "balanco_ml": ganhos_ml - perdas_ml,
        "itens_ganho": itens_ganho,
        "itens_perda": itens_perda,
        "warnings": warnings,
        "ganhos_completos": completos["ganho"],
        "perdas_completas": completos["perda"],
        "balanco_completo": completos["ganho"] and completos["perda"],
        "requires_human_review": bool(warnings),
    }


def resumir_vital(nome: str, dados: Any) -> dict[str, Any]:
    exato = isinstance(dados, list)
    if isinstance(dados, dict):
        valores = [dados.get("max"), dados.get("min")]
    elif isinstance(dados, list):
        valores = dados
    else:
        valores = []
    numericos = [
        float(valor)
        for valor in valores
        if not isinstance(valor, bool)
        and isinstance(valor, (int, float))
        and math.isfinite(float(valor))
    ]
    invalid_count = sum(
        1
        for valor in valores
        if valor is not None
        and (
            isinstance(valor, bool)
            or not isinstance(valor, (int, float))
            or not math.isfinite(float(valor))
        )
    )
    maximo = max(numericos) if numericos else None
    minimo = min(numericos) if numericos else None
    flags: list[str] = []
    for operador, referencia, rotulo in LIMITES.get(nome, ()):
        ocorrencias = sum(
            1
            for valor in numericos
            if (valor < referencia if operador == "lt" else valor > referencia)
        )
        if ocorrencias:
            flags.append(f"[{ocorrencias}x {rotulo}]" if exato else f"[≥1x {rotulo}]")
    erros_fisiologicos: list[str] = []
    if nome in FAIXAS_FISIOLOGICAS:
        limite_min, limite_max = FAIXAS_FISIOLOGICAS[nome]
        fora = [valor for valor in numericos if valor < limite_min or valor > limite_max]
        if fora:
            erros_fisiologicos.append(
                f"{nome}: erro fisiológico em {len(fora)} valor(es) fora da faixa "
                f"({limite_min}-{limite_max}) — revisar fonte"
            )
    return {
        "max": maximo,
        "min": minimo,
        "flags": flags,
        "exact_count": exato,
        "invalid_count": invalid_count,
        "physiological_errors": erros_fisiologicos,
    }


def _formatar_numero(valor: float | int | None, uma_casa: bool = False) -> str:
    if valor is None:
        return "?"
    numero = float(valor)
    if uma_casa:
        return f"{numero:.1f}".replace(".", ",")
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:.1f}".replace(".", ",")


def _suporte_eh_vm(suporte: str) -> bool:
    texto = _normalizar(suporte)
    return any(marcador in texto for marcador in ("vm", "vmi", "pcv", "vcv", "peep"))


def _comparar_conferencia(
    conferencia: Any, balanco: dict[str, Any]
) -> list[str]:
    if not isinstance(conferencia, dict):
        return []
    flags: list[str] = []
    for rotulo, chave_calculada, chave_folha in (
        ("Ganhos", "ganhos_ml", "ganhos"),
        ("Perdas", "perdas_ml", "perdas"),
        ("BH", "balanco_ml", "bh"),
    ):
        informado = conferencia.get(chave_folha)
        if not isinstance(informado, (int, float)) or isinstance(informado, bool):
            continue
        calculado = float(balanco[chave_calculada])
        if abs(calculado - float(informado)) > 0.5:
            flags.append(
                f"CONFERÊNCIA — {rotulo}: folha {_formatar_numero(informado)}; células {_formatar_numero(calculado)}"
            )
    return flags


def _texto_linha(valor: Any) -> str:
    """Normaliza campo escalar para uma única linha sem inventar conteúdo."""
    return " ".join(str(valor).split())


def compilar_leito(
    leito: dict[str, Any], meta: dict[str, Any] | None = None
) -> tuple[str, list[str]]:
    meta = meta or {}
    flags_taticos: list[str] = []
    cabecalho = f"LEITO {_texto_linha(leito.get('leito'))}"
    if leito.get("iniciais"):
        cabecalho += f" — {_texto_linha(leito['iniciais'])}"
    if leito.get("dia_internacao"):
        cabecalho += f" — DH {_texto_linha(leito['dia_internacao'])}"
    linhas = [cabecalho]
    data = _texto_linha(meta.get("data", ""))
    turno = _texto_linha(meta.get("turno", ""))
    if data or turno:
        linhas[0] += f" — {data} {turno}".rstrip()
    janela = _texto_linha(meta.get("janela", ""))
    inicio_sinais = len(linhas)
    linhas.extend(["", f"## Sinais vitais + balanço{f' [{janela}]' if janela else ''}:"])

    suporte = _texto_linha(leito.get("sup_o2") or "")
    vitais_brutos = leito.get("vitais")
    if vitais_brutos is None:
        vitais: dict[str, Any] = {}
    elif isinstance(vitais_brutos, dict):
        vitais = vitais_brutos
        desconhecidos = [str(nome) for nome in vitais if nome not in ORDEM_VITAIS]
        for nome in sorted(desconhecidos):
            flags_taticos.append(f"vital desconhecido '{nome}' — linha omitida")
    else:
        vitais = {}
        flags_taticos.append("vitais: estrutura inválida — revisão humana obrigatória")
    for nome in ORDEM_VITAIS:
        if nome not in vitais:
            continue
        resumo = resumir_vital(nome, vitais[nome])
        if resumo["invalid_count"]:
            flags_taticos.append(
                f"{nome}: {resumo['invalid_count']} célula(s) ilegível(is) — revisar fonte"
            )
            continue
        if resumo["max"] is None or resumo["min"] is None:
            flags_taticos.append(f"{nome}: sem célula numérica legível — linha omitida")
            continue
        if not resumo["exact_count"]:
            flags_taticos.append(
                f"{nome}: máximo/mínimo fornecidos sem células da janela — revisão humana obrigatória"
            )
        flags_taticos.extend(resumo["physiological_errors"])
        separador = " / " if nome == "Dx" else " - "
        uma_casa = nome == "TAX"
        valor = (
            f"{_formatar_numero(resumo['max'], uma_casa)}{separador}"
            f"{_formatar_numero(resumo['min'], uma_casa)}"
        )
        linha = f"{nome}: {valor} {UNIDADES[nome]}"
        if nome == "SpO2" and suporte and not _suporte_eh_vm(suporte):
            linha += f" ({suporte})"
        if resumo["flags"]:
            linha += " " + " ".join(resumo["flags"])
        linhas.append(linha)
    if suporte and _suporte_eh_vm(suporte):
        linhas.append(f"Sup O2: {suporte}")

    ganhos_brutos = leito.get("ganhos")
    perdas_brutas = leito.get("perdas")
    tem_balanco = "ganhos" in leito or "perdas" in leito
    if tem_balanco:
        balanco = calcular_balanco(ganhos_brutos, perdas_brutas)
        flags_taticos.extend(balanco["warnings"])
        ganhos = _formatar_numero(balanco["ganhos_ml"])
        diurese = sum(
            volume
            for nome, volume in balanco["itens_perda"]
            if "diur" in _normalizar(nome) or "urina" in _normalizar(nome)
        )
        dieta = _texto_linha(leito.get("dieta")) if leito.get("dieta") is not None else None
        ingesta_confiavel = bool(balanco["itens_ganho"]) and balanco["ganhos_completos"]
        if dieta is not None and ingesta_confiavel:
            linhas.append(f"Dieta: {dieta} | Ingesta hídrica: {ganhos} ml")
        elif dieta is not None:
            linhas.append(f"Dieta: {dieta}")
        elif ingesta_confiavel:
            linhas.append(f"Ingesta hídrica: {ganhos} ml")
        if leito.get("evacuacao") is not None:
            linhas.append(f"Evacuação: {_texto_linha(leito['evacuacao'])}")
        if balanco["perdas_completas"] and (
            diurese or any("diur" in _normalizar(nome) for nome, _ in balanco["itens_perda"])
        ):
            linhas.append(f"Diurese: {_formatar_numero(diurese)} ml")
        if balanco["perdas_completas"]:
            for nome_perda, volume in balanco["itens_perda"]:
                normalizado = _normalizar(nome_perda)
                if "diur" in normalizado or "urina" in normalizado:
                    continue
                rotulo = (
                    "UF"
                    if normalizado == "uf"
                    else nome_perda[:1].upper() + nome_perda[1:]
                )
                linhas.append(f"{rotulo}: {_formatar_numero(volume)} ml")
        tem_item_balanco = bool(balanco["itens_ganho"] or balanco["itens_perda"])
        if balanco["balanco_completo"]:
            if tem_item_balanco:
                sinal = "+" if balanco["balanco_ml"] >= 0 else ""
                linhas.append(f"BH: {sinal}{_formatar_numero(balanco['balanco_ml'])} ml")
            flags_taticos.extend(
                _comparar_conferencia(leito.get("conferencia_enfermagem"), balanco)
            )
    else:
        if leito.get("dieta") is not None:
            linhas.append(f"Dieta: {_texto_linha(leito['dieta'])}")
        if leito.get("evacuacao") is not None:
            linhas.append(f"Evacuação: {_texto_linha(leito['evacuacao'])}")

    if len(linhas) == inicio_sinais + 2:
        del linhas[inicio_sinais:]

    secoes = (
        ("## Laboratório:", "Laboratório", leito.get("laboratorio"), False),
        ("## Terapias vigentes:", "Terapias vigentes", leito.get("terapias"), False),
        ("## Exame físico:", "Exame físico", leito.get("exame_fisico"), False),
        ("## Evolução / Eventos 24 h:", "Evolução", leito.get("evolucao"), False),
        ("## Impressão / Problemas ativos:", "Impressão", leito.get("impressao"), True),
        (
            "## Plano terapêutico e Condutas:",
            "Plano terapêutico e Condutas",
            leito.get("conduta"),
            True,
        ),
    )
    for titulo, rotulo, conteudo, numerar in secoes:
        if conteudo in (None, "", []):
            continue
        if isinstance(conteudo, str):
            itens_secao = [conteudo.strip()] if conteudo.strip() else []
        elif isinstance(conteudo, list) and all(isinstance(item, str) for item in conteudo):
            itens_secao = [item.strip() for item in conteudo if item.strip()]
        else:
            flags_taticos.append(
                f"{rotulo}: estrutura inválida — seção omitida; revisão humana obrigatória"
            )
            continue
        if not itens_secao:
            continue
        linhas.extend(["", titulo])
        if numerar:
            linhas.extend(
                f"{indice}. {item}" for indice, item in enumerate(itens_secao, 1)
            )
        else:
            linhas.extend(itens_secao)

    if len(linhas) == 1:
        flags_taticos.append("nenhum dado clínico válido — revisão humana obrigatória")
    return "\n".join(linhas), flags_taticos


def compilar_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload deve ser um objeto JSON")
    if "meta" in payload and not isinstance(payload["meta"], dict):
        raise ValueError("meta deve ser um objeto JSON")
    meta = payload.get("meta", {})
    for campo in ("unidade", "data", "turno", "janela"):
        valor = meta.get(campo)
        if valor is not None and (
            isinstance(valor, bool) or not isinstance(valor, (str, int, float))
        ):
            raise ValueError(f"meta.{campo} deve ser um valor escalar")
    leitos = payload.get("leitos") if "leitos" in payload else [payload]
    if not isinstance(leitos, list) or not all(isinstance(item, dict) for item in leitos):
        raise ValueError("leitos deve ser uma lista de objetos")
    if not leitos:
        raise ValueError("leitos não pode ser uma lista vazia")
    blocos: list[str] = []
    flags: list[dict[str, str]] = []
    identificadores: set[str] = set()
    for leito in leitos:
        identificador = leito.get("leito")
        if (
            identificador is None
            or isinstance(identificador, bool)
            or not isinstance(identificador, (str, int))
            or not str(identificador).strip()
        ):
            raise ValueError("leito é obrigatório; dado sem destino não pode ser compilado")
        identificador_texto = str(identificador).strip()
        if "\n" in identificador_texto or "\r" in identificador_texto:
            raise ValueError("leito não pode conter quebra de linha")
        chave = identificador_texto.upper()
        if chave.isdigit():
            chave = str(int(chave))
        if chave in identificadores:
            raise ValueError(f"leito duplicado: {identificador}")
        identificadores.add(chave)
        for campo in ("iniciais", "dia_internacao", "sup_o2", "dieta", "evacuacao"):
            valor = leito.get(campo)
            if valor is not None and (
                isinstance(valor, bool) or not isinstance(valor, (str, int, float))
            ):
                raise ValueError(f"{campo} deve ser um valor escalar")
        bloco, itens = compilar_leito(leito, meta)
        blocos.append(bloco)
        for item in itens:
            flags.append({"leito": str(leito.get("leito", "?")), "mensagem": item})
    return {
        "texto_clinico": "\n\n".join(blocos),
        "flags_taticos": flags,
        "requires_human_review": bool(flags),
    }
