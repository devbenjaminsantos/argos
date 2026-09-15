# Contrato de fetch seguro do coletor

Estado em 15/09/2026: contrato preparado, sem implementação de fetch. Complementa V2_SECURITY.md. Validação sintática de anúncio existe; DNS, transporte seguro e extração Python ainda não existem. Nenhuma URL deve gerar tráfego pelo futuro coletor antes da suíte negativa aprovada.

## Fronteira e destinos

Coleta recebe somente produto ativo autorizado, carregado por UUID e telegram_user_id. Não expor endpoint de proxy nem receber URL arbitrária para buscar conteúdo. Configuração da política é interna e não pode ser ampliada por mensagens Telegram.

Allowlist inicial exata: mercadolivre.com.br, www.mercadolivre.com.br e produto.mercadolivre.com.br. São destinos planejados, sem prova de acessibilidade ou extração nesta etapa. Revalidar URL a cada execução: HTTPS, porta ausente ou 443, sem credenciais, controles, barra invertida, host literal, ponto final ou nome ambíguo. Não herdar automaticamente a aceitação sintática de qualquer subdomínio. Host fora da política produz falha explícita, mesmo para URL já cadastrada.

Entrada inicial exige caminho de anúncio válido pelo normalizador existente. Redirect deve continuar em host exato permitido e caminho de anúncio; bloqueios/login/interstitials não justificam ampliar a política automaticamente. Resolver Location relativo contra URL atual; remover fragmento e revalidar antes de resolver DNS. Não buscar scripts, imagens ou recursos incorporados.

## DNS e conexão

Resolver A e AAAA com prazo limitado. Rejeitar resposta vazia, inválida, excessiva ou contendo qualquer destino privado, reservado, loopback, link-local, multicast, unspecified ou não global. Classificar IPv4 e IPv6; IPv4 mapeado em IPv6 deve ser avaliado também como IPv4. Definir tabela de ranges e testes explícitos, sem depender somente de heurística da biblioteca.

Resposta mista público/privado é recusada inteira. Limite inicial de 16 endereços, contando o conjunto retornado; não validar somente o primeiro. Cada conexão usa exclusivamente endereço validado desse conjunto, sem segunda resolução implícita pelo cliente HTTP. Preservar hostname original em SNI, verificação de certificado e Host; não desabilitar TLS para conectar por IP. Verificar peer quando o transporte o permitir; testes precisam provar que a conexão usa o endereço aprovado.

Desativar proxies de ambiente, cookies, autenticação e redirects automáticos. Não reutilizar conexão de outro host ou sessão autenticada. Falha de transporte não deve acionar fallback com resolução não validada. Se a biblioteca não permitir fixar destino mantendo TLS/SNI, implementação permanece bloqueada; selecionar adaptador em incremento próprio. DNS falso no teste deve conseguir alternar resposta pública/privada para demonstrar proteção contra rebinding.

## Limites iniciais

| Recurso | Limite planejado |
| --- | --- |
| URL | 2048 caracteres, inclusive em redirects |
| DNS | 3 segundos por resolução, dentro do prazo total |
| Conexão/TLS | 5 segundos, dentro do prazo total |
| Inatividade de leitura | 5 segundos |
| Tempo total | 15 segundos, incluindo DNS, redirects e leitura |
| Redirects | Até 3; ciclos recusados |
| Corpo transferido | 2 MiB |
| Corpo descomprimido | 2 MiB |

Prazo total é monotônico e não reinicia a cada hop/chunk. Streaming contabiliza bytes, mesmo sem Content-Length ou com declaração incorreta; Content-Length excessivo permite rejeição antecipada. Solicitar identidade de encoding; se houver compressão, decoder limitado precisa respeitar ambos os tetos ou recusar encoding sem suporte seguro. Não carregar corpo integral antes de aplicar limites. Aceitar somente sucesso HTTP 200 com conteúdo HTML; outros statuses/MIME produzem erro explícito. Sem execução de JavaScript ou HTML remoto.

Não aplicar retries automáticos neste primeiro adaptador. Política de retry/agendamento pertence ao job futuro e deve limitar tentativas. Erro de coleta nunca vira preço zero.

## Portas e resultados planejados

Aplicação depende de porta de coleta por produto autorizado; domínio não importa cliente HTTP. Infraestrutura separa política de URL/destino, resolvedor DNS e transporte, permitindo substitutos falsos independentes. Sucesso retorna HTML limitado e URL final validada para extrator da loja; HTML não é mensagem Telegram nem material de log.

Falhas devem ser tipadas: invalid_url, host_not_allowed, dns_failed, forbidden_address, redirect_rejected, redirect_limit, timeout, body_too_large, unsupported_encoding, invalid_content_type, http_failed e transport_failed. Não incluir URL completa, query, HTML, cookies ou credenciais em exceptions/logs. Logs podem conter código, host normalizado e correlação. Futuro registro de observação distingue erro e último preço válido; ainda não implementado.

## Critérios de teste e sequência

