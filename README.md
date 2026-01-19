## Step 1:
### CREATE VPC :
1 PUBLIC & 2 PRIVATE SUBNET

## Step 2:
### CREATE SG :
11434, 8000, 5432, 5000, 2049, 443, 80, 22

## Step 3:
### CREATE EC2 :
DEBIAN, VPC, PUBLIC SUBNET, SG, SSH KEY, VOLUME 15GB

## Step 4:
### EC2 SETUP GUIDE
### Create 2GB swap file
```sh
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Make permanent
```sh
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Verify
```sh
free -h
```
-- Why: t2.micro has only 1GB RAM. Ollama + model needs ~1.5-2GB. Swap prevents OOM kills. --

### Update system
```sh
sudo apt update && sudo apt upgrade -y
```

### Install Python 3.11
```sh
sudo apt install -y python3 python3-venv python3-pip
```

### Install SQLite (if using SQLite)
```sh
sudo apt install -y sqlite3
```

### Optional: Install PostgreSQL (only if needed)
```sh
sudo apt install -y postgresql postgresql-contrib
```

### Install Ollama
```sh
curl -fsSL https://ollama.com/install.sh | sh
```

### Start Ollama service
```sh
sudo systemctl start ollama
sudo systemctl enable ollama
```

### Pull a small model
```sh
ollama pull tinyllama       # 637MB - fastest, lower quality
```

### Create project directory
```sh
mkdir -p ~/chatapp
cd ~/chatapp
```

### Install Git
```sh
sudo apt install git -y
```

### Improt files from this repo
```sh
git clone https://github.com/xvapai/lks-llm-mini-ec2.git
```

### Create virtual environment
```sh
cd /lks-llm-mini-ec2/project/backend
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies
```sh
pip install -r requirements.txt
```

### Configure environment
```sh
cp .env.example .env
nano .env  # Edit if needed (default SQLite works)
```

### Initialize database
```sh
python3 -c "import db; db.init_db()"
```

## Step 5: 
### Run with Systemd (Production)
### Create service file:
```sh
sudo nano /etc/systemd/system/chatapp.service
```
```sh
[Unit]
Description=AI Chat Application
After=network.target ollama.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/chatapp/lks-llm-mini-ec2/project/backend
Environment="PATH=/home/ubuntu/chatapp/lks-llm-mini-ec2/project/backend/venv/bin"
ExecStart=/home/ubuntu/chatapp/lks-llm-mini-ec2/project/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Start service:
```sh
sudo systemctl daemon-reload
sudo systemctl start chatapp
sudo systemctl enable chatapp
sudo systemctl status chatapp
```

### Test Ollama
```sh
curl http://localhost:11434/api/generate -d '{
  "model": "phi",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

### Test Backend Health
```sh
curl http://localhost:8000/health
```

### Expected output:
```sh
{
  "status": "ok",
  "database": "sqlite",
  "ollama_host": "http://localhost:11434",
  "model": "phi"
}
```

### Test Endpoint
```sh
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what is AI?", "use_history": true}'
```

## If you want to use PostgreSQL instead of SQLite:
### Install PostgreSQL
```sh
sudo apt install -y postgresql postgresql-contrib
```

### Create database
```sh
sudo -u postgres psql
CREATE DATABASE chatdb;
CREATE USER chatuser WITH PASSWORD 'securepassword';
GRANT ALL PRIVILEGES ON DATABASE chatdb TO chatuser;
\q
```

### Update .env
```sh
DATABASE_TYPE=postgres
DATABASE_URL=postgresql://chatuser:securepassword@localhost/chatdb
```

### test apps:
```sh
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Open browser:
```sh
http://<your-ec2-ip>:8000
```
