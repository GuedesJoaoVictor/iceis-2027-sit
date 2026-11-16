"""Prompt templates of the study, verbatim (in Portuguese, the language of the dossiers and of the regulation).

Placeholders, as in the platform's templates: {{instructions}}, {{context}}, {{document_text}}, {{image_count}}.
The blocks that differ between conditions (regulatory context, citation request, photo request, checklist) are placed
next to the final instruction, after the dossier. CONDITIONS at the end of the file assembles the ten conditions of
Table 2; the photo conditions and the draft-opinion prompts are listed for reference (the simulator has no photos).
"""

# Task instruction. It is also the "fixed query" of the fixed-RAG baseline.
INSTRUCTIONS = ("Quais evidências e requisitos a Portaria 310/2020 exige para a certificação higiênico-sanitária "
                "de embarcações pesqueiras? Analise o dossiê e decida se a certificação deve ser deferida ou indeferida.")

HEADER = """Voce e um analista tecnico da certificacao higienico-sanitaria de embarcacoes pesqueiras.
Tarefa: {{instructions}}
Com base no dossie do processo abaixo, verifique cada requisito (programa de autocontrole, declaracao de responsabilidade, treinamento da tripulacao, registros de controle a bordo, documento do material de revestimento, laudo de potabilidade da agua, declaracao do fornecedor de agua, controle de pragas) e classifique como ATENDE, NAO ATENDE ou NAO VERIFICAVEL. Liste as nao conformidades e decida.
"""

RAG_BLOCK = """
Contexto normativo recuperado (cite a fonte no formato [Source: arquivo, Art. N]; a portaria mais recente prevalece):
{{context}}
"""

# Whole regulation in the prompt (the 49 passages of the index, in order, with the same labels) instead of retrieval.
FULL_REGULATION_BLOCK = """
Texto integral das normas aplicaveis (cite a fonte no formato [Source: arquivo, Art. N]; a portaria mais recente prevalece):
{{context}}
"""

FOOTER = """
DOSSIE:
{{document_text}}

Responda com a analise por requisito e termine com uma ultima linha exatamente no formato:
RECOMENDACAO: DEFERIR
ou
RECOMENDACAO: INDEFERIR"""

CITATION_REMINDER = """
Ao justificar cada requisito, cite o dispositivo normativo usado no formato [Source: arquivo, Art. N], com os rotulos do contexto normativo acima.
"""

# Photos in order and numbered (main evaluation): up to 30 photos, the number of each photo written on the image.
PHOTOS_REMINDER = """
Foram anexados a esta mensagem {{image_count}} registros fotograficos do processo, como imagens, na ordem do processo. O numero de cada foto no processo esta escrito no canto superior esquerdo da imagem (FOTO N); quando o processo tem mais de 30 fotos, elas sao uma amostra distribuida ao longo de toda a sequencia e os numeros escritos sao os do processo. Examine as fotos para verificar os requisitos que dependem de evidencia visual (condicoes higienico-sanitarias e estrutura da embarcacao, superficies em contato com o pescado, local de armazenamento do pescado, saida da agua do gelo fundente, sinais de pragas) e classifique tambem o requisito registros fotograficos (fotos suficientes, legiveis e da embarcacao) como ATENDE, NAO ATENDE ou NAO VERIFICAVEL. Ao usar uma foto, cite-a como [Foto N], com o numero escrito nela.
"""

# All the photos of the case (no sampling).
ALL_PHOTOS_REMINDER = PHOTOS_REMINDER.replace(
    "; quando o processo tem mais de 30 fotos, elas sao uma amostra distribuida ao longo de toda a sequencia e os numeros escritos sao os do processo", "")

# First round only (photos without labels; their order was not preserved, see the paper).
PHOTOS_REMINDER_FIRST_ROUND = """
Foram anexados a esta mensagem {{image_count}} registros fotograficos do processo, como imagens, na ordem do processo (Foto 1, Foto 2, ...); quando o processo tem mais de 30 fotos, eles sao uma amostra distribuida ao longo de toda a sequencia. Examine as fotos para verificar os requisitos que dependem de evidencia visual (condicoes higienico-sanitarias e estrutura da embarcacao, superficies em contato com o pescado, local de armazenamento do pescado, saida da agua do gelo fundente, sinais de pragas) e classifique tambem o requisito registros fotograficos (fotos suficientes, legiveis e da embarcacao) como ATENDE, NAO ATENDE ou NAO VERIFICAVEL. Ao usar uma foto, cite-a como [Foto N].
"""

