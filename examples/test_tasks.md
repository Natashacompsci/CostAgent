# CostAgent — Full Scenario Test Suite

All commands assume the API server is running: `python3 api_server.py`

**Level guide:**
- **L1** → gemini-2.0-flash (cheapest, short tasks)
- **L2** → gemini-2.5-flash (mid-tier, multi-paragraph)
- **L3** → gemini-2.5-pro (premium, complex reasoning)

**Workflow:** Always dry-run first (no `-e`), check cost, then add `-e` to execute.

---

## 1. Writing Agent (写作类)

### Email Drafting

```bash
# L1: Quick reply
python3 main.py run-task -p "Write a one-line reply to decline a meeting invitation politely" -t 30 -l 1

# L2: Cold outreach email
python3 main.py run-task -p "Write a cold outreach email to a potential B2B client about our AI-powered customer analytics platform. Include a compelling subject line, value proposition, social proof, and a clear CTA" -t 300 -l 2

# L2: Apology email
python3 main.py run-task -p "Write a professional apology email to a customer whose order was delayed by 2 weeks. Acknowledge the issue, explain what happened, offer a 20% discount, and describe steps taken to prevent recurrence" -t 250 -l 2

# L2: Follow-up after no response
python3 main.py run-task -p "Write a friendly follow-up email to a prospect who hasn't responded in 5 days. Reference the previous email about our SaaS product, add a new value point, and suggest a specific meeting time" -t 200 -l 2
```

### Business Documents

```bash
# L1: Meeting notes summary
python3 main.py run-task -p "Summarize these meeting notes into 3 action items: 'Discussed Q4 roadmap. Alice will finish the auth module by Dec 15. Bob to research payment gateways. Team agreed to weekly standups starting Monday.'" -t 80 -l 1

# L2: Weekly status report
python3 main.py run-task -p "Write a weekly engineering status report. Team completed: user auth, payment integration. In progress: order management, email notifications. Blocked: waiting for design specs for dashboard. Risks: payment gateway sandbox has intermittent downtime" -t 300 -l 2

# L3: Business proposal
python3 main.py run-task -p "Write a business proposal for a client who wants to build a custom CRM system. Include executive summary, project scope, technical approach (Python/FastAPI/PostgreSQL/React), timeline (3 phases over 6 months), team composition, pricing breakdown ($150k total), and risk mitigation plan" -t 1000 -l 3
```

### Marketing Copy

```bash
# L1: Product tagline
python3 main.py run-task -p "Write 5 catchy taglines for an AI-powered personal finance app called 'WealthPilot'" -t 50 -l 1

# L2: Product launch announcement
python3 main.py run-task -p "Write a product launch announcement for social media (Twitter, LinkedIn, and email newsletter versions) for a new AI code review tool that finds bugs 10x faster than manual review. Include emojis for social posts" -t 400 -l 2

# L2: Landing page copy
python3 main.py run-task -p "Write landing page copy for a SaaS project management tool targeting remote teams. Include hero section headline, 3 feature sections with benefits, social proof section, pricing comparison (Free/Pro/Enterprise), and FAQ section" -t 500 -l 2
```

### Technical Writing

```bash
# L1: Error message explanation
python3 main.py run-task -p "Explain this error in plain English: 'FATAL: password authentication failed for user postgres'" -t 50 -l 1

# L2: API documentation
python3 main.py run-task -p "Write API documentation for a user registration endpoint. Method: POST /api/v1/users. Fields: email (required, unique), password (min 8 chars), name (optional). Returns: user object with JWT token. Include request/response examples, error codes (400, 409, 500), and rate limiting info" -t 400 -l 2

# L2: Changelog entry
python3 main.py run-task -p "Write a changelog entry for version 2.5.0. Changes: added OAuth2 login (Google, GitHub), redesigned dashboard with dark mode, fixed memory leak in WebSocket connections, upgraded to Python 3.12, deprecated /api/v1/legacy endpoints (removal in v3.0)" -t 300 -l 2
```

---

