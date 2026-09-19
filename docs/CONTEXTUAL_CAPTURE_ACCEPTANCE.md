# Aceitação da observação contextual local

Pré-requisito: `npm run check`, `npm test`, `npm run build`. Carregar `dist/` no Chrome e recarregar a página do Mercado Livre. Nenhuma chamada à API Argos é necessária.

- [ ] Abrir anúncio real em BRL e clicar em “Observar preço da página aberta”; comparar valor exibido pela extensão com o preço principal da página.
- [ ] Repetir com Pix/cupom: a extensão deve informar menção e elegibilidade não confirmada, sem aplicar desconto calculado.
- [ ] Trocar variante e observar novamente: não misturar resultados anteriores; preço ambíguo deve ser recusado.
- [ ] Repetir com outra conta/perfil; nunca afirmar automaticamente sessão autenticada ou personalização.
- [ ] Página de bloqueio, sem preço ou loja diferente deve falhar sem preço zero.
- [ ] Confirmar que não houve alteração dos produtos/histórico da V1 nem notificação de preço.
- [ ] Inspecionar mensagens: somente estrutura normalizada, sem URL completa, HTML, cookies ou tokens; nenhum envio ao backend.
- [ ] Validar que cadastro, listagem e remoção locais da V1 continuam funcionando.

Limite conhecido: este primeiro extrator usa apenas a área principal de preço e não resolve vendedor, variante, quantidade, elegibilidade ou sessão. A evidência de testes sintéticos não substitui estes testes reais. Não habilitar ingestão contextual ou alertas antes deste aceite.
