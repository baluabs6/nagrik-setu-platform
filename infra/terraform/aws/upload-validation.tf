# Companion to thumbnail.tf: validates that uploaded objects are really
# images (not just client-labelled as such), strips EXIF/GPS metadata, and
# deletes anything that fails the check. See
# backend/lambda/upload_validation/handler.py for the implementation and
# core/internal_views.py for the callback it hits on success.

data "archive_file" "upload_validation_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../../backend/lambda/upload_validation"
  output_path = "${path.module}/.build/upload-validation-lambda.zip"
  excludes    = ["__pycache__"]
}

resource "aws_iam_role" "upload_validation_lambda" {
  name = "${var.project_name}-upload-validation-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "upload_validation_lambda_basic_logs" {
  role       = aws_iam_role.upload_validation_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Least privilege: this function only ever needs to read, overwrite, or
# delete objects under the issue-attachments/ prefix it's triggered on —
# never the thumbnails prefix, never any other bucket.
resource "aws_iam_role_policy" "upload_validation_lambda_s3_access" {
  name = "${var.project_name}-upload-validation-lambda-s3"
  role = aws_iam_role.upload_validation_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
      Resource = "${aws_s3_bucket.uploads.arn}/issue-attachments/*"
    }]
  })
}

resource "aws_lambda_function" "upload_validation" {
  function_name    = "${var.project_name}-upload-validation"
  role             = aws_iam_role.upload_validation_lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.upload_validation_lambda.output_path
  source_code_hash = data.archive_file.upload_validation_lambda.output_base64sha256
  timeout          = 15
  memory_size      = 512

  layers = ["arn:aws:lambda:${var.aws_region}:770693421928:layer:Klayers-p312-Pillow:1"]

  environment {
    variables = {
      MAX_UPLOAD_BYTES     = "8388608" # 8 MB, must match IssueViewSet.MAX_UPLOAD_BYTES
      # Internal-only backend URL (VPC-private ALB listener / service
      # discovery name), not the public-facing domain.
      BACKEND_INTERNAL_URL   = var.backend_internal_url
      # Sourced from var.internal_service_token (see variables.tf) — never
      # hardcode the real value here. Consider SSM Parameter Store /
      # Secrets Manager instead of a plain Terraform variable if you'd
      # rather it never transit a .tfvars file at all.
      BACKEND_INTERNAL_TOKEN = var.internal_service_token
    }
  }
}

resource "aws_lambda_permission" "allow_s3_upload_validation" {
  statement_id  = "AllowS3InvokeUploadValidation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_validation.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.uploads.arn
}

# NOTE: the actual aws_s3_bucket_notification resource lives in
# s3-notifications.tf, not here — AWS only allows one notification
# configuration per bucket, so both this Lambda's trigger and the
# thumbnail Lambda's trigger (thumbnail.tf) are declared together there
# instead of as two competing resources that would each overwrite the
# other's config on apply.
