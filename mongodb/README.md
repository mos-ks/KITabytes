```bash
docker compose up -d
```



```bash
docker exec -i mongo-secure mongorestore \
  --ssl \
  --sslCAFile /etc/ssl/mongo/mongodb.crt \
  --sslAllowInvalidCertificates \
  --username schraube \
  --password "öwi0yß2älkjf8cx923" \
  --authenticationDatabase admin \
  --archive=/backups/txp_backup.gz \
  --gzip \
  --numInsertionWorkersPerCollection=4
```