# Expected evidence (completeness hypothesis): 12 documents and 13 photographic views taken from the help text of the
# PNIP submission form, one per line with a code.
CHECKLIST = """
Lista de evidencias esperadas pela PNIP (orientacoes do formulario de solicitacao):
D1 Programa de autocontrole da embarcacao
D2 Fichas e planilhas de registro dos controles a bordo (instrucoes de trabalho, monitoramentos, registros)
D3 Registros de treinamento da tripulacao com registro de presenca
D4 Registros de treinamento com os assuntos abordados
D5 Registros de treinamento com o nome da embarcacao
D6 Documento tecnico do material de revestimento das superficies que entram em contato com o pescado
D7 Comprovante de controle de pragas e roedores: empresa especializada licenciada pela autoridade sanitaria e ambiental, ou habilitacao tecnica para o uso dos praguicidas
D8 Laudo de analise de potabilidade da agua e do gelo
D9 Evidencia que associe o laudo de potabilidade a embarcacao (por exemplo, nota fiscal)
D10 Nota fiscal de compra ou declaracao do fornecedor da agua potavel e do gelo
D11 Declaracao de responsabilidade
D12 Se a embarcacao usa isca-viva: onde a obtem e como a armazena e manipula
F1 Foto da parte externa da embarcacao
F2 Foto das tubulacoes de agua
F3 Foto do motor
F4 Foto do porao
F5 Foto dos banheiros
F6 Foto da cozinha
F7 Foto do dormitorio
F8 Foto dos EPI
F9 Foto das bombas de agua
F10 Se aplicavel: foto do local e das ferramentas de evisceracao
F11 Se aplicavel: foto dos termometros
F12 Se aplicavel: foto do local de armazenamento de agua e gelo
F13 Se aplicavel: foto da pa de agua
Antes de decidir, escreva uma linha para CADA codigo acima, na ordem, no formato "<codigo>: PRESENTE (<documento ou [Foto N]>)", "<codigo>: AUSENTE", "<codigo>: NAO SE APLICA" ou "<codigo>: NAO VERIFICAVEL". As vistas F so podem ser verificadas nas fotos anexadas a esta mensagem: com fotos anexadas, uma vista que nao aparece em nenhuma delas e AUSENTE; sem fotos anexadas, escreva NAO VERIFICAVEL. Um item AUSENTE, ou um documento cujo conteudo nao comprova o que se espera dele, e uma nao conformidade. So depois classifique os requisitos e decida.
"""


def _footer(*reminders):
    return FOOTER.replace("\nResponda com a analise", "".join(reminders) + "\nResponda com a analise", 1)


# condition -> (template, regulatory context: None | "fixed" | "case" | "full", photos: None | "sample" | "all")
CONDITIONS = {
    "text": (HEADER + _footer(), None, None),
    "text_rag_fixed": (HEADER + RAG_BLOCK + _footer(CITATION_REMINDER), "fixed", None),
    "text_rag_case": (HEADER + RAG_BLOCK + _footer(CITATION_REMINDER), "case", None),
    "text_full_regulation": (HEADER + FULL_REGULATION_BLOCK + _footer(CITATION_REMINDER), "full", None),
    "text_checklist": (HEADER + _footer(CHECKLIST), None, None),
    "photos": (HEADER + _footer(PHOTOS_REMINDER), None, "sample"),
    "photos_rag_fixed": (HEADER + RAG_BLOCK + _footer(CITATION_REMINDER, PHOTOS_REMINDER), "fixed", "sample"),
    "photos_rag_case": (HEADER + RAG_BLOCK + _footer(CITATION_REMINDER, PHOTOS_REMINDER), "case", "sample"),
    "all_photos": (HEADER + _footer(ALL_PHOTOS_REMINDER), None, "all"),
    "all_photos_checklist": (HEADER + _footer(ALL_PHOTOS_REMINDER, CHECKLIST), None, "all"),
}

# ---------------------------------------------------------------------------------------------------------------------
# Draft technical opinions (Section "Draft Opinions and the Analysts' Opinions"): same structure as the PNIP opinion.
DRAFT_START = """Você é analista técnico do Departamento da Indústria do Pescado do Ministério da Pesca e Aquicultura e vai redigir o RASCUNHO do parecer técnico de uma solicitação de Certificado Oficial de Boas Práticas Higiênico-Sanitárias a Bordo. O rascunho será revisado por um analista humano, que decide.
Tarefa: {{instructions}}
"""

