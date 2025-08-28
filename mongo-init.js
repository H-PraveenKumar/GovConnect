// MongoDB initialization script
// This script runs when the MongoDB container starts for the first time

// Switch to the schemes database
db = db.getSiblingDB('schemes_db');

// Create collections with validation
db.createCollection('schemes', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["scheme_id", "scheme_name", "pdf_file_id", "upload_date"],
      properties: {
        scheme_id: { bsonType: "string" },
        scheme_name: { bsonType: "string" },
        pdf_file_id: { bsonType: "objectId" },
        upload_date: { bsonType: "date" },
        source: { bsonType: "string" },
        status: { bsonType: "string", enum: ["processing", "completed", "failed"] }
      }
    }
  }
});

db.createCollection('scheme_rules', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["scheme_id", "scheme_name", "eligibility", "required_inputs"],
      properties: {
        scheme_id: { bsonType: "string" },
        scheme_name: { bsonType: "string" },
        eligibility: { bsonType: "object" },
        required_inputs: { bsonType: "array" },
        required_documents: { bsonType: "array" },
        benefit_outline: { bsonType: "string" },
        next_steps: { bsonType: "string" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  }
});

db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "profile", "created_at"],
      properties: {
        user_id: { bsonType: "string" },
        profile: { bsonType: "object" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  }
});

db.createCollection('eligibility_results', {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "scheme_id", "is_eligible", "checked_at"],
      properties: {
        user_id: { bsonType: "string" },
        scheme_id: { bsonType: "string" },
        is_eligible: { bsonType: "bool" },
        reasons: { bsonType: "array" },
        required_documents: { bsonType: "array" },
        checked_at: { bsonType: "date" }
      }
    }
  }
});

// Create indexes for better performance
db.schemes.createIndex({ "scheme_id": 1 }, { unique: true });
db.schemes.createIndex({ "status": 1 });
db.scheme_rules.createIndex({ "scheme_id": 1 }, { unique: true });
db.users.createIndex({ "user_id": 1 }, { unique: true });
db.eligibility_results.createIndex({ "user_id": 1, "scheme_id": 1 }, { unique: true });
db.eligibility_results.createIndex({ "user_id": 1 });
db.eligibility_results.createIndex({ "scheme_id": 1 });

print("Database 'schemes_db' initialized successfully!");
print("Collections created: schemes, scheme_rules, users, eligibility_results");
print("Indexes created for optimal performance");
