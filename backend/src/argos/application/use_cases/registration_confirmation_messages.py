"""Resumo e respostas públicas da confirmação."""
from argos.application.ports.telegram_registration_confirmation import RegistrationConfirmationReplies
from argos.domain.products.registration import ProductRegistration
from argos.domain.target_price import format_target_price_brl

CONFIRMATION_REPLIES = RegistrationConfirmationReplies(
    created="Produto cadastrado no ambiente de testes. Use /produtos para obter o código e /verificar para consultar o preço. Alertas automáticos ainda não estão disponíveis.",
    corrected="Vamos corrigir o cadastro. Envie novamente a URL do anúncio do Mercado Livre.\n\nUse /cancelar para interromper.",
    duplicate="Você já cadastrou este produto. Use /cancelar para encerrar este rascunho.",
    limit_reached="Você atingiu o limite de três produtos. Use /cancelar para encerrar este rascunho.",
    invalid_data="Os dados do rascunho estão incompletos ou inválidos. Envie corrigir para reiniciar ou use /cancelar.",
    invalid_action="Envie confirmar para cadastrar ou corrigir para reiniciar os dados. Use /cancelar para interromper.",
    no_active_draft="Não há cadastro ativo. Use /adicionar para iniciar.",
    unexpected_state="O rascunho ainda não está pronto para confirmação. Continue a etapa atual ou use /cancelar.",
)


def registration_confirmation_summary(product: ProductRegistration) -> str:
    return (
        f"Confira o cadastro:\n\nURL: {product.url}\nApelido: {product.alias}\n"
        f"Preço-alvo: {format_target_price_brl(product.target_price_cents)}\nIntervalo: {product.interval_hours} horas\n\n"
        "Envie confirmar para cadastrar ou corrigir para reiniciar os dados.\nUse /cancelar para interromper.\n\n"
        "Após cadastrar, use /produtos para obter o código e /verificar para consultar o preço. Alertas automáticos ainda não estão disponíveis."
    )