DRAFT_RAG_BLOCK = """
Contexto normativo recuperado (a portaria mais recente prevalece):
{{context}}
"""

DRAFT_DOSSIER = """
DOSSIÊ DA SOLICITAÇÃO (dados da embarcação, lista de verificação preenchida pelo técnico responsável e texto extraído dos documentos anexados):
{{document_text}}

Foram anexados a esta mensagem {{image_count}} registros fotográficos do processo, como imagens, na ordem do processo. O número de cada foto está escrito no canto superior esquerdo da imagem (FOTO 1, FOTO 2, ...); use esse número ao citá-la.
"""

DRAFT_INSTRUCTIONS = """
INSTRUÇÕES DO PARECER
Redija o parecer em português, com linguagem técnica e objetiva, seguindo exatamente a estrutura abaixo. Não invente documentos, fotos, datas ou dados que não estejam no dossiê ou nas imagens. Para cada item, escolha uma avaliação entre Conforme, Não conforme e Solicitação de complementos, e escreva um comentário curto que diga em qual documento ou foto a avaliação se baseia (cite fotos como [Foto N], usando somente números de 1 a {{image_count}}, e apenas as fotos que mostram o item avaliado, no máximo cinco por item; não liste todas as fotos) e, quando não for Conforme, o que está faltando ou o que o técnico responsável deve corrigir. Se a evidência de um item não estiver no dossiê nem nas fotos, use Solicitação de complementos e diga o que deve ser apresentado. Na seção 3.2, avalie somente os itens da LISTA DE VERIFICAÇÃO PREENCHIDA PELO TÉCNICO RESPONSÁVEL que está no dossiê, com a mesma numeração dela (por exemplo 4.1, 5.1, 6.1, 7.1); não acrescente itens de outras listas. Documentos do dossiê devem ser citados pelo nome (por exemplo, "laudo de potabilidade").CITATION

Use este formato, um bloco por item:

## 3.0. DA EMBARCAÇÃO
### 3.0 Dados básicos da embarcação
Avaliação: <Conforme | Não conforme | Solicitação de complementos>
Comentários: <texto>

## 3.1. DA DOCUMENTAÇÃO
### 3.1 Programa de autocontrole
### 3.2 Fichas e planilhas de registro dos controles a bordo
### 3.3 Registros fotográficos
### 3.4 Registros de treinamento da tripulação
### 3.5 Documento técnico do material de revestimento das superfícies que entram em contato com o pescado
### 3.6 Comprovante documental de controle de pragas e roedores
### 3.7 Laudo de análise de potabilidade da água e do gelo
### 3.8 Nota fiscal de compra ou declaração do fornecedor da água potável e do gelo
### 3.9 Declaração de responsabilidade
### 3.10 Outros documentos relacionados ao controle higiênico-sanitário da embarcação
(cada item com as linhas Avaliação e Comentários)

## 3.2. DA LISTA DE VERIFICAÇÃO
Um bloco para cada item da lista de verificação do dossiê, na mesma numeração:
### <número> <pergunta>
Resposta do técnico: <resposta>
Avaliação: <Conforme | Não conforme | Solicitação de complementos | Não se aplica>
Comentários: <texto>

## 4. CONCLUSÃO
<Um parágrafo dizendo se, após a avaliação documental, das fotos e da lista de verificação, a área técnica opina pelo deferimento (PARECER FAVORÁVEL) ou pelo indeferimento (PARECER DESFAVORÁVEL) da solicitação, resumindo as não conformidades e os complementos necessários.>

Termine com uma última linha exatamente no formato:
RECOMENDACAO: DEFERIR
ou
RECOMENDACAO: INDEFERIR"""

DRAFT_CITATION = (" Fundamente cada avaliação no dispositivo normativo pertinente do contexto normativo acima, citado no formato "
                  "[Source: arquivo, Art. N] com os rótulos desse contexto; use esse formato somente para a norma, nunca para documentos do dossiê.")

DRAFT_CONDITIONS = {  # both send every photo of the case; the second retrieves with queries taken from the case
    "draft": DRAFT_START + DRAFT_DOSSIER + DRAFT_INSTRUCTIONS.replace("CITATION", ""),
    "draft_rag_case": DRAFT_START + DRAFT_RAG_BLOCK + DRAFT_DOSSIER + DRAFT_INSTRUCTIONS.replace("CITATION", DRAFT_CITATION),
}
