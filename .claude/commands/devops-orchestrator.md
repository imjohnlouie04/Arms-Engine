---
name: devops-orchestrator
description: >
  Automate the bridge between local development and production-ready deployments while enforcing zero-config-drift. Use this skill for infrastructure as code workflows, deployment pipeline design, CI/CD automation, environment parity, drift detection and remediation, GitOps practices, immutable infrastructure patterns, blue-green or canary deployments, local-to-production consistency, configuration management, Terraform/Ansible/Pulumi workflows, Kubernetes deployment automation, cloud infrastructure provisioning (AWS, Azure, GCP), container orchestration, infrastructure testing, state management, secrets management, rollback strategies, and any scenario involving automated infrastructure deployment or preventing configuration drift between environments.
---

# DevOps Orchestrator

## Overview

This skill helps you design and implement automated infrastructure workflows that maintain zero configuration drift from local development through production. The core principle: **what works locally must work identically in production**, enforced through code, automation, and continuous validation.

Configuration drift—when live systems diverge from their intended state—is the silent killer of reliability. It stems from manual hotfixes, undocumented patches, inconsistent tooling, and emergency changes that bypass proper workflows. This skill focuses on preventing drift before it happens and detecting it immediately when it does.

## Core Principles

### 1. Infrastructure as Code is the Single Source of Truth

All infrastructure definitions live in version control. If it's not in code, it doesn't exist. This includes:

- Compute resources (VMs, containers, serverless functions)
- Networking (VPCs, subnets, security groups, load balancers)
- Storage and databases
- IAM roles and policies
- Configuration files and environment variables
- Deployment scripts and pipeline definitions

Why this matters: When infrastructure is code, you get versioning, peer review, rollback capability, and an audit trail. Manual changes bypass all of these safeguards and introduce drift.

### 2. Build Once, Deploy Everywhere

Artifacts (containers, binaries, packages) are built once and promoted through environments. Never rebuild for different stages—this guarantees what you tested is what you deploy.

Pattern:
```
Commit → Build Artifact → Tag with SHA
  ↓
Dev (deploy artifact:SHA)
  ↓
Staging (deploy same artifact:SHA)
  ↓
Production (deploy same artifact:SHA)
```

Environment-specific configuration is injected at runtime via environment variables, config maps, or secrets—never baked into artifacts.

### 3. Environments Must Be Identical in Structure

Production and non-production environments should differ only in scale and data, not in architecture. If production runs on Kubernetes with a PostgreSQL RDS instance behind an ALB, staging should too (even if smaller).

Why: "It works on my machine" problems scale exponentially when dev uses SQLite, staging uses MySQL, and production uses PostgreSQL. Structural differences hide bugs until production.

### 4. Automate Drift Detection and Remediation

Drift happens. The question is whether you detect it in minutes or discover it during an outage.

**Detection strategies:**
- Run `terraform plan` or equivalent on a schedule (every 1-6 hours)
- Integrate drift checks into CI/CD pipelines before deployments
- Use cloud-native tools (AWS Config, Azure Policy, GCP Config Connector) for continuous monitoring
- Alert on any detected drift immediately

**Remediation approaches:**
- **Automated reconciliation**: GitOps tools (ArgoCD, Flux) continuously sync live state to desired state
- **Immutable infrastructure**: Replace drifted resources entirely rather than patching them
- **Pull request generation**: Tools like Firefly generate PRs to incorporate valid manual changes back into IaC

### 5. Treat Configuration Changes Like Code Changes

Configuration errors cause more outages than code bugs. Environment configs, feature flags, and infrastructure definitions must go through the same rigor as application code:

- Peer review via pull requests
- Automated validation and testing
- Staged rollouts with monitoring
- Immediate rollback capability

## Deployment Pipeline Patterns

### Progressive Validation Pipeline

Each stage validates different concerns, failing fast when issues are detected:

```
1. Commit Stage (< 5 min)
   - Lint IaC (terraform validate, tflint, checkov)
   - Unit tests
   - Build artifacts
   - Static security scanning
   
2. Integration Stage (10-20 min)
   - Deploy to ephemeral environment
   - Integration tests
   - Infrastructure validation tests
   - Tear down environment
   
3. Staging Deployment (on-demand)
   - Deploy to persistent staging
   - Smoke tests
   - Performance baseline checks
   - Drift detection scan
   
4. Production Deployment (on-demand or automated)
   - Blue-green or canary deployment
   - Health checks and monitoring
   - Automated rollback on failure
```

