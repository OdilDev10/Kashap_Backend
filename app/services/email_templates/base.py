"""Base email template and common styling."""

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .email-header {{
            background-color: #1e40af;
            color: white;
            padding: 24px;
            text-align: center;
        }}
        .email-header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .email-body {{
            padding: 32px 24px;
            color: #374151;
            line-height: 1.6;
        }}
        .email-body h2 {{
            color: #1f2937;
            font-size: 20px;
            margin-top: 0;
        }}
        .email-body p {{
            margin: 16px 0;
        }}
        .button {{
            display: inline-block;
            background-color: #1e40af;
            color: white !important;
            padding: 14px 28px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 16px 0;
        }}
        .button:hover {{
            background-color: #1e3a8a;
        }}
        .button-secondary {{
            background-color: #10b981;
        }}
        .button-secondary:hover {{
            background-color: #059669;
        }}
        .code-box {{
            background-color: #f3f4f6;
            border: 2px dashed #d1d5db;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }}
        .code {{
            font-size: 32px;
            font-weight: 700;
            letter-spacing: 4px;
            color: #1e40af;
            font-family: 'Courier New', monospace;
        }}
        .info-box {{
            background-color: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 12px 16px;
            margin: 16px 0;
            border-radius: 0 4px 4px 0;
        }}
        .warning-box {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px 16px;
            margin: 16px 0;
            border-radius: 0 4px 4px 0;
        }}
        .footer {{
            background-color: #f9fafb;
            padding: 16px 24px;
            text-align: center;
            font-size: 12px;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
        .footer a {{
            color: #1e40af;
            text-decoration: none;
        }}
        .divider {{
            border-top: 1px solid #e5e7eb;
            margin: 24px 0;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <h1>{app_name}</h1>
        </div>
        <div class="email-body">
            {content}
        </div>
        <div class="footer">
            <p>Este correo fue enviado por {app_name}</p>
            <p>Si no solicitaste este correo, puedes ignorarlo de forma segura.</p>
            <p>&copy; 2026 {app_name}. Todos los derechos reservados. 🇩🇴</p>
        </div>
    </div>
</body>
</html>
"""


def render_template(title: str, content: str, app_name: str = "OptiCredit") -> str:
    """Render the base template with content."""
    return BASE_TEMPLATE.format(title=title, content=content, app_name=app_name)
