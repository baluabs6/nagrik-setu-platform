variable "location" {
  description = "Azure region for the DR site — pick one geographically distinct from ap-south-1"
  type        = string
  default     = "centralindia"
}

variable "project_name" {
  type    = string
  default = "nagrik-setu"
}

variable "environment" {
  type    = string
  default = "dr"
}

variable "aks_node_count" {
  description = "Baseline node count — kept small since this cluster is warm-standby, not active"
  type        = number
  default     = 2
}

variable "aks_node_vm_size" {
  type    = string
  default = "Standard_D2s_v5"
}

variable "kubernetes_version" {
  type    = string
  default = "1.29"
}

variable "postgres_replica_admin_password" {
  description = "Admin password for the Azure Postgres read replica (store in Vault, injected via TF_VAR at apply time)"
  type        = string
  sensitive   = true
}
