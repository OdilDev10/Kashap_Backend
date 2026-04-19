"""Password reset email template."""

from app.services.email_templates.base import render_template


def get_password_reset_email_html(
    recipient_name: str, reset_link: str, app_name: str = "OptiCredit"
) -> str:
    """Generate HTML for password reset email."""
    content = f"""
    <h2>Restablecer Contraseña</h2>
    
    <p>Hola, <strong>{recipient_name}</strong>.</p>
    
    <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en <strong>{app_name}</strong>.</p>
    
    <p>Haz clic en el siguiente botón para crear una nueva contraseña:</p>
    
    <p style="text-align: center;">
        <a href="{reset_link}" class="button button-secondary">Restablecer Contraseña</a>
    </p>
    
    <div class="warning-box">
        <strong>⚠️ Importante:</strong> Este enlace expira en <strong>1 hora</strong> por razones de seguridad.
    </div>
    
    <p>Si no solicitaste el restablecimiento de contraseña, ignora este correo. Tu contraseña actual seguirá siendo válida.</p>
    
    <p>O copia y pega este enlace en tu navegador:</p>
    <p style="word-break: break-all; font-size: 12px; color: #6b7280;">{reset_link}</p>
    
    <div class="divider"></div>
    
    <p style="font-size: 14px; color: #6b7280;"><strong>¿No solicitaste este cambio?</strong></p>
    <p style="font-size: 14px; color: #6b7280;">Si no fuiste tú quien solicitó el restablecimiento, es posible que alguien esté intentando acceder a tu cuenta. Te recomendamos ignorar este correo o contactarnos si tienes dudas.</p>
    """
    return render_template(
        title=f"Restablecer Contraseña - {app_name}", content=content, app_name=app_name
    )
