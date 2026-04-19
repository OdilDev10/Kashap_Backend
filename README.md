# OptiCredit Backend

Backend FastAPI para OptiCredit.

## Arranque rápido

Desde `backend/`:

```powershell
uv sync --dev
python main.py
```

Opcional con flags:

```powershell
python main.py --host 0.0.0.0 --port 8000 --reload --access-log --log-level debug
```

Healthcheck:

```powershell
curl http://127.0.0.1:8000/health
```

## Seed automático al iniciar

Cada vez que arranca el servidor se ejecuta un seed idempotente (`app/services/startup_seed.py`):

- crea/actualiza financiera demo `lender@opticredit.app`
- crea/actualiza usuarios de prueba
- si ya existen, los actualiza sin duplicar registros

### Credenciales de prueba

Todos usan la misma contraseña:

```text
Test@1234
```

Usuarios:

- `odil.martinez@opticredit.app` -> `platform_admin` (también vinculado a lender demo)
- `lender@opticredit.app` -> `owner` (panel prestamista)
- `cliente@opticredit.app` -> `customer` (panel cliente)

## JWT, roles y permisos

El `access_token` incluye claims de autorización para evitar consultas extra en frontend:

- `role`
- `roles`
- `permissions`
- `account_type`
- `status`
- `lender_id`
- `email`, `first_name`, `last_name`, `phone`

`GET /api/v1/auth/me` responde desde claims del JWT (sin query a DB).

## Notas de autorización

- Endpoints `/api/v1/lender/*` aceptan roles: `platform_admin`, `owner`, `manager`, `reviewer`, `agent`.
- Endpoints `/api/v1/admin/*` aceptan `platform_admin`.
- Endpoints `/api/v1/me/*` son portal cliente autenticado.
