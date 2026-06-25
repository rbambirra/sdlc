# Deck — Autonomous SDLC (script de apresentação)

Apresentação da estrutura agêntica autônoma de desenvolvimento de software. Formato: slide +
notas do apresentador. Público: liderança de engenharia / stakeholders + times que vão adotar.
Duração-alvo: 15–20 min. Convenção: **[SLIDE]** = o que está na tela · **Fala:** = narração.

---

## Slide 1 — Abertura
**[SLIDE]** Título: *"Autonomous SDLC — um ciclo de desenvolvimento dirigido por agentes,
verificável e seguro."* Subtítulo: full-agentes ou agentes+humanos, conforme o risco.

**Fala:** "A pergunta não é mais *se* agentes podem escrever software — é como fazê-los entregar
software de produção sem abrir mão de segurança e qualidade. Este é um modelo completo de SDLC
onde agentes percorrem todas as etapas, do ticket ao PR, e humanos entram exatamente onde o risco
justifica. Não é um assistente de código. É um ciclo de entrega."

---

## Slide 2 — O problema
**[SLIDE]** Três caixas: *"Agente escreve código"* → *"...e os próprios testes"* → *"...e diz que
está pronto."* Um X vermelho sobre a última.

**Fala:** "O modo ingênuo de automação falha num ponto: o agente que escreve o código também
escreve os testes e declara 'done'. A literatura tem nome pra isso — *reward hacking*: o agente
enfraquece o próprio teste pra passar. Se quem faz o trabalho também é o juiz, não há garantia
nenhuma. Todo o nosso design parte de uma regra: **um agente nunca é o oráculo da própria prova.**"

---

## Slide 3 — Os princípios
**[SLIDE]** Cinco princípios em ícones: orquestrador+agentes · oráculo independente · mitiga-não-
fecha · template parametrizável · autonomia modulada por risco.

**Fala:** "Cinco princípios sustentam tudo. Um: o Claude orquestra, agentes isolados executam — o
orquestrador decide e delega, nunca implementa. Dois: verificação é uma pilha de sinais
ortogonais, o juiz de IA é a última camada, nunca a única. Três: somos honestos — cada controle
*mitiga*, não *fecha*; segurança vem das camadas. Quatro: é um template — board, repos, regras,
tudo é configurado por projeto. Cinco: a autonomia é modulada por risco — tarefa simples roda
sozinha, tarefa sensível chama o humano."

---

## Slide 4 — O flow, de ponta a ponta
**[SLIDE]** O pipeline horizontal: DoR → Risco → Spec+AC → Escopo → Plano(juiz) → Decomposição →
Dev loop → Gate DoD → Review → PR → DEV-DONE → [deploy opt-in]. Marcar os ✋ (Spec, Plano, Merge).

**Fala:** "Este é o ciclo. Começa por um **Definition of Ready** que bloqueia o que não está
pronto pra desenvolver. Classifica o risco. Lê o requisito na fonte e escreve uma spec com
critérios de aceite testáveis — e aqui o QA já entra, antes de uma linha de código. Decide escopo,
planeja, e o plano passa por um juiz adversarial. Decompõe em tarefas isoladas, cada uma com seu
loop de implementação e revisão. Então o portão de 'done'. Revisão holística. PR. E, se o projeto
quiser, deploy. Os cadeados são os pontos onde o humano aprova — e só aparecem quando o risco pede."

---

## Slide 5 — Definition of Ready e Done
**[SLIDE]** Dois portões: DoR (entrada) e DoD (saída), ambos com selo "definido no setup,
versionado em wiki/git".

**Fala:** "Dois portões dão simetria ao ciclo. O Ready, na entrada, é como decidimos que algo está
pronto pra ser desenvolvido e testado. O Done, na saída, é como decidimos que está realmente
entregue. O ponto crítico: nenhum dos dois é inventado pelo agente em tempo real. São definidos no
**setup do projeto**, documentados em Confluence e git, e podem ser atualizados — com aprovação
humana. O agente aplica o critério, não o define."

---

## Slide 6 — Como medimos "done"
**[SLIDE]** Pilha de gates ortogonais empilhados: held-out tests · mutation · type/lint · contrato
· deps · secret-scan · SAST · E2E real · juiz independente.

**Fala:** "'Done' nunca é um teste verde. É uma pilha de sinais independentes, e o mais importante:
os **held-out tests** — testes que o agente não vê nem pode editar, rodados pela esteira. É a
defesa direta contra o reward hacking. Somamos mutation testing pra medir a *qualidade* da suíte,
checagem de contrato, varredura de dependências, secret scanning, SAST, e E2E contra ambiente
real. Só quando tudo isso fecha é que algo é 'done'."

---

## Slide 7 — O juiz de modelo diferente
**[SLIDE]** Terminal: um plano sendo grelhado → NO-GO (achados) → correção → GO.

