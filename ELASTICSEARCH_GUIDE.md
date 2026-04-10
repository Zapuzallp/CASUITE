# Elasticsearch Global Search Setup Guide

## Quick Setup Steps

### 1. Install Dependencies
```bash
pip install elasticsearch django-elasticsearch-dsl
```

### 2. Start Elasticsearch
Choose one option:

**Option A: Docker (Recommended)**
```bash
docker run -d --name elasticsearch -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.1
```

**Option B: Local Installation**
- Download from https://www.elastic.co/downloads/elasticsearch
- Extract and run `bin/elasticsearch`

### 3. Verify Elasticsearch is Running
```bash
curl http://localhost:9200
```
You should see JSON response with cluster info.

### 4. Create Search Indexes with Permission Fields
```bash
python manage.py search_index --rebuild
```

### 5. Test Permission Filtering (Optional)
```bash
# Test with a specific user
python manage.py test_search_permissions --user admin --query "test"

# Test all user types
python manage.py test_search_permissions --query "client"
```

### 6. Start Django Server
```bash
python manage.py runserver
```

## Permission System

The search now implements production-grade permission filtering:

### User Roles & Access:

**Superuser/Admin:**
- Can see all records across all clients

**Branch Manager:**
- Can see clients assigned to them
- Can see clients created by them  
- Can see clients from their office branch
- Related records (GST, Tasks, Invoices) inherit client permissions

**Staff:**
- Can see clients assigned to them
- Can see clients created by them
- Related records (GST, Tasks, Invoices) inherit client permissions

**Leads:**
- Users can see leads created by them or assigned to them

**Employees:**
- Only visible to Admin and Branch Manager roles

### Permission Fields in Elasticsearch:

Each document now includes permission metadata:
```json
{
  "client_id": 12,
  "assigned_ca_id": 7,
  "created_by_id": 7,
  "office_location_id": 3
}
```

### Performance Benefits:

- Permission filtering happens at Elasticsearch query level
- No post-processing of results needed
- Maintains fast search performance even with large datasets
- Automatic fallback to database search with same permission rules

## Environment Variables (Optional)

For production, set:
```bash
export ELASTICSEARCH_HOST=http://your-elasticsearch-server:9200
```

## Troubleshooting

**Elasticsearch not starting?**
```bash
# Check if port 9200 is free
netstat -an | grep 9200

# Check Docker container
docker ps | grep elasticsearch
```

**Index issues?**
```bash
# Delete and recreate indexes with permission fields
python manage.py search_index --delete --rebuild
```

**Permission testing:**
```bash
# Test specific user permissions
python manage.py test_search_permissions --user username --query "search_term"
```

## Security Notes

- All search results are filtered by user permissions at query time
- No unauthorized data can be returned from Elasticsearch
- Database fallback maintains same permission rules
- Permission metadata is automatically updated when models change