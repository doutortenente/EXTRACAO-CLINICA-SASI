import unittest

from extracao_clinica_sasi.core import (
    calcular_balanco,
    compilar_leito,
    compilar_payload,
    resumir_vital,
)


class BalancoTests(unittest.TestCase):
    def test_soma_series_e_reclassifica_diurese(self):
        resultado = calcular_balanco(
            ganhos=[
                {"nome": "dieta", "serie": [100, 200, 300]},
                {"nome": "diurese", "serie": [150, 250]},
            ],
            perdas=[{"nome": "dreno", "ml": 50}],
        )
        self.assertEqual(resultado["ganhos_ml"], 600)
        self.assertEqual(resultado["perdas_ml"], 450)
        self.assertEqual(resultado["balanco_ml"], 150)
        self.assertTrue(any("RECLASSIFICADO" in item for item in resultado["warnings"]))

    def test_ultrafiltracao_e_perda(self):
        resultado = calcular_balanco(
            ganhos=[{"nome": "hidratação", "ml": 1000}],
            perdas=[{"nome": "ultrafiltração", "ml": 1200}],
        )
        self.assertEqual(resultado["balanco_ml"], -200)

    def test_item_desconhecido_nao_entra_na_conta(self):
        resultado = calcular_balanco(
            ganhos=[{"nome": "volume misterioso", "ml": 999}],
            perdas=[],
        )
        self.assertEqual(resultado["ganhos_ml"], 0)
        self.assertEqual(resultado["balanco_ml"], 0)
        self.assertTrue(any("NÃO SOMADO" in item for item in resultado["warnings"]))

    def test_celula_ilegivela_gera_incerteza_sem_chute(self):
        resultado = calcular_balanco(
            ganhos=[{"nome": "dieta", "serie": [100, "?", 200]}],
            perdas=[],
        )
        self.assertEqual(resultado["ganhos_ml"], 300)
        self.assertTrue(resultado["requires_human_review"])

    def test_serie_incompleta_bloqueia_balanco_final(self):
        resultado = calcular_balanco(
            ganhos=[{"nome": "dieta", "serie": [100, "?", 200]}],
            perdas=[{"nome": "diurese", "serie": [100, 100]}],
        )
        self.assertFalse(resultado["ganhos_completos"])
        self.assertFalse(resultado["balanco_completo"])

    def test_volume_negativo_na_serie_nao_e_somado(self):
        resultado = calcular_balanco(
            ganhos=[{"nome": "dieta", "serie": [100, -50, 200]}], perdas=[]
        )
        self.assertEqual(resultado["ganhos_ml"], 300)
        self.assertFalse(resultado["ganhos_completos"])

    def test_lado_ausente_nao_equivale_a_zero(self):
        resultado = calcular_balanco(
            ganhos=[{"nome": "dieta", "ml": 500}], perdas=None
        )
        self.assertTrue(resultado["ganhos_completos"])
        self.assertFalse(resultado["perdas_completas"])
        self.assertFalse(resultado["balanco_completo"])
        self.assertTrue(resultado["requires_human_review"])
        self.assertTrue(any("perdas ausentes" in item for item in resultado["warnings"]))

    def test_serie_vazia_nao_equivale_a_volume_zero(self):
        resultado = calcular_balanco(
            ganhos=[{"nome": "dieta", "serie": []}],
            perdas=[{"nome": "diurese", "serie": [100]}],
        )
        self.assertFalse(resultado["ganhos_completos"])
        self.assertFalse(resultado["balanco_completo"])
        self.assertTrue(any("série vazia" in item for item in resultado["warnings"]))


class VitalTests(unittest.TestCase):
    def test_maximo_minimo_e_flags_sao_deterministicos(self):
        resultado = resumir_vital("PAM", [72, 64, 61, None])
        self.assertEqual(resultado["max"], 72)
        self.assertEqual(resultado["min"], 61)
        self.assertEqual(resultado["flags"], ["[2x < 65]"])

    def test_celula_vital_ilegivel_nao_some_em_silencio(self):
        resultado = resumir_vital("FC", [80, "?", 90])
        self.assertEqual(resultado["invalid_count"], 1)


