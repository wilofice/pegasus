AWS Deployment Plan for Pegasus Backend

  Overview

  Deploy the Pegasus backend as a multi-tier cloud-native application on AWS using containerized services, managed databases, and proper secret management.

  Architecture Strategy

  🏗️ Core Infrastructure (AWS Services)

  1. Container Orchestration

  - AWS ECS Fargate or AWS EKS (Kubernetes)
    - Recommendation: ECS Fargate for simplicity, EKS for advanced control
    - Auto-scaling, load balancing, service discovery
    - Container health checks and rolling deployments

  2. Database Layer (Managed Services)

  - Amazon RDS PostgreSQL → Replace Docker PostgreSQL
    - Multi-AZ for high availability
    - Automated backups, point-in-time recovery
    - Performance Insights, connection pooling
  - Amazon ElastiCache Redis → Replace Docker Redis
    - Redis Cluster mode for scalability
    - Automatic failover, data persistence
  - Amazon Neptune → Replace Neo4j (OR self-hosted Neo4j on EC2)
    - Managed graph database service
    - Alternative: Neo4j Enterprise on EC2 with EBS volumes

  3. Vector Database

  - ChromaDB on ECS → Containerized ChromaDB
    - Persistent EFS storage for vector embeddings
    - Auto-scaling based on query load

  4. Application Services

  - FastAPI Backend → ECS Fargate service
  - Celery Workers → Separate ECS service for background jobs
  - Data Pipeline → ECS Scheduled Tasks or AWS Batch

  📋 Deployment Plan

  Phase 1: Infrastructure Setup (Week 1)

  1.1 Network & Security

  # Create VPC, subnets, security groups
  terraform/cloudformation/cdk
  ├── vpc.tf                 # Private/public subnets, NAT gateway
  ├── security-groups.tf     # Fine-grained access control
  ├── iam.tf                # Service roles, policies
  └── secrets.tf            # AWS Secrets Manager integration

  1.2 Managed Databases

  # RDS PostgreSQL
  - Instance: db.t3.medium (production: db.r6g.large)
  - Multi-AZ: true
  - Backup retention: 7 days
  - Parameter group: Custom for connection pooling

  # ElastiCache Redis  
  - Node type: cache.t3.micro (production: cache.r6g.large)
  - Cluster mode: enabled
  - Auth token enabled

  1.3 Secret Management

  # AWS Secrets Manager entries
  aws secretsmanager create-secret --name pegasus/postgres --secret-string '{
    "username": "pegasus_user",
    "password": "generated-strong-password",
    "host": "pegasus-db.cluster-xxx.region.rds.amazonaws.com",
    "port": 5432,
    "database": "pegasus_db"
  }'

  aws secretsmanager create-secret --name pegasus/vertex-ai --secret-string '{
    "project_id": "gen-lang-client-0319023828",
    "location": "europe-west4", 
    "agent_engine_id": "3290583215235923968",
    "service_account_key": "base64-encoded-key"
  }'

  Phase 2: Container Preparation (Week 1-2)

  2.1 Docker Optimization

  # backend/Dockerfile.production
  FROM python:3.11-slim as builder
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  FROM python:3.11-slim
  WORKDIR /app
  COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
  COPY . .

  # Health check for ECS
  HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

  # Non-root user
  RUN useradd --create-home --shell /bin/bash app
  USER app

  CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

  2.2 Multi-Service Docker Compose → ECS Task Definitions

  # ecs-task-definitions/
  ├── backend-api.json       # FastAPI service
  ├── celery-worker.json     # Background job processor  
  ├── chromadb.json         # Vector database
  └── data-pipeline.json    # ETL scheduled tasks

  2.3 Environment Variable Strategy

  # Container environment (ECS Task Definition)
  DATABASE_URL=postgres://username:password@rds-endpoint:5432/pegasus_db
  REDIS_URL=redis://elasticache-endpoint:6379/0
  VERTEX_AI_PROJECT_ID=${pegasus/vertex-ai:project_id}  # From Secrets Manager
  VERTEX_AI_AGENT_ENGINE_ID=${pegasus/vertex-ai:agent_engine_id}

  Phase 3: Service Deployment (Week 2)

  3.1 ECS Cluster Setup

  # Create ECS cluster
  aws ecs create-cluster --cluster-name pegasus-production

  # ECR repositories for container images
  aws ecr create-repository --repository-name pegasus/backend
  aws ecr create-repository --repository-name pegasus/celery-worker
  aws ecr create-repository --repository-name pegasus/chromadb

  3.2 Load Balancer & Service Discovery

  # Application Load Balancer
  ALB:
    - Target groups: FastAPI backend (port 8000)
    - Health checks: /health endpoint
    - SSL termination: ACM certificate
    - WAF integration: DDoS protection

  # Service Discovery
  CloudMap:
    - Internal DNS for service-to-service communication
    - chromadb.pegasus.internal → ChromaDB service
    - redis.pegasus.internal → ElastiCache endpoint

  3.3 Auto-scaling Configuration

  # ECS Service auto-scaling
  scaling:
    target_cpu: 70%
    target_memory: 80%
    min_capacity: 2
    max_capacity: 10

  # Application-level scaling
  celery_workers:
    min_workers: 2
    max_workers: 20
    scaling_trigger: "queue_length > 50"

  Phase 4: Data Migration & Testing (Week 2-3)

  4.1 Database Migration Strategy

  # Production migration script
  scripts/aws_migration/
  ├── 01_create_rds_database.py    # Initialize RDS PostgreSQL
  ├── 02_migrate_data.py           # Copy existing data (if any)
  ├── 03_create_indexes.py         # Performance optimization
  └── 04_verify_migration.py       # Data integrity checks

  4.2 Vector Database Migration

  # ChromaDB persistence migration
  aws efs create-file-system --tags Key=Name,Value=pegasus-chromadb-storage
  # Mount EFS to ECS tasks for persistent vector storage

  4.3 Authentication Setup

  # Google Cloud Service Account for Vertex AI
  # Create service account in Google Cloud Console
  # Download JSON key → Store in AWS Secrets Manager
  # Configure ECS tasks to retrieve credentials from Secrets Manager

  Phase 5: Monitoring & CI/CD (Week 3-4)

  5.1 Observability Stack

  # CloudWatch integration
  logging:
    - ECS container logs → CloudWatch Logs
    - Structured JSON logging
    - Log aggregation and filtering

  monitoring:
    - CloudWatch metrics (CPU, memory, custom metrics)
    - AWS X-Ray distributed tracing
    - Application Insights dashboards

  alerting:
    - SNS notifications for critical errors
    - Slack/email integration
    - Automated incident response

  5.2 CI/CD Pipeline

  # GitHub Actions or AWS CodePipeline
  Pipeline:
    1. Code commit → trigger build
    2. Docker image build → push to ECR
    3. ECS service update → rolling deployment
    4. Health checks → rollback if failed
    5. Notify deployment status

  🔧 Migration Scripts Needed

  Critical Scripts to Develop:

  scripts/aws_deployment/
  ├── 01_infrastructure/
  │   ├── terraform/               # Infrastructure as code
  │   ├── create_secrets.sh       # AWS Secrets Manager setup
  │   └── setup_networking.sh     # VPC, security groups
  ├── 02_containers/
  │   ├── build_and_push.sh       # ECR image management
  │   ├── ecs_task_definitions/   # ECS service configs
  │   └── health_check_aws.sh     # AWS-specific health checks
  ├── 03_database/
  │   ├── setup_rds.py           # PostgreSQL RDS creation
  │   ├── setup_elasticache.py   # Redis cluster setup
  │   └── migrate_data.py        # Data migration utilities
  └── 04_deployment/
      ├── deploy_ecs_services.sh  # ECS service deployment
      ├── setup_load_balancer.sh  # ALB configuration
      └── configure_auto_scaling.sh # Auto-scaling policies

  💰 Cost Optimization

  Development Environment

  - ECS Fargate Spot instances
  - RDS db.t3.micro with burstable performance
  - ElastiCache t3.micro nodes
  - Estimated cost: $100-200/month

  Production Environment

  - ECS Fargate with reserved capacity
  - RDS Multi-AZ db.r6g.large
  - ElastiCache cluster mode with multiple nodes
  - Estimated cost: $500-1000/month

  🚀 Deployment Timeline

  | Week | Phase                | Deliverables                              |
  |------|----------------------|-------------------------------------------|
  | 1    | Infrastructure       | VPC, RDS, ElastiCache, Secrets            |
  | 2    | Containerization     | Docker images, ECS task definitions       |
  | 2-3  | Service Deployment   | ECS services, load balancer, auto-scaling |
  | 3    | Data Migration       | Database setup, vector storage migration  |
  | 4    | Production Readiness | Monitoring, CI/CD, documentation          |

  Ready to proceed with Phase 1: Infrastructure Setup?