Each stage must pass before the next begins. A failure at any stage blocks progression and triggers alerts.

### GitOps Workflow

Git repository is the single source of truth. Changes to the repo automatically trigger reconciliation in live environments.

**Pattern:**
1. Developer commits IaC change to feature branch
2. CI runs validation tests and security scans
3. PR review and approval
4. Merge to main branch
5. GitOps agent (ArgoCD, Flux) detects change
6. Agent applies changes to cluster/infrastructure
7. Continuous monitoring compares live state to Git state
8. Any drift triggers alerts or auto-remediation

**Critical detail:** The GitOps agent must have read-only access to Git and write access to infrastructure, never the reverse. This prevents compromised infrastructure from poisoning your source of truth.

### Environment Parity via Shared Scripts

Local development, CI, and production should execute identical scripts with identical configurations.

**Anti-pattern:**
- Local: `black --line-length 88 .`
- CI: `black --line-length 120 .`
- Result: CI fails on code that passes locally

**Correct pattern:**
Store a single `scripts/format.sh` in version control:
```bash
#!/bin/bash
black --line-length 88 --config pyproject.toml .
```

Both local and CI execute `./scripts/format.sh`. Configuration lives in `pyproject.toml`, versioned alongside code. Impossible for environments to diverge.

Extend this pattern to all tooling: linting, testing, building, deploying. One script, one config, many environments.

## Drift Prevention Strategies

### Immutable Infrastructure

Servers are never modified after deployment. To make a change, deploy a new version and destroy the old one.

**Benefits:**
- Drift is impossible—instances are replaced, not modified
- Rollback means routing traffic back to previous version
- Every deployment is tested (you deploy the same way every time)
- No snowflake servers with unknown history

**Implementation:**
- Use container orchestration (Kubernetes, ECS) or auto-scaling groups
- Bake AMIs/images with Packer or Docker
- Blue-green or canary deployment patterns
- Never SSH into production servers to make changes

### Declarative Over Imperative

Declarative IaC (Terraform, CloudFormation, Pulumi) defines desired end state. The tool figures out how to get there. Imperative approaches (shell scripts, Ansible playbooks) define exact steps.

Declarative is better for drift prevention because:
- Running the same config twice produces the same result (idempotent)
- Drift is visible: `terraform plan` shows divergence from code
- State management is built-in

Use imperative tools (Ansible, scripts) for configuration management on top of declaratively-provisioned infrastructure, not as a replacement.

### Policy as Code

Enforce compliance and security requirements automatically via policy engines:

- **OPA (Open Policy Rego)**: General-purpose policy engine
- **Sentinel (Terraform)**: Policy as code for Terraform workflows
- **Kyverno (Kubernetes)**: Policy engine for K8s resources
- **Cloud-native**: AWS Config Rules, Azure Policy, GCP Organization Policies

**Example policies:**
- All S3 buckets must have encryption enabled
- No security groups can allow 0.0.0.0/0 on port 22
- All production resources must have specific tags
- Database instances must be in private subnets

Policies run during `terraform plan` or as admission controllers, blocking non-compliant changes before they're applied.

## Deployment Strategies

### Blue-Green Deployment

Two identical production environments. Only one receives traffic at a time.

1. Blue is live, serving production traffic
2. Deploy new version to Green
3. Run smoke tests against Green
4. Switch traffic from Blue to Green (instant cutover)
5. Monitor Green closely
6. Keep Blue running for fast rollback if needed
7. After confidence period, tear down Blue

**Pros:** Instant rollback, zero-downtime, full testing in production environment before cutover
**Cons:** Requires 2x infrastructure (at least temporarily), database migrations need special handling

### Canary Deployment

Gradually shift traffic from old version to new version while monitoring for issues.

1. Deploy new version alongside old version
2. Route 5% of traffic to new version
3. Monitor error rates, latency, business metrics
4. If healthy, increase to 25%, then 50%, then 100%
5. If issues detected, halt rollout and route all traffic back to old version

**Pros:** Lower risk, real production validation with limited blast radius
**Cons:** Requires sophisticated traffic routing, both versions run simultaneously, longer deployment window

### Feature Flags for Decoupled Deployment

