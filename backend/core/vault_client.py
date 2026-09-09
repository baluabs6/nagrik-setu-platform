"""
Thin wrapper around hvac (HashiCorp Vault client).

Auth method: AppRole (role_id / secret_id), suited to a workload running in
an EC2 instance / container rather than a human operator.

Falls back to `default` silently if Vault is unreachable, so local
development without a running Vault instance still works via .env values.
"""
import os
import logging

logger = logging.getLogger(__name__)

_client = None
_authenticated = False


def _get_client():
    global _client, _authenticated
    if _client is not None:
        return _client

    try:
        import hvac

        addr = os.environ.get("VAULT_ADDR")
        role_id = os.environ.get("VAULT_ROLE_ID")
        secret_id = os.environ.get("VAULT_SECRET_ID")

        if not (addr and role_id and secret_id):
            logger.warning("Vault env vars not fully set; skipping Vault auth.")
            return None

        client = hvac.Client(url=addr)
        client.auth.approle.login(role_id=role_id, secret_id=secret_id)
        _authenticated = client.is_authenticated()
        _client = client if _authenticated else None
        return _client
    except Exception as exc:  # noqa: BLE001 - Vault being down must never crash boot
        logger.warning("Vault unavailable, using env/.env fallback: %s", exc)
        return None


def get_secret(key: str, default=None):
    """
    Read `key` from the KV-v2 secret at VAULT_SECRETS_PATH.
    Returns `default` if Vault is unreachable or the key is absent.
    """
    client = _get_client()
    if client is None:
        return default

    path = os.environ.get("VAULT_SECRETS_PATH", "secret/data/nagrik-setu")
    mount_point, _, sub_path = path.partition("/data/")
    try:
        result = client.secrets.kv.v2.read_secret_version(
            path=sub_path or path, mount_point=mount_point or "secret"
        )
        return result["data"]["data"].get(key, default)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vault read failed for key=%s: %s", key, exc)
        return default
