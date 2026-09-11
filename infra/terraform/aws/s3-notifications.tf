# AWS allows exactly one aws_s3_bucket_notification resource per bucket —
# a second one silently overwrites the first on apply rather than merging
# with it. Both Lambdas that react to new uploads (thumbnail.tf,
# upload-validation.tf) are wired up here together instead of each
# declaring their own notification resource.
resource "aws_s3_bucket_notification" "uploads_triggers" {
  bucket = aws_s3_bucket.uploads.id

  lambda_function {
    id                  = "thumbnail"
    lambda_function_arn = aws_lambda_function.thumbnail.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "issue-attachments/"
  }

  lambda_function {
    id                  = "upload-validation"
    lambda_function_arn = aws_lambda_function.upload_validation.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "issue-attachments/"
  }

  depends_on = [
    aws_lambda_permission.allow_s3,
    aws_lambda_permission.allow_s3_upload_validation,
  ]
}
