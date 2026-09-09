resource "aws_apigatewayv2_vpc_link" "app" {
  name               = "${var.project_name}-vpc-link"
  subnet_ids         = aws_subnet.public[*].id
  security_group_ids = [aws_security_group.alb.id]
}

resource "aws_apigatewayv2_api" "app" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"] # tighten to the real frontend domain in production
    allow_methods = ["GET", "POST", "PATCH", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
  }
}

resource "aws_apigatewayv2_integration" "alb" {
  api_id             = aws_apigatewayv2_api.app.id
  integration_type   = "HTTP_PROXY"
  integration_uri    = aws_lb_listener.http.arn
  integration_method = "ANY"
  connection_type    = "VPC_LINK"
  connection_id      = aws_apigatewayv2_vpc_link.app.id
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.app.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.alb.id}"
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.app.id
  name        = "prod"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      requestId = "$context.requestId"
      status    = "$context.status"
      path      = "$context.path"
      latency   = "$context.responseLatency"
    })
  }
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/apigateway/${var.project_name}"
  retention_in_days = 30
}
