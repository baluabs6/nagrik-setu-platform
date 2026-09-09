# Cross-cloud DR replication, made concrete: AWS Database Migration Service
# supports "full-load + CDC" (ongoing change data capture) tasks against
# ANY Postgres target reachable over the network — including an Azure
# Postgres Flexible Server on its public endpoint. This is the actual
# mechanism, not just a runbook note: `enable_dr_replication = true` plus
# both host/password variables turns it on.
#
# Requires on the source Postgres: `wal_level = logical` and a replication
# user with REPLICATION privilege — RDS exposes this via a parameter group;
# a self-managed EC2 Postgres needs it set directly in postgresql.conf.

resource "aws_dms_replication_subnet_group" "dr" {
  count                                = var.enable_dr_replication ? 1 : 0
  replication_subnet_group_id          = "${var.project_name}-dr-replication-subnets"
  replication_subnet_group_description = "Subnets for the DMS replication instance"
  subnet_ids                           = aws_subnet.public[*].id
}

resource "aws_security_group" "dms" {
  count       = var.enable_dr_replication ? 1 : 0
  name_prefix = "${var.project_name}-dms-"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # needs to reach the Azure Postgres public endpoint
  }
}

resource "aws_dms_replication_instance" "dr" {
  count                       = var.enable_dr_replication ? 1 : 0
  replication_instance_id     = "${var.project_name}-dr-replication"
  replication_instance_class  = "dms.t3.medium"
  allocated_storage           = 50
  replication_subnet_group_id = aws_dms_replication_subnet_group.dr[0].id
  vpc_security_group_ids      = [aws_security_group.dms[0].id]
  publicly_accessible         = true # must reach the Azure endpoint over the public internet
  multi_az                    = false
}

resource "aws_dms_endpoint" "primary_postgres" {
  count         = var.enable_dr_replication ? 1 : 0
  endpoint_id   = "${var.project_name}-primary-postgres"
  endpoint_type = "source"
  engine_name   = "postgres"
  server_name   = var.primary_postgres_host
  port          = 5432
  database_name = "nagrik_setu"
  username      = "dms_replication_user"
  password      = var.primary_postgres_password

  # Required for CDC against Postgres
  extra_connection_attributes = "pluginName=pglogical;slotName=dms_dr_slot"
}

resource "aws_dms_endpoint" "dr_postgres" {
  count         = var.enable_dr_replication ? 1 : 0
  endpoint_id   = "${var.project_name}-dr-postgres"
  endpoint_type = "target"
  engine_name   = "postgres"
  server_name   = var.dr_postgres_host
  port          = 5432
  database_name = "nagrik_setu"
  username      = "nagrik_setu_dr"
  password      = var.dr_postgres_password
}

resource "aws_dms_replication_task" "dr" {
  count                    = var.enable_dr_replication ? 1 : 0
  replication_task_id      = "${var.project_name}-dr-replication-task"
  replication_instance_arn = aws_dms_replication_instance.dr[0].replication_instance_arn
  source_endpoint_arn      = aws_dms_endpoint.primary_postgres[0].endpoint_arn
  target_endpoint_arn      = aws_dms_endpoint.dr_postgres[0].endpoint_arn

  # full-load-and-cdc: seeds the DR replica once, then streams ongoing
  # changes continuously — this is what keeps it "warm".
  migration_type = "full-load-and-cdc"

  table_mappings = jsonencode({
    rules = [{
      rule-type   = "selection"
      rule-id     = "1"
      rule-name   = "replicate-all-tables"
      object-locator = { schema-name = "public", table-name = "%" }
      rule-action = "include"
    }]
  })

  replication_task_settings = jsonencode({
    Logging = {
      EnableLogging = true
    }
  })
}

# Fires an SNS notification if replication lag or task state indicates the
# DR replica has fallen behind — the earliest useful DR health signal.
resource "aws_sns_topic" "dr_alerts" {
  count = var.enable_dr_replication ? 1 : 0
  name  = "${var.project_name}-dr-alerts"
}

resource "aws_cloudwatch_metric_alarm" "dms_task_stopped" {
  count               = var.enable_dr_replication ? 1 : 0
  alarm_name          = "${var.project_name}-dms-replication-stopped"
  namespace           = "AWS/DMS"
  metric_name         = "CDCLatencySource"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 300 # alert if replication lags more than 5 minutes, 3 periods in a row
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.dr_alerts[0].arn]

  dimensions = {
    ReplicationInstanceIdentifier = aws_dms_replication_instance.dr[0].replication_instance_id
  }
}
