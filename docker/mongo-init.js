db = db.getSiblingDB("radsight");

db.createCollection("reports");
db.createCollection("findings");
db.createCollection("nlp_entities");
db.createCollection("severity_scores");
db.createCollection("analytics");
db.createCollection("embeddings");
db.createCollection("processing_logs");
db.createCollection("anomaly_logs");
db.createCollection("users");

// Compound indexes for query performance
db.reports.createIndex({ created_at: -1 });
db.reports.createIndex({ severity: 1, created_at: -1 });
db.reports.createIndex({ status: 1 });
db.reports.createIndex({ patient_id: 1, created_at: -1 });
db.reports.createIndex({ report_type: 1, severity: 1 });

db.findings.createIndex({ report_id: 1 });
db.findings.createIndex({ disease: 1, severity: 1 });
db.findings.createIndex({ anatomy: 1 });
db.findings.createIndex({ created_at: -1 });
db.findings.createIndex({ disease: "text", symptoms: "text" });

db.nlp_entities.createIndex({ report_id: 1 });
db.nlp_entities.createIndex({ entity_type: 1 });

db.severity_scores.createIndex({ report_id: 1 }, { unique: true });
db.severity_scores.createIndex({ risk_level: 1, created_at: -1 });
db.severity_scores.createIndex({ score: -1 });

db.analytics.createIndex({ date: -1 });
db.analytics.createIndex({ metric_type: 1, date: -1 });

db.embeddings.createIndex({ report_id: 1 }, { unique: true });
db.embeddings.createIndex({ created_at: -1 });

db.processing_logs.createIndex({ report_id: 1 });
db.processing_logs.createIndex({ status: 1, created_at: -1 });
db.processing_logs.createIndex({ created_at: -1 }, { expireAfterSeconds: 2592000 });

db.anomaly_logs.createIndex({ detected_at: -1 });
db.anomaly_logs.createIndex({ anomaly_type: 1 });

db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ role: 1 });

print("RadSight MongoDB initialized with collections and indexes.");