## 2. Research Agent (研究分析类)

### Market Research

```bash
# L1: Quick market fact
python3 main.py run-task -p "What is the current global market size of the SaaS industry?" -t 40 -l 1

# L2: Competitive analysis
python3 main.py run-task -p "Compare Notion, Confluence, and Coda as team knowledge bases. Cover pricing, key features, integrations, pros/cons, and recommend which is best for a 50-person engineering team" -t 500 -l 2

# L3: SWOT + market entry strategy
python3 main.py run-task -p "Perform a SWOT analysis for a startup entering the AI-powered legal document review market. Then design a go-to-market strategy covering target segments, pricing model, distribution channels, competitive positioning, and first-year milestones with KPIs" -t 800 -l 3
```

### Technical Research

```bash
# L1: Quick comparison
python3 main.py run-task -p "Redis vs Memcached: which should I use for session caching and why?" -t 80 -l 1

# L2: Technology evaluation
python3 main.py run-task -p "Evaluate PostgreSQL vs MongoDB vs DynamoDB for a real-time analytics platform processing 100K events/second. Compare on: write throughput, query flexibility, scaling model, operational complexity, cost at scale, and ecosystem/tooling" -t 500 -l 2

# L3: Architecture feasibility study
python3 main.py run-task -p "Conduct a feasibility study for migrating a monolithic Python/Django application to microservices. Current system: 500K LOC, 50 developers, 10M daily active users, PostgreSQL. Evaluate: migration strategies (strangler fig vs big bang), service boundary identification, data decomposition challenges, team restructuring, estimated timeline, and risk assessment" -t 1000 -l 3
```

### Data Analysis

```bash
# L1: Interpret a metric
python3 main.py run-task -p "Our user churn rate increased from 3% to 5% this month. What are the top 3 most likely causes?" -t 80 -l 1

# L2: Analysis report
python3 main.py run-task -p "Analyze this quarterly data and write a report: Q1 revenue $2.1M (up 15%), Q2 $2.4M (up 14%), Q3 $2.3M (down 4%), Q4 $2.8M (up 22%). Monthly active users: 45K, 52K, 48K, 61K. Customer acquisition cost dropped from $120 to $85. Identify trends, anomalies, and provide 3 strategic recommendations" -t 400 -l 2
```

---

## 3. Customer Service Agent (客服类)

### FAQ & Support

```bash
# L1: Simple FAQ
python3 main.py run-task -p "A customer asks: 'How do I reset my password?' Write a friendly support response with step-by-step instructions" -t 80 -l 1

# L1: Refund policy
python3 main.py run-task -p "A customer wants a refund for a subscription purchased 20 days ago. Our policy allows refunds within 30 days. Write a response approving the refund" -t 60 -l 1

# L2: Technical support
python3 main.py run-task -p "A customer reports: 'I keep getting a 503 error when uploading files larger than 10MB. I've tried Chrome and Firefox, same issue. My internet is fine.' Write a detailed troubleshooting response. Consider: file size limits, server configuration, proxy/CDN issues, and browser upload timeouts" -t 300 -l 2
```

### Ticket Processing

```bash
# L2: Classify and respond
python3 main.py run-task -p "Classify this support ticket and write a response. Ticket: 'Hi, I was charged $49.99 twice on my credit card this month for my Pro subscription. I only have one account (email: john@example.com). Please fix this and refund the duplicate charge. This is very frustrating.' Classify by: category, priority, sentiment, and estimated resolution time" -t 300 -l 2

# L2: Escalation recommendation
python3 main.py run-task -p "This customer has submitted 5 tickets in 2 weeks about the same data export issue. Previous responses suggested clearing cache and re-exporting. Issue persists. Write an internal escalation note to the engineering team and a customer-facing response acknowledging the ongoing issue" -t 300 -l 2
```

### Sentiment Analysis

