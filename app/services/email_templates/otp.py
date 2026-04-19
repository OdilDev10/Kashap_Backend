"""OTP verification email template."""

from app.services.email_templates.base import render_template


def get_otp_email_html(
    recipient_name: str, otp_code: str, app_name: str = "OptiCredit"
) -> str:
    """Generate HTML for OTP verification email."""
    content = f"""
    <h2>Código de Verificación</h2>
    
    <p>Hola, <strong>{recipient_name}</strong>.</p>
    
    <p>Has solicitado un código de verificación para acceder a tu cuenta en <strong>{app_name}</strong>.</p>
    
    <p>Tu código de verificación es:</p>
    
    <div class="code-box">
        <span class="code">{otp_code}</span>
    </div>
    
    <div class="warning-box">
        <strong>⚠️ Importante:</strong> Este código expira en <strong>10 minutos</strong> por razones de seguridad. No compartas este código con nadie.
    </div>
    
    <p>Si no solicitaste este código, puedes ignorar este correo de forma segura. Es posible que alguien haya ingresado tu dirección de correo por error.</p>
    
    <div class="divider"></div>
    
    <p style="font-size: 14px; color: #6b7280;"><strong>¿No esperabas este correo?</strong></p>
    <p style="font-size: 14px; color: #6b7280;">Si no fuiste tú quien solicitó el código, te recomendamos hacer caso omiso de este correo. Tu cuenta permanece segura.</p>
    """
    return render_template(
        title=f"Código de Verificación - {app_name}", content=content, app_name=app_name
    )
