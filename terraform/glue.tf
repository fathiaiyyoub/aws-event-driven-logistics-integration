resource "aws_glue_catalog_database" "integration_analytics" {
  name        = replace("${local.common_name_prefix}_analytics", "-", "_")
  description = "Canonical integration event data delivered by Amazon Data Firehose"

  tags = local.common_tags
}

resource "aws_glue_catalog_table" "integration_events" {
  name          = "integration_events"
  database_name = aws_glue_catalog_database.integration_analytics.name
  description   = "Partitioned Parquet representation of Adapter and Worker canonical events"
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL                    = "TRUE"
    "classification"            = "parquet"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2020,2100"
    "projection.year.digits"    = "4"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.month.digits"   = "2"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "projection.day.digits"     = "2"
    "storage.location.template" = "s3://${aws_s3_bucket.data_lake.id}/integration-events/year=$${year}/month=$${month}/day=$${day}/"
  }

  partition_keys {
    name = "year"
    type = "string"
  }

  partition_keys {
    name = "month"
    type = "string"
  }

  partition_keys {
    name = "day"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake.id}/integration-events/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "eventId"
      type = "string"
    }

    columns {
      name = "eventType"
      type = "string"
    }

    columns {
      name = "eventSource"
      type = "string"
    }

    columns {
      name = "timestamp"
      type = "string"
    }

    columns {
      name = "requestEventId"
      type = "string"
    }

    columns {
      name = "requestEventType"
      type = "string"
    }

    columns {
      name = "status"
      type = "string"
    }

    columns {
      name = "message"
      type = "string"
    }

    columns {
      name = "correlation"
      type = "struct<correlationId:string,partnerId:string,sourceSystem:string,originalFormat:string,receivedAt:string>"
    }

    // Known request and response payload properties are nullable, allowing the
    // same schema to represent all current canonical event variants.
    columns {
      name = "payload"
      type = "struct<shipmentId:string,customer:string,destination:string,status:string>"
    }
  }
}
