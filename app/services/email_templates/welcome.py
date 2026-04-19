"""Welcome email template."""

from app.services.email_templates.base import render_template


def get_welcome_email_html(
    recipient_name: str,
    app_name: str = "OptiCredit",
    app_url: str = "http://localhost:3000",
) -> str:
    """Generate HTML for welcome email after email verification."""
    content = f"""
    <h2>¡Bienvenido/a, {recipient_name}!</h2>
    
    <p>Tu cuenta en <strong>{app_name}</strong> ha sido verificada exitosamente.</p>
    
    <p>Ahora puedes acceder a todos los servicios de <strong>{app_name}</strong>:</p>
    
    <p style="text-align: center;">
        <a href="{app_url}" class="button">Ir a mi Cuenta</a>
    </p>
    
    <div class="info-box">
        <strong>¿Qué puedes hacer en {app_name}?</strong>
        <ul style="margin: 8px 0 0 0; padding-left: 20px;">
            <li>Gestionar tus préstamos</li>
            <li>Realizar pagos en línea</li>
            <li>Verificar el estado de tus solicitudes</li>
            <li>Actualizar tu información personal</li>
        </ul>
    </div>
    
    <p>Si tienes alguna pregunta o necesitas ayuda, no dudes en contactarnos.</p>
    
    <div class="divider"></div>
    
    <p style="font-size: 14px; color: #6b7280;"><strong>¿Necesitas ayuda?</strong></p>
    <p style="font-size: 14px; color: #6b7280;">Visita nuestro centro de ayuda o contacta a nuestro equipo de soporte.</p>
    """
    return render_template(
        title=f"Bienvenido/a a {app_name}", content=content, app_name=app_name
    )