**Fala:** "Antes de codar, o plano passa por um juiz adversarial — e de propósito um modelo de
*família diferente* da que escreveu o plano, pra não ter viés de auto-preferência. Ele tenta
quebrar o plano e devolve GO ou NO-GO. O autor não dá nota pra própria prova. O mesmo juiz revisa
o código no fim. Foi assim, aliás, que validamos este próprio modelo — cada decisão passou por
rodadas de um juiz independente até GO."

---

## Slide 8 — Enforcement: a trava, não a promessa
**[SLIDE]** Quatro camadas: Local → CI → Merge protection → CD. Selo: "o agente NÃO pode contornar."

**Fala:** "Aqui está o que torna seguro deixar um agente rodar sozinho. De nada adianta uma regra
se o agente pode editar o arquivo que define a regra. Então: a identidade do agente tem permissão
mínima — não aprova PR, não mexe em branch protection, não escreve secrets. A configuração de
enforcement vive em política de organização, fora do alcance do agente. E o risco é detectado
*semanticamente* — se o agente mover código sensível pra um lugar 'inocente', a análise ainda
pega. 'Não-overridável' aqui é uma trava de verdade, imposta pela infraestrutura."

---

## Slide 9 — Risco modula a autonomia
**[SLIDE]** Uma régua: baixo risco (full-agente) → alto risco (agentes + humano). Caixas
hard-sensitive: auth, pagamento, migração, secrets, infra.

**Fala:** "Nem toda tarefa precisa do mesmo rigor. Uma correção trivial roda full-agente. Algo que
toca autenticação, pagamento, migração de dados ou infraestrutura ativa aprovação humana
obrigatória — e essa não pode ser dispensada pelo agente. A linha entre os dois é uma matriz de
risco que vem no template e cada projeto calibra. E o risco é reavaliado em quatro pontos do ciclo,
não uma vez só — porque uma tarefa pode ficar perigosa no meio do caminho."

---

## Slide 10 — Dois modos, um core
**[SLIDE]** Diagrama: à esquerda o dev rodando um comando; à direita um webhook do Jira/ADO. Os
dois convergem pro mesmo core → sandbox efêmero.

**Fala:** "O mesmo pipeline roda de dois jeitos. Modo dev: o desenvolvedor dispara um comando e
acompanha, com aprovações síncronas. Modo serviço: um webhook do board — um card que entra em
'Ready' — dispara o ciclo sozinho, sem ninguém presente. No modo autônomo, cada job roda num
sandbox descartável, isolado, e os pontos de aprovação humana viram um serviço durável que pausa
e espera a decisão. Mesma lógica, dois gatilhos."

---

## Slide 11 — Deploy e operação
**[SLIDE]** Container na cloud: ingester (stateless) + fila + worker efêmero + vault. Selo:
"observável, retomável, com orçamento."

**Fala:** "Em produção, é conteinerizado e roda na cloud: um recebedor de webhooks que escala,
uma fila durável, e workers efêmeros — um por tarefa. Tudo observável: cada decisão e delegação é
auditável, há correlação do webhook até o PR, orçamento de tokens por job, e detecção de job
travado. E a administração — quem cria a identidade do agente e configura os gates — roda num
caminho separado, com credencial humana, que o agente nunca alcança."

---

## Slide 12 — Adoção incremental
**[SLIDE]** Escada de 8 degraus: core+dev → enforcement → adapters → aprovação → serviço → deploy →
observabilidade → field test.

**Fala:** "Nada disso é big-bang. Cada peça entra como um PR. Começa pelo core no modo dev, que já
entrega valor sem nenhuma infra. Depois enforcement, adapters, o serviço de aprovação, o modo
autônomo, deploy, observabilidade. E então o teste de campo num projeto real. Um time pode parar
no modo dev e já ter ganho, ou ir até o ciclo totalmente autônomo."

---

## Slide 13 — Fechamento
**[SLIDE]** Recap dos 5 princípios + tagline: *"Agentes entregam. Humanos decidem o que importa.
A infraestrutura garante o resto."*

**Fala:** "Resumindo: um ciclo de desenvolvimento onde agentes percorrem todas as etapas, verificado
por sinais independentes que o agente não pode falsear, com humanos exatamente onde o risco pede, e
travas de infraestrutura que tornam 'autônomo' seguro. É um template — qualquer projeto adota e
especializa. Não automatizamos um passo. Construímos o ciclo que entrega o próximo, e o próximo."

---

## Apêndice — referências para perguntas
- Flow completo: `docs/model/autonomous-workflow-model.md`
- Controles de enforcement: `docs/model/enforcement-controls-checklist.md`
- Arquitetura do repositório: `docs/model/repo-architecture.md`
- Documentação de processo: `docs/README.md`
