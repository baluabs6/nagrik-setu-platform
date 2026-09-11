variable "aws_region" {
  description = "Primary AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Short project slug used in resource names"
  type        = string
  default     = "nagrik-setu"
}

variable "vpc_cidr" {
  description = "CIDR block for the application VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDRs for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "availability_zones" {
  description = "AZs to spread subnets and EC2 instances across"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

variable "ec2_instance_type" {
  description = "Instance type for the Django/Docker app servers"
  type        = string
  default     = "t3.medium"
}

variable "ec2_min_size" {
  type    = number
  default = 2
}

variable "ec2_max_size" {
  type    = number
  default = 6
}

variable "ec2_key_name" {
  description = "Existing EC2 key pair name for SSH access (break-glass only; normal access is via SSM)"
  type        = string
  default     = ""
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach EC2 on port 22 (leave empty to disable SSH entirely and rely on SSM)"
  type        = string
  default     = ""
}

variable "s3_bucket_name" {
  description = "S3 bucket for user-uploaded attachments (issue photos, etc.)"
  type        = string
  default     = "nagrik-setu-uploads"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table for the audit/event log"
  type        = string
  default     = "nagrik-setu-events"
}

variable "domain_name" {
  description = "Primary domain the app is served on (used for the ACM cert). Leave empty to skip HTTPS listener provisioning."
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Hosted zone ID for domain_name, needed for ACM DNS validation. Leave empty if validating manually."
  type        = string
  default     = ""
}

variable "primary_postgres_host" {
  description = "Hostname of the primary Postgres instance (RDS endpoint or the app's own EC2-hosted Postgres) that DMS replicates FROM."
  type        = string
  default     = ""
}

variable "primary_postgres_password" {
  description = "Password for the DMS replication user on the primary Postgres. Store in Vault; pass at apply time."
  type        = string
  default     = ""
  sensitive   = true
}

variable "dr_postgres_host" {
  description = "FQDN of the Azure Postgres flexible server DMS replicates TO (output of infra/terraform/azure-dr as dr_postgres_fqdn)."
  type        = string
  default     = ""
}

variable "dr_postgres_password" {
  description = "Password for the DR Postgres admin user (matches postgres_replica_admin_password in the azure-dr stack)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_dr_replication" {
  description = "Set true once both Postgres endpoints exist and are reachable, to provision the DMS replication task."
  type        = bool
  default     = false
}

variable "backend_internal_url" {
  description = "VPC-internal URL of the Django backend (NOT the public domain), used by the upload-validation Lambda's verification callback."
  type        = string
  default     = ""
}

variable "internal_service_token" {
  description = "Shared secret the upload-validation Lambda presents to the backend's internal-only mark-attachment-verified endpoint. Source from Vault/CI secrets at apply time — never commit a real value here."
  type        = string
  default     = "*******"
  sensitive   = true
}
