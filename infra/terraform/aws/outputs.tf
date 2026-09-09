output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer"
  value       = aws_lb.app.dns_name
}

output "api_gateway_endpoint" {
  description = "Invoke URL for the HTTP API"
  value       = aws_apigatewayv2_stage.prod.invoke_url
}

output "s3_uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}

output "dynamodb_events_table" {
  value = aws_dynamodb_table.events.name
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "dms_replication_task_arn" {
  description = "ARN of the cross-cloud DR replication task, if enabled"
  value       = var.enable_dr_replication ? aws_dms_replication_task.dr[0].replication_task_arn : null
}

output "thumbnail_lambda_name" {
  value = aws_lambda_function.thumbnail.function_name
}