```bash
# L1: Quick sentiment
python3 main.py run-task -p "Classify the sentiment (positive/negative/neutral) and extract the key issue: 'Your app is amazing for task management but the mobile version crashes every time I try to sync. Really frustrating because I love the desktop version.'" -t 60 -l 1

# L2: Batch feedback analysis
python3 main.py run-task -p "Analyze these 5 customer reviews and provide: overall sentiment distribution, top 3 praised features, top 3 complaints, and actionable recommendations. Reviews: 1) 'Love the UI but pricing is too high' 2) 'Best API docs I've ever seen' 3) 'Keeps crashing on large datasets' 4) 'Customer support responded in 5 minutes!' 5) 'Missing basic features like CSV export'" -t 400 -l 2
```

### Multilingual Support

```bash
# L1: Translation
python3 main.py run-task -p "Translate this customer message from Spanish to English and draft a reply in both languages: 'Hola, no puedo acceder a mi cuenta desde ayer. He intentado restablecer la contrasena pero no recibo el correo electronico.'" -t 150 -l 1

# L2: Localized response
python3 main.py run-task -p "A Japanese customer wrote: 'サブスクリプションの解約方法を教えてください。来月の請求前に解約したいです。' Translate, draft a helpful response in Japanese that includes cancellation steps, and note any cultural considerations for the tone" -t 300 -l 2
```

---

## 4. Coding Agent (代码类)

### Code Generation

```bash
# L1: Simple function
python3 main.py run-task -p "Write a Python function that validates an email address using regex" -t 60 -l 1

# L2: Full module
python3 main.py run-task -p "Write a Python rate limiter class using the token bucket algorithm. Include: configurable rate and burst size, thread-safe implementation, decorator for Flask/FastAPI routes, and unit tests" -t 500 -l 2

# L3: System component
python3 main.py run-task -p "Write a complete Python event sourcing implementation. Include: Event base class, EventStore (with SQLite backend), aggregate root pattern, event replay, snapshot support, and a concrete example modeling a bank account with deposit/withdraw/transfer operations" -t 1000 -l 3
```

### Code Review

```bash
# L1: Quick bug spot
python3 main.py run-task -p "Find the bug in this code: def get_average(numbers): total = 0; for n in numbers: total += n; return total / len(numbers)" -t 60 -l 1

# L2: Security review
python3 main.py run-task -p "Review this Flask endpoint for security issues and suggest fixes: @app.route('/search') def search(): query = request.args.get('q'); results = db.execute(f'SELECT * FROM products WHERE name LIKE \"%{query}%\"'); return render_template('results.html', results=results, query=query)" -t 300 -l 2

# L2: Performance review
python3 main.py run-task -p "Review this Python code for performance issues and rewrite it: def find_duplicates(lst): duplicates = []; for i in range(len(lst)): for j in range(i+1, len(lst)): if lst[i] == lst[j] and lst[i] not in duplicates: duplicates.append(lst[i]); return duplicates" -t 200 -l 2
```

### Debugging

```bash
# L1: Error explanation
python3 main.py run-task -p "Explain this Python traceback and suggest a fix: KeyError: 'user_id' at line 42 in views.py: user = session['user_id']" -t 80 -l 1

# L2: Complex debugging
python3 main.py run-task -p "Our Django app has a memory leak. After running for 24 hours, RAM usage grows from 200MB to 2GB. We use: Django 4.2, Celery workers, PostgreSQL, Redis for caching, and we have background tasks that process CSV uploads (up to 50MB). What are the most likely causes? Provide a systematic debugging plan with specific tools and commands" -t 400 -l 2
```

### Database & SQL

```bash
# L1: Simple query
python3 main.py run-task -p "Write a SQL query to find the top 10 customers by total order amount in the last 30 days. Tables: customers(id, name, email), orders(id, customer_id, amount, created_at)" -t 60 -l 1

# L2: Schema design
python3 main.py run-task -p "Design a PostgreSQL schema for a multi-tenant SaaS project management tool. Include: tenants, users, projects, tasks, comments, attachments, time tracking, and audit log. Add indexes, foreign keys, and explain your partitioning strategy for the audit log" -t 500 -l 2
```

---