Deploy code to production with new features disabled. Enable features independently of deployment.

**Benefits:**
- Deploy anytime without exposing incomplete features
- Test in production with internal users before public release
- Instant feature rollback without redeployment
- A/B testing and gradual rollouts
- Separate deployment risk from feature risk

**Implementation:** LaunchDarkly, Unleash, Flagsmith, or build your own config service.

## Practical Workflows

### Local Development That Mirrors Production

**Dev containers** (VS Code devcontainers, GitHub Codespaces) ensure every developer has identical tooling:

```json
{
  "name": "Infrastructure Dev",
  "image": "hashicorp/terraform:1.7",
  "features": {
    "ghcr.io/devcontainers/features/aws-cli:1": {},
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {}
  },
  "postCreateCommand": "./scripts/setup-dev.sh"
}
```

Every developer gets the same Terraform version, same AWS CLI, same kubectl. No more "works on my machine."

### Infrastructure Testing

Test your infrastructure code before applying it:

**Static validation:**
```bash
terraform fmt -check
terraform validate
tflint
checkov --directory .
```

**Unit tests** (Terratest example):
```go
func TestVPCCreation(t *testing.T) {
    terraformOptions := &terraform.Options{
        TerraformDir: "../modules/vpc",
    }
    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)
    
    vpcID := terraform.Output(t, terraformOptions, "vpc_id")
    assert.NotEmpty(t, vpcID)
}
```

**Integration tests:** Deploy to ephemeral environment, validate behavior, tear down.

### Secrets Management

Never commit secrets to Git. Never.

**Patterns:**
- **Secrets managers**: AWS Secrets Manager, HashiCorp Vault, Azure Key Vault
- **Injection at runtime**: K8s secrets, AWS Parameter Store, env vars from CI/CD
- **Encryption at rest**: SOPS, git-crypt for encrypted secrets in Git (use cautiously)

**Workflow:**
```bash
# Development: use local .env (gitignored)
source .env

# CI/CD: inject from secrets manager
export DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id prod/db/password --query SecretString --output text)

# Kubernetes: mount secrets as volumes or env vars
kubectl create secret generic db-creds \
  --from-literal=password="${DB_PASSWORD}"
```

### State Management (Terraform)

State files track what infrastructure exists. Never store state locally for shared infrastructure.

**Remote state backends:**
```hcl
terraform {
  backend "s3" {
    bucket         = "company-terraform-state"
    key            = "production/infrastructure.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```

**State locking** (via DynamoDB) prevents concurrent modifications. **Encryption** protects sensitive data in state. **Versioning** on the S3 bucket enables state recovery.

## Common Pitfalls

**Manual emergency fixes that bypass IaC**: Always follow up by codifying the change. Set a reminder, create a ticket, or block the next deployment until drift is resolved.

**Rebuilding artifacts for different environments**: This invalidates all testing. Build once, configure per environment.

**Skipping drift detection because "we never make manual changes"**: Drift happens from automation too—cloud provider changes, autoscaling, agents, monitoring tools.

**Treating staging as optional**: If you skip staging and deploy straight to production, you're using your customers as QA.

**No rollback plan**: Every deployment must have a tested rollback procedure. "We'll figure it out if something breaks" is not a plan.

## Decision Framework

**When to use immutable infrastructure:**
Stateless applications, containerized workloads, cloud-native architectures. Avoid for legacy systems with complex state or licensing constraints.

**When to use blue-green vs canary:**
Blue-green for lower-traffic systems or when instant rollback is critical. Canary for high-traffic systems where gradual validation reduces risk.

**When to use GitOps:**
Kubernetes environments, teams comfortable with declarative config, when audit trail and drift prevention are priorities. Avoid if you need imperative workflows or complex multi-step orchestrations.

**When to automate drift remediation:**
Well-understood, stable infrastructure with high confidence in IaC. Start with alerts only for critical or complex systems until you've validated your automation.

## Key Metrics

- **Deployment frequency**: How often do you deploy to production?
- **Lead time**: Time from commit to production deployment
- **Change failure rate**: What percentage of deployments cause incidents?
- **Time to restore**: How quickly can you recover from a failed deployment?
- **Drift detection latency**: How long between drift occurring and detection?
- **Drift remediation time**: How long from detection to resolution?

High-performing teams deploy multiple times per day with <15% change failure rate and <1 hour recovery time.