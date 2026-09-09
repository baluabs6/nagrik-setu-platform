# nagrik-setu-app.hcl
# Attach this policy to the AppRole the EC2 instances / AKS pods authenticate
# as. Least privilege: read-only, scoped to this app's own KV path.

path "secret/data/nagrik-setu" {
  capabilities = ["read"]
}

path "secret/data/nagrik-setu/*" {
  capabilities = ["read"]
}

# Allow the AppRole to renew its own token but not to escalate privileges.
path "auth/token/renew-self" {
  capabilities = ["update"]
}