## 5. CRM & Sales Agent (CRM/销售类)

### Customer Profiling

```bash
# L1: Quick profile
python3 main.py run-task -p "Based on this data, write a one-paragraph customer profile: Company: TechStart Inc, 25 employees, Series A, using our Pro plan for 8 months, 15 active users, main features used: API integration and analytics dashboard" -t 80 -l 1

# L2: Detailed profile + strategy
python3 main.py run-task -p "Create a detailed customer success profile and engagement strategy. Data: Acme Corp, 500 employees, Enterprise plan ($2000/mo), 18 months tenure, 120 active users (down from 150), feature usage declining in reporting module, 3 support tickets about performance in last month, contract renewal in 90 days, champion (VP Engineering) recently left the company" -t 400 -l 2
```

### Sales Emails

```bash
# L2: Upsell email
python3 main.py run-task -p "Write a personalized upsell email to a customer on our Basic plan ($29/mo). They've hit their API rate limit 5 times this month and have 3 team members who can't access the project because of the 5-user limit. Our Pro plan ($79/mo) has unlimited API calls and 25 users. Don't be pushy" -t 250 -l 2

# L2: Renewal reminder
python3 main.py run-task -p "Write a contract renewal email for an Enterprise customer. Their annual contract ($24,000/year) expires in 30 days. They've expanded from 50 to 80 users this year. Propose a renewal with a volume discount (15% off for 3-year commitment) and highlight new features coming in Q2" -t 300 -l 2
```

### Churn Prevention

```bash
# L2: Churn risk analysis
python3 main.py run-task -p "Analyze this customer's behavior and assess churn risk (low/medium/high). Then write a retention action plan. Data: Login frequency dropped from daily to weekly over 3 months. Support tickets: 2 unresolved bugs. NPS score: dropped from 8 to 5. Usage of key features: down 40%. Payment: last invoice paid 15 days late. Contract renewal: 60 days away" -t 400 -l 2
```

---

## 6. Data Agent (数据处理类)

### Format Conversion & SQL

```bash
# L1: Regex
python3 main.py run-task -p "Write a regex pattern that matches valid US phone numbers in these formats: (123) 456-7890, 123-456-7890, 1234567890, +1-123-456-7890" -t 40 -l 1

# L1: SQL from natural language
python3 main.py run-task -p "Convert to SQL: 'Show me all orders from last month where the total is over $100, grouped by product category, sorted by total revenue descending'" -t 60 -l 1

# L2: ETL pipeline design
python3 main.py run-task -p "Design a data pipeline to sync customer data from Salesforce to our PostgreSQL analytics database. Requirements: incremental sync every 15 minutes, handle schema changes, deduplicate records, track sync history, alert on failures. Provide the Python code structure using Apache Airflow" -t 500 -l 2
```

### Data Cleaning

```bash
# L2: Data quality report
python3 main.py run-task -p "I have a CSV with 100K customer records. Common issues found: 15% have missing phone numbers, 8% have invalid email formats, 5% have duplicate entries (same email different names), dates are in mixed formats (MM/DD/YYYY and YYYY-MM-DD), and state field has inconsistent values (CA, California, Calif.). Write a Python data cleaning script using pandas that handles all these issues" -t 500 -l 2
```

---

## 7. Decision Agent (决策支持类)

### Risk Assessment

```bash
# L1: Quick risk check
python3 main.py run-task -p "What are the top 3 risks of deploying a new payment system during Black Friday weekend?" -t 80 -l 1

# L3: Full risk analysis
python3 main.py run-task -p "Conduct a comprehensive risk assessment for migrating our production database from MySQL 5.7 to PostgreSQL 15. Current state: 2TB data, 50K queries/second peak, 99.99% uptime SLA, 200+ stored procedures, 30 dependent microservices. Cover: technical risks, data migration risks, performance risks, business continuity risks, rollback strategy, and risk mitigation plan with timeline" -t 800 -l 3
```

### Decision Framework

