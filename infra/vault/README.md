# Vault setup for Nagrik Setu

This app authenticates to Vault using **AppRole**, which suits a workload
(EC2 instance / AKS pod) rather than a human operator.

## One-time setup (run against your Vault cluster)

```bash
# 1. Enable the KV v2 secrets engine (skip if already enabled)
vault secrets enable -path=secret kv-v2

# 2. Write the app's secrets
vault kv put secret/nagrik-setu \
  django_secret_key="$(openssl rand -hex 32)" \
  postgres_db="nagrik_setu" \
  postgres_user="nagrik_setu" \
  postgres_password="<strong-password>"

# 3. Load the least-privilege policy
vault policy write nagrik-setu-app nagrik-setu-app-policy.hcl

# 4. Enable AppRole auth and bind it to the policy
vault auth enable approle
vault write auth/approle/role/nagrik-setu \
  token_policies="nagrik-setu-app" \
  token_ttl=1h \
  token_max_ttl=4h

# 5. Fetch the role_id and a secret_id — these go into the app's
#    VAULT_ROLE_ID / VAULT_SECRET_ID (injected via EC2 instance metadata /
#    a Kubernetes Secret populated by the Vault Agent Injector, never
#    committed to source control)
vault read auth/approle/role/nagrik-setu/role-id
vault write -f auth/approle/role/nagrik-setu/secret-id
```

## How the app consumes this

`backend/core/vault_client.py` logs in with `role_id` + `secret_id`, reads
the KV-v2 path in `VAULT_SECRETS_PATH`, and falls back to `.env` values if
Vault is unreachable — so local development never requires a running Vault
instance, but production always prefers Vault-sourced secrets.

## On the DR side (Azure/AKS)

Run the same Vault cluster (or a Vault Enterprise DR replication cluster)
reachable from AKS, and use the [Vault Agent Injector for
Kubernetes](https://developer.hashicorp.com/vault/docs/platform/k8s/injector)
to mount the same secrets into the DR pods via annotations on the
deployment, rather than re-implementing the AppRole login in-cluster.
