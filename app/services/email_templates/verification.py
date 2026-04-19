"""Email verification template."""

from app.services.email_templates.base import render_template


def get_verification_email_html(
    recipient_name: str, verification_link: str, app_name: str = "OptiCredit"
) -> str:
    """Generate HTML for email verification."""
    content = f"""
    <h2>¡Bienvenido/a, {recipient_name}!</h2>
    
    <p>Gracias por registrarte en <strong>{app_name}</strong>. Para activar tu cuenta, necesitamos verificar tu dirección de correo electrónico.</p>
    
    <p>Haz clic en el siguiente botón para verificar tu email:</p>
    
    <p style="text-align: center;">
        <a href="{verification_link}" class="button">Verificar Correo Electrónico</a>
    </p>
    
    <div class="info-box">
        <strong>Nota:</strong> Este enlace expira en 24 horas. Si no verificas tu correo dentro de este plazo, tendrás que solicitar un nuevo enlace de verificación.
    </div>
    
    <p>O copia y pega este enlace en tu navegador:</p>
    <p style="word-break: break-all; font-size: 12px; color: #6b7280;">{verification_link}</p>
    
    <div class="divider"></div>
    
    <p style="font-size: 14px; color: #6b7280;"><strong>¿No te registraste en {app_name}?</strong></p>
    <p style="font-size: 14px; color: #6b7280;">Si no solicitaste este correo, puedes ignorarlo de forma segura. Tu dirección de correo no será utilizada sin tu consentimiento.</p>
    """
    return render_template(
        title=f"Verifica tu correo - {app_name}", content=content, app_name=app_name
    )
