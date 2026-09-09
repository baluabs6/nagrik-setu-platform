variable "acme_email" {
  description = "Contact email for Let's Encrypt certificate expiry notices"
  type        = string
  default     = "ops@nagriksetu.in"
}

resource "kubernetes_namespace" "cert_manager" {
  metadata {
    name = "cert-manager"
  }
}

resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  namespace  = kubernetes_namespace.cert_manager.metadata[0].name
  version    = "v1.15.1"

  set {
    name  = "installCRDs"
    value = "true"
  }
}

# ClusterIssuer for Let's Encrypt via HTTP-01 challenge, routed through the
# same Azure Application Gateway ingress used by infra/k8s-dr/deployment.yaml.
# Applied as a raw manifest (rather than another Helm values block) since
# cert-manager's CRDs need to exist first — the explicit depends_on enforces
# that ordering.
resource "kubernetes_manifest" "letsencrypt_issuer" {
  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "ClusterIssuer"
    metadata   = { name = "letsencrypt-prod" }
    spec = {
      acme = {
        server = "https://acme-v02.api.letsencrypt.org/directory"
        email  = var.acme_email
        privateKeySecretRef = { name = "letsencrypt-prod-key" }
        solvers = [{
          http01 = {
            ingress = { class = "azure/application-gateway" }
          }
        }]
      }
    }
  }

  depends_on = [helm_release.cert_manager]
}
