output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.dr.name
}

output "aks_kube_config" {
  value     = azurerm_kubernetes_cluster.dr.kube_config_raw
  sensitive = true
}

output "acr_login_server" {
  value = azurerm_container_registry.dr.login_server
}

output "dr_postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.dr.fqdn
}

output "dr_redis_hostname" {
  value = azurerm_redis_cache.dr.hostname
}

output "traffic_manager_fqdn" {
  value = azurerm_traffic_manager_profile.failover.fqdn
}
