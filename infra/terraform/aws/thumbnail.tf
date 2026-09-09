# Packages backend/lambda/thumbnail/handler.py into a zip at plan time.
# The Pillow dependency ships as a separate layer (built via the AWS SAM
# build image or a prebuilt public layer ARN) rather than bundled here,
# since Pillow has compiled C extensions that must match the Lambda
# runtime's architecture — pip-installing it locally on an arbitrary dev
# machine and zipping it up is a common source of "works on my machine"
# Lambda failures.
data "archive_file" "thumbnail_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../../backend/lambda/thumbnail"
  output_path = "${path.module}/.build/thumbnail-lambda.zip"
  excludes    = ["__pycache__"]
}

resource "aws_iam_role" "thumbnail_lambda" {
  name = "${var.project_name}-thumbnail-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "thumbnail_lambda_basic_logs" {
  role       = aws_iam_role.thumbnail_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "thumbnail_lambda_s3_access" {
  name = "${var.project_name}-thumbnail-lambda-s3"
  role = aws_iam_role.thumbnail_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject"]
      Resource = "${aws_s3_bucket.uploads.arn}/*"
    }]
  })
}

resource "aws_lambda_function" "thumbnail" {
  function_name    = "${var.project_name}-thumbnail-generator"
  role             = aws_iam_role.thumbnail_lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.thumbnail_lambda.output_path
  source_code_hash = data.archive_file.thumbnail_lambda.output_base64sha256
  timeout          = 15
  memory_size      = 512

  # Public Pillow layer maintained by the community (klayers project),
  # pinned to a Python 3.12 / x86_64 build. Swap for a self-built layer
  # if you'd rather not depend on a third-party ARN in production.
  layers = ["arn:aws:lambda:${var.aws_region}:770693421928:layer:Klayers-p312-Pillow:1"]

  environment {
    variables = {
      THUMBNAIL_WIDTH = "320"
    }
  }
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.thumbnail.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.uploads.arn
}

resource "aws_s3_bucket_notification" "uploads_thumbnail_trigger" {
  bucket = aws_s3_bucket.uploads.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.thumbnail.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "issue-attachments/"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
