terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Remote state in S3 with DynamoDB locking. Bootstrap this bucket/table
  # once by hand (or via a separate "bootstrap" state) before running this.
  backend "s3" {
    bucket         = "nagrik-setu-terraform-state"
    key            = "aws/nagrik-setu.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "nagrik-setu-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "nagrik-setu"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
