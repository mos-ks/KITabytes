1. Put `txp_backup.gz` into the folder `data`.

2. Start the docker container
```bash
docker compose up -d
```

3. Load data dump into database
```bash
docker exec -i mongo-secure mongorestore \
  --ssl \
  --sslCAFile /etc/ssl/mongo/mongodb.crt \
  --sslAllowInvalidCertificates \
  --username $MONGO_USER \
  --password "$MONGO_PASSWORD" \
  --authenticationDatabase admin \
  --archive=/backups/txp_backup.gz \
  --gzip \
  --numInsertionWorkersPerCollection=4
```

Set `MONGO_USER` and `MONGO_PASSWORD` environment variables before running.
