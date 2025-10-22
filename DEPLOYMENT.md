# Nginx Deployment Guide for bip300.xyz and explorer.bip300.xyz

This guide explains how to deploy your blockchain explorer with nginx configuration for two subdomains and an enforcer service:

- **bip300.xyz** - Serves static files from `/var/www/html`
- **explorer.bip300.xyz** - Proxies to Flask application on port 5000
- **Port 8123** - Enforcer service (accessible via HTTPS on port 8123)

## Configuration Files

- `nginx.conf` - Full HTTPS configuration with SSL
- `nginx-simple.conf` - HTTP-only configuration for testing

## Prerequisites

1. **Nginx installed** on your server
2. **Flask application** running on port 5000
3. **Enforcer service** running on port 8123
4. **Static files** in `/var/www/html` directory
5. **SSL certificates** (for HTTPS version)

## Quick Setup (HTTP Testing)

1. **Copy the simple configuration:**
   ```bash
   sudo cp nginx-simple.conf /etc/nginx/sites-available/bip300
   sudo ln -s /etc/nginx/sites-available/bip300 /etc/nginx/sites-enabled/
   ```

2. **Test the configuration:**
   ```bash
   sudo nginx -t
   ```

3. **Reload nginx:**
   ```bash
   sudo systemctl reload nginx
   ```

## Production Setup (HTTPS)

1. **Install SSL certificates:**
   ```bash
   # Using Let's Encrypt (recommended)
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d bip300.xyz -d www.bip300.xyz -d explorer.bip300.xyz
   ```

2. **Copy the HTTPS configuration:**
   ```bash
   sudo cp nginx.conf /etc/nginx/sites-available/bip300
   sudo ln -s /etc/nginx/sites-available/bip300 /etc/nginx/sites-enabled/
   ```

3. **Update SSL certificate paths** in the configuration file if needed:
   ```bash
   sudo nano /etc/nginx/sites-available/bip300
   ```

4. **Test and reload:**
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## Directory Structure

Ensure your server has the following structure:

```
/var/www/html/          # Static files for bip300.xyz
├── index.html
├── css/
├── js/
├── images/
└── ...

/Users/rob/projects/explorer/  # Flask application
├── app.py
├── requirements.txt
└── ...
```

## Starting the Flask Application

1. **Install dependencies:**
   ```bash
   cd /Users/rob/projects/explorer
   pip install -r requirements.txt
   ```

2. **Run the Flask app:**
   ```bash
   python app.py
   ```

   Or run as a service:
   ```bash
   # Create systemd service file
   sudo nano /etc/systemd/system/blockchain-explorer.service
   ```

   Add this content:
   ```ini
   [Unit]
   Description=Blockchain Explorer Flask App
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/Users/rob/projects/explorer
   ExecStart=/usr/bin/python3 app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Enable and start:
   ```bash
   sudo systemctl enable blockchain-explorer
   sudo systemctl start blockchain-explorer
   ```

## Testing the Setup

1. **Test static files (bip300.xyz):**
   ```bash
   curl -H "Host: bip300.xyz" http://your-server-ip/
   ```

2. **Test Flask proxy (explorer.bip300.xyz):**
   ```bash
   curl -H "Host: explorer.bip300.xyz" http://your-server-ip/health
   ```

3. **Test the enforcer service (port 8123):**
   ```bash
   curl http://your-server-ip:8123/health
   ```

4. **Check nginx logs:**
   ```bash
   sudo tail -f /var/log/nginx/access.log
   sudo tail -f /var/log/nginx/error.log
   ```

## DNS Configuration

Make sure your DNS records point to your server:

```
A    bip300.xyz           -> YOUR_SERVER_IP
A    www.bip300.xyz        -> YOUR_SERVER_IP
A    explorer.bip300.xyz   -> YOUR_SERVER_IP
```

## Security Considerations

1. **Firewall setup:**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 8123/tcp
   sudo ufw enable
   ```

2. **Regular updates:**
   ```bash
   sudo apt update && sudo apt upgrade
   ```

3. **SSL certificate renewal:**
   ```bash
   sudo certbot renew --dry-run
   ```

## Troubleshooting

### Common Issues

1. **502 Bad Gateway:**
   - Check if Flask app is running: `ps aux | grep python`
   - Check port 5000: `netstat -tlnp | grep 5000`

2. **404 Not Found (static files):**
   - Check `/var/www/html` permissions: `ls -la /var/www/html`
   - Ensure nginx can read files: `sudo chown -R www-data:www-data /var/www/html`

3. **SSL Certificate Issues:**
   - Check certificate paths in nginx config
   - Verify certificate validity: `openssl x509 -in /path/to/cert.crt -text -noout`

### Useful Commands

```bash
# Check nginx status
sudo systemctl status nginx

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check Flask app logs
sudo journalctl -u blockchain-explorer -f

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

## Performance Optimization

1. **Enable gzip compression:**
   Add to nginx config:
   ```nginx
   gzip on;
   gzip_vary on;
   gzip_min_length 1024;
   gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
   ```

2. **Set up caching:**
   The configuration already includes caching for static files.

3. **Monitor performance:**
   ```bash
   # Install monitoring tools
   sudo apt install htop iotop nethogs
   ```

## Backup and Maintenance

1. **Backup configuration:**
   ```bash
   sudo cp /etc/nginx/sites-available/bip300 /backup/nginx-bip300-$(date +%Y%m%d).conf
   ```

2. **Regular maintenance:**
   - Monitor disk space
   - Check log file sizes
   - Update SSL certificates
   - Review security logs

## Support

If you encounter issues:

1. Check nginx error logs: `/var/log/nginx/error.log`
2. Verify Flask application is running
3. Test DNS resolution
4. Check firewall settings
5. Verify SSL certificate validity

For additional help, check the nginx documentation or Flask deployment guides.
