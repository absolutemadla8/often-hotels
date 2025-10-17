# CI/CD Setup Guide - Often Hotels

This guide will help you complete the CI/CD setup for the Often Hotels project.

## 🎯 Overview

Your CI/CD pipeline is now configured with:
- ✅ **CI Pipeline** (`.github/workflows/ci.yml`) - Runs tests and builds on every push/PR
- ✅ **CD Pipeline** (`.github/workflows/cd.yml`) - Auto-deploys to VM on push to `sarvesh/db-setup`
- ✅ **Deployment Script** (`scripts/deploy.sh`) - Handles the deployment process on VM

## 🔐 Required: Configure GitHub Secrets

You need to add these secrets to your GitHub repository to make the CI/CD work.

### Step 1: Go to GitHub Secrets

1. Open your repository: https://github.com/absolutemadla8/often-hotels
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

### Step 2: Add These Secrets

Add each of the following secrets one by one:

#### **VM Connection Secrets**

| Secret Name | Value | Description |
|------------|-------|-------------|
| `VM_HOST` | `209.38.122.169` | Your VM IP address |
| `VM_USER` | `root` | SSH username for VM |
| `VM_SSH_KEY` | `[Your SSH Private Key]` | See instructions below |

#### **Application Secrets**

| Secret Name | Value | Description |
|------------|-------|-------------|
| `SECRET_KEY` | `04b13762d1a3ab964d002f70c68c714dc84caa7ad908d08d290e70aac9751156` | App secret key |
| `SERP_API_KEY` | `[Your SerpAPI Key]` | Get from https://serpapi.com |
| `TRAVCLAN_API_KEY` | `[Your TravClan Key]` | Your TravClan API key |
| `DATABASE_URL` | `postgresql://postgres:password@db:5432/often_hotels` | PostgreSQL connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |

---

## 🔑 How to Get Your SSH Private Key

### Option 1: Use Existing SSH Key

If you already have an SSH key that can access your VM:

```bash
# On your local machine
cat ~/.ssh/id_rsa
# or
cat ~/.ssh/id_ed25519
```

Copy the **entire output** (including `-----BEGIN ... KEY-----` and `-----END ... KEY-----`)

### Option 2: Create a New Deploy Key

```bash
# On your VM (209.38.122.169)
ssh root@209.38.122.169

# Generate a new SSH key specifically for deployment
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_key -N ""

# Add the public key to authorized_keys
cat ~/.ssh/github_deploy_key.pub >> ~/.ssh/authorized_keys

# Display the private key (copy this to GitHub Secrets)
cat ~/.ssh/github_deploy_key
```

Copy the private key output and add it as the `VM_SSH_KEY` secret.

---

## ✅ Verify Setup on VM

Before pushing code, ensure your VM is ready:

```bash
# SSH into your VM
ssh root@209.38.122.169

# Navigate to project directory
cd /root/often-hotels

# Ensure you're on the correct branch
git checkout sarvesh/db-setup

# Ensure Docker and Docker Compose are installed
docker --version
docker-compose --version

# If not installed, run:
# curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
# curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
# chmod +x /usr/local/bin/docker-compose
```

---

## 🚀 How to Use the CI/CD Pipeline

### 1. **Automatic Deployment**

Simply push to the `sarvesh/db-setup` branch:

```bash
git add .
git commit -m "feat: add new feature"
git push origin sarvesh/db-setup
```

This will:
1. ✅ Run CI tests (if configured)
2. ✅ Build Docker images
3. ✅ Deploy to VM automatically
4. ✅ Restart all services

### 2. **Manual Deployment**

Trigger deployment manually from GitHub:

1. Go to: https://github.com/absolutemadla8/often-hotels/actions
2. Click on "CD - Deploy to VM"
3. Click "Run workflow"
4. Select branch `sarvesh/db-setup`
5. Click "Run workflow"

### 3. **View Deployment Logs**