```bash
# L2: Build vs Buy
python3 main.py run-task -p "We need an authentication system for our SaaS app (10K users currently, expecting 100K in a year). Compare Build-in-house vs Auth0 vs Firebase Auth vs Keycloak. Evaluate on: cost at different scales, customization needs, compliance (SOC2, GDPR), migration effort, vendor lock-in risk, and team capability (2 backend devs). Recommend one with justification" -t 500 -l 2

# L3: Strategic planning
python3 main.py run-task -p "Our startup ($5M ARR, 30 employees) needs to decide between three growth strategies for next year: A) Focus on enterprise sales (hire 5 sales reps, target $50K+ deals), B) Product-led growth (invest in self-serve, freemium, virality), C) Geographic expansion to EU market. Current metrics: 80% SMB customers, 5% monthly growth, $200 average deal size, 90% US revenue. Provide a decision matrix with scoring, financial projections for each option, and your recommendation" -t 1000 -l 3
```

---

## 8. Ops & DevOps Agent (运维类)

### Alert Analysis

```bash
# L1: Quick alert triage
python3 main.py run-task -p "Triage this alert: 'WARNING: CPU usage at 92% on web-server-03 for 15 minutes. Normal baseline: 40-60%.' What should I check first?" -t 80 -l 1

# L2: Incident response
python3 main.py run-task -p "Write an incident response plan for this scenario: Our API latency spiked from 200ms to 5 seconds at 2:30 AM. Error rate jumped to 15%. Affected services: user-service, order-service. Database CPU is normal. Redis shows high memory usage (95%). Last deployment was 6 hours ago. Include: immediate steps, communication plan, root cause investigation checklist, and post-mortem template" -t 500 -l 2
```

### Configuration Generation

```bash
# L1: Dockerfile
python3 main.py run-task -p "Write a production Dockerfile for a Python FastAPI app. Use multi-stage build, non-root user, health check, and minimal image size" -t 100 -l 1

# L2: CI/CD pipeline
python3 main.py run-task -p "Write a complete GitHub Actions CI/CD pipeline for a Python monorepo with 3 services (api, worker, web). Include: lint (ruff), type check (mypy), unit tests (pytest with coverage), integration tests, build Docker images, push to ECR, deploy to ECS staging on PR merge, deploy to production on release tag with manual approval" -t 600 -l 2

# L2: Kubernetes config
python3 main.py run-task -p "Write Kubernetes manifests for deploying a Python web app with: Deployment (3 replicas, rolling update), Service (ClusterIP), Ingress (with TLS), HPA (scale 3-10 based on CPU), ConfigMap, Secret (for DB credentials), PersistentVolumeClaim (for uploaded files), and NetworkPolicy" -t 500 -l 2
```

### Capacity Planning

```bash
# L2: Infrastructure sizing
python3 main.py run-task -p "Our SaaS app is growing from 10K to 100K users over the next 12 months. Current infra: 2 x t3.large (API), 1 x r5.xlarge (PostgreSQL), 1 x r5.large (Redis), 50GB S3. Average user makes 50 API calls/day, stores 100MB of data. Estimate the required infrastructure at 50K and 100K users, monthly AWS cost projection, and recommend when to scale each component" -t 500 -l 2
```

---

## 9. Product Agent (产品类)

### Requirements

```bash
# L1: User story
python3 main.py run-task -p "Write a user story with acceptance criteria for: 'As a user, I want to export my dashboard data to PDF'" -t 80 -l 1

# L2: PRD section
python3 main.py run-task -p "Write the requirements section of a PRD for a notification system. Features needed: in-app notifications, email digests (daily/weekly), push notifications (mobile), notification preferences per channel, do-not-disturb schedule, notification grouping, read/unread status, and notification center UI. Include priority (P0-P3) for each feature" -t 500 -l 2

# L3: Full PRD
python3 main.py run-task -p "Write a complete PRD for adding a team collaboration feature to our project management tool. Include: problem statement, user personas (3), jobs-to-be-done, feature requirements with priorities, UX wireframe descriptions, technical constraints, success metrics, phased rollout plan, and competitive analysis vs Asana and Monday.com" -t 1000 -l 3
```