1. Política pura: hosts exatos, caminhos, portas/credenciais, controles, IPs literais, ranges IPv4/IPv6 e respostas mistas. Não faz rede.
2. Transporte falso: pinning de IP, TLS/Host/SNI preservados, rebinding, nenhum proxy/cookie, redirects relativos/proibidos/cíclicos, múltiplos IPs.
3. Streaming falso: status/MIME, corpos sem comprimento, comprimento mentiroso, teto de bytes, compressão excessiva, prazo total e leitura lenta.
4. Teste controlado do adaptador real para provar resolução única/destino fixado; separado de anúncios reais e sem segredos. Só depois selecionar fixtures de extração da loja e planejar coleta persistida.

Esta preparação não conclui V2.10, não habilita `/verificar` e não substitui a aceitação com dois usuários da V2.9. Próximo incremento: política pura de destinos e suíte negativa, sem chamadas externas.

Política pura implementada em domain/safe_fetch.py: valida hosts exatos e conjuntos DNS completos (máximo 16), rejeita ranges especiais e normaliza IPv4 mapeado. 44 testes locais passaram; CI 34992039718 aprovado em 5489150. Sem resolvedor/transporte ou tráfego externo. Próximo incremento: transporte ao IP validado com TLS/SNI.

Conexão TLS ao IP validado preparada isoladamente em infrastructure/scrapers/pinned_tls.py, sem DNS implícito, mantendo SNI/certificado pelo hostname. Seis testes locais com sockets falsos passaram; CI 34992693219 aprovado em c8a288b. Falhas fecham socket; prazo TCP/TLS compartilhado de até cinco segundos. Ainda faltam resolvedor, HTTP, redirects, streaming limitado e teste controlado real; componente não integrado ao bot.

Orquestração de resolução preparada em resolved_destination.py: resolvedor injetável, conjunto completo validado, teto DNS de três segundos dentro do deadline total e falhas sem detalhes sensíveis. Seis testes locais passaram; CI 35001642812 aprovado em af86bc7. Resolvedor real com I/O interrompível e composição com TLS/HTTP ainda pendentes; não há tráfego externo.

Resolvedor real preparado em system_dns.py: getaddrinfo A/AAAA em subprocesso isolado, timeout encerra e aguarda filho; sem shell, falhas sanitizadas. 16 testes locais de resolução passaram, inclusive interrupção de processo bloqueado sem DNS externo; CI 35001969996 aprovado em 1d45731. Conjunto completo segue para política de IPs. Ainda falta composição HTTP/redirects/streaming e validação controlada de TLS real; não integrado ao bot.

GET limitado preparado em limited_http.py: compõe DNS validado/TLS fixado, HTML 200, identidade de encoding, teto de 2 MiB e prazo monotônico com interrupção do socket. Redirects/compressão recusados. Sete testes falsos passaram; CI 35002727975 aprovado em 7305740. Validação real controlada, redirects seguros e cobertura adicional de streaming/prazo ainda pendentes; não integrado ao bot.

HTTP validado com socketpair real (TLS falso): Connection: close, chunked e corpo excessivo. Corrigido parsing para não fechar socket antes do streaming e fechar response explicitamente. Dez testes locais passaram; CI 35003760138 aprovado em 3e99e14. TLS real controlado e leitura lenta/deadline ainda pendentes; sem rede externa ou coleta no bot.

TLS real validado localmente com certificado efêmero e socketpair: hostname/SNI original aceito e hostname divergente recusado. Leitura HTTP bloqueada interrompida pelo prazo total; 35 testes relacionados passaram. CI 35004349707 aprovado em 35bc1c7. Sem Internet; destino TCP simulado, handshake criptográfico real. Próximo incremento: redirecionamentos com nova validação de URL/DNS/IP por salto e deadline compartilhado. Não integrado ao bot; V2.10 permanece aberta.

Redirecionamentos implementados no transporte isolado: 301/302/303/307/308, até três saltos, ciclos normalizados recusados, Location validado antes de DNS, resolução completa e IP fixado novamente a cada salto. Conexão anterior fechada antes do próximo DNS; corpo de redirect não é lido. Prazo total único preservado. 53 testes relacionados passaram localmente; CI 35004734079 aprovado em 2fdb00a. Cobertura inclui troca de host/IP/Host, rebinding misto e deadline expirado. Não integrado ao bot; próximo incremento: revisar framing HTTP e respostas truncadas antes da extração Mercado Livre.

Framing HTTP endurecido no transporte isolado: Content-Length único com decimal ASCII não negativo; duplicatas, conflito com Transfer-Encoding e codificações de transferência diferentes de chunked recusados. Corpo menor que tamanho declarado e IncompleteRead retornam http_failed, preservando timeout quando prazo expirou. 68 testes relacionados passaram localmente; CI 35005275274 aprovado em 86d7951. Cobertura inclui 13 respostas inválidas e sucessos com tamanho exato/zero em sockets reais. Próximo incremento: devolver HTML limitado junto da URL final validada para a futura extração; ainda sem coletor integrado ao bot.

Resultado do transporte preparado: fetch_html_once retorna FetchedHTML imutável, com html em bytes e final_url do destino validado que respondeu 200. HTML e URL não aparecem no repr padrão. Testes verificam destino direto, redirect relativo e troca de host; 68 testes relacionados passaram localmente; CI 35006082395 aprovado em cb7597a. Sem alteração no bot ou tráfego externo. Próximo incremento: inspecionar o extrator V1 e selecionar fixtures locais para portar a extração Mercado Livre, mantendo falhas explícitas e preços em centavos.