1. Go to: https://github.com/absolutemadla8/often-hotels/actions
2. Click on the latest workflow run
3. Expand the steps to see detailed logs

---

## 📊 What Each Pipeline Does

### **CI Pipeline** (`.github/workflows/ci.yml`)

Runs on: Every push and pull request

Steps:
1. Sets up PostgreSQL and Redis test databases
2. Installs Python dependencies
3. Runs linting (flake8)
4. Runs unit tests with coverage
5. Runs security scans (Bandit, Safety)
6. Builds Docker image to verify Dockerfile

### **CD Pipeline** (`.github/workflows/cd.yml`)

Runs on: Push to `sarvesh/db-setup` branch

Steps:
1. Connects to VM via SSH
2. Pulls latest code from GitHub
3. Updates `.env` with secrets
4. Stops existing containers
5. Rebuilds Docker images
6. Starts all containers (API, Celery, Redis, PostgreSQL)
7. Runs database migrations
8. Verifies deployment health
9. Shows container status and logs

---

## 🔍 Monitoring Your Deployment

### Check Deployment Status

```bash
# SSH into VM
ssh root@209.38.122.169

# Navigate to project
cd /root/often-hotels

# Check all containers
docker-compose ps

# View API logs
docker logs -f often-hotels-api

# View Celery worker logs
docker logs -f often-hotels-celery-worker

# Check if API is responding
curl http://localhost:8006/docs
```

### Access Services

Once deployed on VM:
- **API**: http://209.38.122.169:8006
- **API Docs**: http://209.38.122.169:8006/docs
- **Flower (Celery Monitor)**: http://209.38.122.169:5559

---

## 🐛 Troubleshooting

### Deployment Failed?

1. **Check GitHub Actions logs**:
   - Go to Actions tab → Click failed workflow → View error logs

2. **SSH into VM and check**:
   ```bash
   ssh root@209.38.122.169
   cd /root/often-hotels
   docker-compose ps
   docker logs often-hotels-api
   ```

3. **Common issues**:
   - ❌ **SSH connection failed**: Check `VM_SSH_KEY` secret is correct
   - ❌ **Permission denied**: Ensure SSH key is added to VM's `authorized_keys`
   - ❌ **Docker build failed**: Check Dockerfile syntax
   - ❌ **Container not starting**: Check environment variables in secrets
   - ❌ **Database migration failed**: Check database is running

### Rollback to Previous Version

```bash
# SSH into VM
ssh root@209.38.122.169
cd /root/often-hotels

# View commit history
git log --oneline -10

# Checkout previous working commit
git checkout <commit-hash>

# Restart containers
docker-compose down && docker-compose up -d
```

---

## 🔄 Manual Deployment (Fallback)

If CI/CD fails, deploy manually:

```bash
# SSH into VM
ssh root@209.38.122.169

# Run the deployment script
cd /root/often-hotels
git pull origin sarvesh/db-setup
./scripts/deploy.sh
```

---

## 📝 Next Steps

1. ✅ **Add GitHub Secrets** (see above)
2. ✅ **Verify VM is accessible** via SSH
3. ✅ **Push code** to trigger first deployment
4. ✅ **Monitor** the GitHub Actions workflow
5. ✅ **Check** services are running on VM

---

## 🎉 Success Checklist

- [ ] All GitHub Secrets added
- [ ] SSH key works for VM access
- [ ] Pushed code to `sarvesh/db-setup` branch
- [ ] GitHub Actions workflow completed successfully
- [ ] Containers running on VM (`docker-compose ps`)
- [ ] API accessible at http://209.38.122.169:8006/docs
- [ ] No errors in container logs

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)

---

## 🆘 Need Help?

If you encounter issues:
1. Check GitHub Actions logs
2. Check VM container logs
3. Verify all secrets are correctly configured
4. Ensure SSH access to VM works

**Happy Deploying! 🚀**