### User Feedback Analysis

```bash
# L2: Feedback synthesis
python3 main.py run-task -p "Synthesize these 8 user feedback items into product insights: 1) 'Need Slack integration' 2) 'Dashboard loads too slowly' 3) 'Can you add Microsoft Teams notifications?' 4) 'Export to Excel doesn't work on Safari' 5) 'We need SSO for our team' 6) 'The mobile app needs offline mode' 7) 'Please add Zapier/webhook support' 8) 'Search is broken when using special characters'. Group by theme, identify the top 3 priorities, and suggest a product roadmap" -t 400 -l 2
```

---

## 10. Legal & Compliance Agent (法务合规类)

### Compliance

```bash
# L1: Quick compliance check
python3 main.py run-task -p "Does a SaaS company processing EU customer emails need to comply with GDPR? What are the 3 most critical requirements?" -t 80 -l 1

# L2: Compliance checklist
python3 main.py run-task -p "Create a SOC 2 Type II compliance checklist for a cloud-based SaaS startup. Cover the 5 Trust Service Criteria (Security, Availability, Processing Integrity, Confidentiality, Privacy). For each, list specific controls needed, evidence to collect, and common gaps" -t 600 -l 2

# L3: Privacy policy draft
python3 main.py run-task -p "Draft a privacy policy for a SaaS analytics platform that: collects user behavioral data via JavaScript SDK, processes data in US and EU (AWS regions), shares anonymized data with advertising partners, uses cookies and local storage, offers a free tier and paid plans, has users in EU/US/Japan. Cover: GDPR, CCPA, LGPD requirements, data retention policy, user rights, cookie policy, third-party services, children's privacy, and international data transfers" -t 1000 -l 3
```

---

## Workflow Tests

### W1. Dry-run → Execute (Cost-Aware Execution)

```bash
# Step 1: Estimate cost
python3 main.py run-task -p "Write a product launch email for our new AI feature" -t 200 -l 2
# Step 2: If cost is acceptable, execute
python3 main.py run-task -p "Write a product launch email for our new AI feature" -t 200 -l 2 -e
# Step 3: Verify it was logged
python3 main.py history -n 2
```

### W2. Cross-Level Cost Comparison

```bash
# Same prompt, different levels — compare model and cost
python3 main.py run-task -p "Explain the CAP theorem and its implications for distributed databases" -t 200 -l 1
python3 main.py run-task -p "Explain the CAP theorem and its implications for distributed databases" -t 200 -l 2
python3 main.py run-task -p "Explain the CAP theorem and its implications for distributed databases" -t 200 -l 3
```

### W3. Budget Guard Test

```bash
# Set extremely low budget — should be blocked
python3 main.py run-task -p "Write a long essay about machine learning" -t 500 -l 3 -b 0.000001
# Raise budget — should pass
python3 main.py run-task -p "Write a long essay about machine learning" -t 500 -l 3 -b 10.0
```

### W4. Model Override

```bash
# Force expensive model on a simple task
python3 main.py run-task -p "What is 2+2?" -t 10 -l 1 -m "gemini/gemini-2.5-pro"
# Force cheap model on a complex task
python3 main.py run-task -p "Design a distributed consensus algorithm" -t 500 -l 3 -m "gemini/gemini-2.0-flash"
```

### W5. File Input/Output

```bash
# Save a complex prompt to a file, then run it
echo "Analyze the competitive landscape of the cloud computing market in 2024. Cover AWS, Azure, GCP market share, pricing trends, and emerging players." > /tmp/research_prompt.txt
python3 main.py run-task -f /tmp/research_prompt.txt -t 500 -l 2 -o /tmp/research_result.json
cat /tmp/research_result.json | python3 -m json.tool
```

### W6. Batch API Estimation (curl)

