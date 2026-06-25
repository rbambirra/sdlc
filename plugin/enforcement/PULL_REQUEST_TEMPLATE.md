# Pull Request

> Template do SDLC autônomo. Um check de CI valida que os campos obrigatórios existem
> (não a veracidade — o sinal de risco real vem do re-risking semântico server-side).

## Work item
- ID: <!-- [#123] obrigatório -->
- Escopo: <!-- FE | BE | FE+BE | mixed -->

## O que muda
<!-- descrição objetiva; sem "N/A", omita seções não aplicáveis -->

## Critérios de aceite cobertos
<!-- cada AC com o teste que a prova -->
- [ ] AC1 → teste:
- [ ] AC2 → teste:

## Verificação (gate DoD)
- [ ] Held-out tests verdes
- [ ] Type-check / lint / compile
- [ ] Contrato/OpenAPI (se BE/FE+BE)
- [ ] Deps scan (CVE + slopsquatting)
- [ ] Secret scan + SAST (se security-relevant)
- [ ] E2E real

## Risco
- Classe(s) sensível(eis): <!-- auth/pagamento/migração/secrets/infra/none -->
- [ ] Aprovação humana obtida (se hard-sensitive)
