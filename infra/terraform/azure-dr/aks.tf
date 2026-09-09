resource "azurerm_resource_group" "dr" {
  name     = "${var.project_name}-dr-rg"
  location = var.location
}

# Mirrors the images pushed to the primary registry so a failover doesn't
# depend on Docker Hub / GHCR being reachable.
resource "azurerm_container_registry" "dr" {
  name                = "${replace(var.project_name, "-", "")}drregistry"
  resource_group_name = azurerm_resource_group.dr.name
  location            = azurerm_resource_group.dr.location
  sku                 = "Standard"
  admin_enabled       = false
}

resource "azurerm_kubernetes_cluster" "dr" {
  name                = "${var.project_name}-dr-aks"
  resource_group_name = azurerm_resource_group.dr.name
  location            = azurerm_resource_group.dr.location
  dns_prefix          = "${var.project_name}-dr"
  kubernetes_version  = var.kubernetes_version

  default_node_pool {
    name       = "default"
    node_count = var.aks_node_count
    vm_size    = var.aks_node_vm_size
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    load_balancer_sku = "standard"
  }

  tags = {
    role = "disaster-recovery"
  }
}

resource "azurerm_role_assignment" "aks_pull_from_acr" {
  scope                = azurerm_container_registry.dr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.dr.kubelet_identity[0].object_id
}

# --- DR data layer ---
# Warm-standby Postgres: kept in sync from the AWS RDS/EC2-hosted primary via
# logical replication (set up at the application layer — Terraform can't
# create a cross-cloud replication slot). See infra/terraform/azure-dr/README
# in the root README for the runbook.
resource "azurerm_postgresql_flexible_server" "dr" {
  name                   = "${var.project_name}-dr-pg"
  resource_group_name    = azurerm_resource_group.dr.name
  location               = azurerm_resource_group.dr.location
  version                = "16"
  administrator_login    = "nagrik_setu_dr"
  administrator_password = var.postgres_replica_admin_password
  storage_mb             = 32768
  sku_name               = "GP_Standard_D2s_v3"
  zone                   = "1"
}

resource "azurerm_redis_cache" "dr" {
  name                = "${var.project_name}-dr-redis"
  resource_group_name = azurerm_resource_group.dr.name
  location            = azurerm_resource_group.dr.location
  capacity            = 1
  family              = "C"
  sku_name            = "Standard"
  minimum_tls_version = "1.2"
}

# --- DNS failover ---
# Points at the AWS ALB by default; an external health-check/runbook (or
# Azure Front Door's own probes) flips the active endpoint to the AKS
# ingress controller's IP during a real failover.
resource "azurerm_traffic_manager_profile" "failover" {
  name                   = "${var.project_name}-failover"
  resource_group_name    = azurerm_resource_group.dr.name
  traffic_routing_method = "Priority"

  dns_config {
    relative_name = "${var.project_name}-app"
    ttl           = 30
  }

  monitor_config {
    protocol = "HTTPS"
    port     = 443
    path     = "/healthz/"
  }
}
