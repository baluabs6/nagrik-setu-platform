terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.14"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.31"
    }
  }

  backend "azurerm" {
    resource_group_name  = "nagrik-setu-tfstate-rg"
    storage_account_name = "nagriksetutfstate"
    container_name       = "tfstate"
    key                  = "azure-dr/nagrik-setu.tfstate"
  }
}

provider "azurerm" {
  features {}
}

provider "helm" {
  kubernetes {
    host                   = azurerm_kubernetes_cluster.dr.kube_config.0.host
    client_certificate     = base64decode(azurerm_kubernetes_cluster.dr.kube_config.0.client_certificate)
    client_key             = base64decode(azurerm_kubernetes_cluster.dr.kube_config.0.client_key)
    cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.dr.kube_config.0.cluster_ca_certificate)
  }
}

provider "kubernetes" {
  host                   = azurerm_kubernetes_cluster.dr.kube_config.0.host
  client_certificate     = base64decode(azurerm_kubernetes_cluster.dr.kube_config.0.client_certificate)
  client_key             = base64decode(azurerm_kubernetes_cluster.dr.kube_config.0.client_key)
  cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.dr.kube_config.0.cluster_ca_certificate)
}