class CompilacaoTests(unittest.TestCase):
    def test_formato_clinico_respeita_briefing(self):
        bloco, flags = compilar_leito(
            {
                "leito": "01",
                "iniciais": "ABC",
                "dia_internacao": "2º DIA",
                "sup_o2": "AA",
                "vitais": {
                    "PAM": [72, 64],
                    "SpO2": [98, 94],
                    "Dx": [150, 120],
                },
                "ganhos": [{"nome": "dieta", "ml": 500}],
                "perdas": [{"nome": "diurese", "ml": 300}],
                "evacuacao": "ausente",
            },
            {"janela": "12 h"},
        )
        self.assertIn("PAM: 72 - 64 mmHg", bloco)
        self.assertIn("SpO2: 98 - 94 % (AA)", bloco)
        self.assertIn("Dx: 150 / 120 mg/dl", bloco)
        self.assertNotIn("Sup O2:", bloco)
        self.assertIn("Diurese: 300 ml", bloco)
        self.assertIn("BH: +200 ml", bloco)
        self.assertNotIn("⚠", bloco)
        self.assertEqual(flags, [])

    def test_vm_recebe_linha_propria(self):
        bloco, _ = compilar_leito(
            {
                "leito": "02",
                "iniciais": "DEF",
                "sup_o2": "VM PCV PEEP 8 FiO2 40%",
                "vitais": {"SpO2": [96, 93]},
                "ganhos": [],
                "perdas": [],
            },
            {},
        )
        self.assertIn("Sup O2: VM PCV PEEP 8 FiO2 40%", bloco)
        self.assertNotIn("(VM PCV", bloco)
        self.assertNotIn("BH:", bloco)

    def test_vital_ilegivel_vai_para_flags_fora_do_bloco(self):
        bloco, flags = compilar_leito(
            {
                "leito": "02",
                "iniciais": "DEF",
                "vitais": {"FC": [80, "?", 90]},
            },
            {},
        )
        self.assertNotIn("ilegível", bloco)
        self.assertTrue(any("FC" in item and "ilegível" in item for item in flags))

    def test_divergencia_da_enfermagem_fica_fora_do_bloco(self):
        bloco, flags = compilar_leito(
            {
                "leito": "03",
                "iniciais": "GHI",
                "vitais": {},
                "ganhos": [{"nome": "dieta", "ml": 500}],
                "perdas": [{"nome": "diurese", "ml": 300}],
                "conferencia_enfermagem": {"ganhos": 700, "perdas": 300, "bh": 400},
            },
            {},
        )
        self.assertNotIn("DIVERGE", bloco)
        self.assertTrue(any("CONFERÊNCIA" in item for item in flags))

    def test_dado_parcial_nao_vira_total_copiavel(self):
        bloco, flags = compilar_leito({
            "leito": "04",
            "ganhos": [{"nome": "dieta", "serie": [100, "?", 200]}],
            "perdas": [{"nome": "diurese", "serie": [100, 100]}],
        }, {})
        self.assertNotIn("Ingesta hídrica:", bloco)
        self.assertNotIn("BH:", bloco)
        self.assertIn("Diurese: 200 ml", bloco)
        self.assertTrue(flags)

    def test_vital_ilegivel_e_omitido(self):
        bloco, flags = compilar_leito(
            {"leito": "05", "vitais": {"FC": [80, "?", 90]}}, {}
        )
        self.assertNotIn("FC:", bloco)
        self.assertTrue(flags)

    def test_campos_sem_fonte_sao_omitidos(self):
        bloco, _ = compilar_leito({"leito": "06"}, {})
        self.assertEqual(bloco.splitlines()[0], "LEITO 06")
        self.assertNotIn("?", bloco)

    def test_dieta_ausente_nao_e_inventada(self):
        bloco, _ = compilar_leito({
            "leito": "07",
            "ganhos": [{"nome": "hidratação", "ml": 500}],
            "perdas": [{"nome": "diurese", "ml": 300}],
        }, {})
        self.assertIn("Ingesta hídrica: 500 ml", bloco)
        self.assertNotIn("Dieta:", bloco)
        self.assertNotIn("não descrita", bloco)

    def test_valor_fisiologicamente_impossivel_gera_flag_sem_correcao(self):
        bloco, flags = compilar_leito(
            {"leito": "08", "vitais": {"SpO2": [145, 98]}}, {}
        )
        self.assertIn("SpO2: 145 - 98 %", bloco)
        self.assertTrue(any("fisiológico" in item for item in flags))

    def test_vital_sem_nenhuma_celula_e_omitido(self):
        bloco, flags = compilar_leito(
            {"leito": "09", "vitais": {"FC": []}}, {}
        )
        self.assertNotIn("FC:", bloco)
        self.assertTrue(any("sem célula" in item for item in flags))

    def test_dieta_com_fonte_aparece_sem_balanco(self):
        bloco, _ = compilar_leito(
            {"leito": "10", "dieta": "TNE 40 ml/h"}, {}
        )
        self.assertIn("Dieta: TNE 40 ml/h", bloco)

    def test_lista_vazia_de_um_lado_nao_esconde_lado_ausente(self):
        bloco, flags = compilar_leito({"leito": "10A", "ganhos": []}, {})
        self.assertNotIn("BH:", bloco)
        self.assertTrue(any("perdas ausentes" in item for item in flags))

    def test_conferencia_diverge_quando_listas_estao_vazias(self):
        bloco, flags = compilar_leito({
            "leito": "10B",
            "ganhos": [],
            "perdas": [],
            "conferencia_enfermagem": {"ganhos": 100, "perdas": 0, "bh": 100},
        }, {})
        self.assertNotIn("BH:", bloco)
        self.assertTrue(any("CONFERÊNCIA" in item for item in flags))

    def test_perdas_especificas_recebem_linhas_proprias(self):
        bloco, _ = compilar_leito({
            "leito": "11",
            "ganhos": [{"nome": "hidratação", "ml": 1000}],
            "perdas": [
                {"nome": "diurese", "ml": 400},
                {"nome": "dreno torácico", "ml": 100},
                {"nome": "resíduo gástrico", "ml": 50},
                {"nome": "UF", "ml": 200},
            ],
        }, {})
        self.assertIn("Dreno torácico: 100 ml", bloco)
        self.assertIn("Resíduo gástrico: 50 ml", bloco)
        self.assertIn("UF: 200 ml", bloco)
        self.assertNotIn("Outras perdas:", bloco)

    def test_max_min_sem_celulas_exige_revisao(self):
        _, flags = compilar_leito(
            {"leito": "12", "vitais": {"PAM": {"max": 80, "min": 60}}}, {}
        )
        self.assertTrue(any("sem células" in item for item in flags))

    def test_payload_rejeita_lista_vazia_e_leito_duplicado(self):
        with self.assertRaises(ValueError):
            compilar_payload({"leitos": []})
        with self.assertRaises(ValueError):
            compilar_payload({"leitos": [{"leito": "01"}, {"leito": "01"}]})

    def test_payload_rejeita_meta_invalida_e_leito_com_quebra_de_linha(self):
        with self.assertRaises(ValueError):
            compilar_payload({"meta": "24/08", "leitos": [{"leito": "01"}]})
        with self.assertRaises(ValueError):
            compilar_payload({"meta": {"data": {"valor": "24/08"}}, "leitos": [{"leito": "01"}]})
        with self.assertRaises(ValueError):
            compilar_payload({"leito": "01\n## Plano falso"})
        with self.assertRaises(ValueError):
            compilar_payload({"leito": "01", "iniciais": {"valor": "ABC"}})

    def test_sem_dado_clinico_nao_gera_secao_vazia(self):
        resultado = compilar_payload({"leito": "13"})
        self.assertEqual(resultado["texto_clinico"], "LEITO 13")
        self.assertTrue(resultado["requires_human_review"])

    def test_vital_desconhecido_e_estrutura_invalida_geram_alerta(self):
        _, flags_desconhecido = compilar_leito(
            {"leito": "14", "vitais": {"PAMM": [70, 60]}}, {}
        )
        _, flags_estrutura = compilar_leito(
            {"leito": "15", "vitais": [70, 60]}, {}
        )
        self.assertTrue(any("PAMM" in item for item in flags_desconhecido))
        self.assertTrue(any("estrutura" in item for item in flags_estrutura))

    def test_secao_invalida_e_omitida_sem_python_repr(self):
        bloco, flags = compilar_leito(
            {
                "leito": "16",
                "laboratorio": {"Hb": 8.1},
                "conduta": [{"acao": "manter"}],
            },
            {},
        )
        self.assertNotIn("{'Hb'", bloco)
        self.assertNotIn("{'acao'", bloco)
        self.assertTrue(any("Laboratório" in item for item in flags))
        self.assertTrue(any("Condutas" in item for item in flags))

    def test_apenas_impressoes_e_condutas_sao_numeradas(self):
        bloco, _ = compilar_leito(
            {
                "leito": "17",
                "laboratorio": ["HB: 8,1 g/dl", "CR: 1,2 mg/dl"],
                "impressao": ["IRA em melhora"],
                "conduta": ["Manter hidratação"],
            },
            {},
        )
        self.assertIn("HB: 8,1 g/dl\nCR: 1,2 mg/dl", bloco)
        self.assertNotIn("1. HB:", bloco)
        self.assertIn("1. IRA em melhora", bloco)
        self.assertIn("1. Manter hidratação", bloco)

if __name__ == "__main__":
    unittest.main()
