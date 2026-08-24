# 🏥 SASI - Extração e Compilação de Dados Clínicos

> **Sistema de Extração e Compilação de Dados Clínicos para UTI - Dr. Nicolas**
> **Versão:** 1.0.0
> **Data:** 24/08/2026
> **Status:** 🟢 Produção

---

## 📋 Descrição

Sistema especializado em extrair dados clínicos estruturados de:
- Folhas de enfermagem (sinais vitais, balanço hídrico)
- Exames laboratoriais (hemograma, bioquímica, gasometria)
- Prescrições médicas
- Laudos de imagem

O sistema opera sob **regra de ZERO ALUCINAÇÃO**: campos sem fonte legível retornam `null` com warnings, nunca valores inventados.