resource "aws_dynamodb_table" "events" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tracking_id"

  attribute {
    name = "tracking_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = { Name = var.dynamodb_table_name }
}

# Also used as the Terraform state lock table referenced in main.tf's
# backend block. Provisioned once via a bootstrap step, kept here for
# visibility into its schema.
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "nagrik-setu-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