```bash
# Estimate cost for multiple tasks in one go
for prompt in \
  "Translate hello to Spanish" \
  "Write a Python sort function" \
  "Design a payment system architecture"; do
  echo "=== $prompt ==="
  curl -s -X POST http://localhost:8000/api/run \
    -H "Content-Type: application/json" \
    -d "{\"input_text\": \"$prompt\", \"tokens\": 200, \"level\": 2}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Model: {d[\"model\"]} | Cost: \${d[\"total_cost\"]:.5f}')"
done
```

---

## Agent Flow Tests

### F1. Chain: Research → Report → Email Summary

```bash
# Step 1: Research (save output)
python3 main.py run-task -p "List the top 5 project management tools for engineering teams with pros and cons" -t 400 -l 2 -e -o /tmp/step1_research.json

# Step 2: Feed research into report (use the output as context)
python3 main.py run-task -p "Based on this research, write a recommendation report for our CTO: $(python3 -c 'import json; print(json.load(open("/tmp/step1_research.json"))["response"][:500])')" -t 400 -l 2 -e -o /tmp/step2_report.json

# Step 3: Summarize into email
python3 main.py run-task -p "Summarize this report into a 3-sentence email for the CTO: $(python3 -c 'import json; print(json.load(open("/tmp/step2_report.json"))["response"][:500])')" -t 100 -l 1 -e
```

### F2. Fan-out: Same Prompt, Different Models

```bash
# Compare responses from different models via API
for model in "gemini/gemini-2.0-flash" "gemini/gemini-2.5-flash" "gemini/gemini-2.5-pro"; do
  echo "=== $model ==="
  curl -s -X POST http://localhost:8000/api/run \
    -H "Content-Type: application/json" \
    -d "{\"input_text\": \"Explain quantum computing in one paragraph\", \"tokens\": 100, \"level\": 1, \"model\": \"$model\", \"execute\": true}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Cost: \${d[\"actual_cost\"]:.6f} | Tokens: {d.get(\"actual_output_tokens\",\"?\")}'); print(d['response'][:200]); print()"
done
```

### F3. Conditional: Execute Only If Cheap

```bash
# Dry-run first, then conditionally execute based on cost
RESULT=$(curl -s -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Write a haiku about programming", "tokens": 30, "level": 1}')
COST=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['total_cost'])")
echo "Estimated cost: $COST"
if python3 -c "exit(0 if $COST < 0.01 else 1)"; then
  echo "Cost is low, executing..."
  curl -s -X POST http://localhost:8000/api/run \
    -H "Content-Type: application/json" \
    -d '{"input_text": "Write a haiku about programming", "tokens": 30, "level": 1, "execute": true}' \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['response'])"
else
  echo "Cost too high, skipping execution"
fi
```

### F4. Budget Monitor: Multi-Call Tracking

```bash
# Run 5 tasks and track cumulative cost
for i in 1 2 3 4 5; do
  echo "=== Task $i ==="
  python3 main.py run-task -p "Task $i: Summarize the benefits of cloud computing" -t 50 -l 1 -e
  echo ""
done
# Check total spend
python3 main.py budget-check
```

---

## Edge Case & Error Tests

```bash
# Empty prompt (should return 422)
python3 main.py run-task -p "" -t 20 -l 1

# Very long prompt (10000+ chars)
python3 main.py run-task -p "$(python3 -c "print('test ' * 2500)")" -t 50 -l 1

# Minimal output tokens
python3 main.py run-task -p "Say yes or no: Is the sky blue?" -t 1 -l 1

# Large output tokens
python3 main.py run-task -p "Write a long essay" -t 4096 -l 3

# Zero budget
python3 main.py run-task -p "Hello" -t 20 -l 1 -b 0

# Invalid level (should return 422)
python3 main.py run-task -p "Hello" -t 20 -l 0
python3 main.py run-task -p "Hello" -t 20 -l 4

# Invalid model name
python3 main.py run-task -p "Hello" -t 20 -l 1 -m "nonexistent/model" -e

# Server not running
# (stop the server first, then try)
python3 main.py run-task -p "Hello" -t 20 -l 1
# Expected: "Error: cannot connect to API server..."
```
